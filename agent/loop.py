"""The agent loop (T6): model call, tool calls, tool results, repeat until the model answers.

No framework (SPEC §4). At most STEP_CAP model calls per question (D57); at the cap the answer is
"I don't know" with the evidence so far (D65). A tool error goes back to the model as the tool result;
a spend-cap refusal or a failed model call ends the run.

Evidence comes from the tool calls that actually ran, not from the model's account of them (D63).
The confidence note is the model's last line plus flags the code checks itself (D64).
Retrieved passages reach the model inside <passage> tags, as data (D62).
"""
import json, re, time
from datetime import datetime, timezone
from pathlib import Path

from agent import adapter, index, spend, tools

STEP_CAP = 8           # model calls per question (D57)
MAX_TOKENS = 2048      # per model call (D66)
SYSTEM_PROMPT = Path(__file__).resolve().parent / "system_prompt.md"
RUN_LOG = tools.ROOT / "logs" / "runs.jsonl"
CITATION = re.compile(r"\b[A-Z]{3}(?:-[A-Z0-9]+)+-v\d+#\d+\b")
# T13: a lookup that finds nothing is checked for near matches before the answer says none exist.
ZERO_ROWS = ("0 rows. If the query filtered on an exact ID, code or name, check for near-matching values "
             "(another spelling, part of the value) before concluding that none exist.")
CONFIDENCE = re.compile(r"^\W*confidence\W*:?\W*(high|medium|low)\b\W*(.*)$", re.I)

# One neutral line per table (D59). Nothing here may hint at the planted problems in docs/DATA.md.
NOTES = {
    "sku_master": "one row per SKU: brand, flavor, pack, case_size (cans per case), co-packer line; "
                  "status is active, launch or discontinued",
    "distributor_orders": "distributor purchase orders, one SKU per PO line, quantities in cases; status is open, "
                          "confirmed, shipped or received; requested_date is the requested delivery date; pickup_date "
                          "and carrier are filled in once a carrier is assigned, and a confirmed PO with a pickup_date "
                          "is awaiting pickup; ship_date, shipped_qty and delivered_date record the shipment",
    "copacker_plan": "co-packer production runs; scheduled_week is the Monday of the run's week; status is "
                     "completed, cancelled, confirmed or planned",
    "warehouse_inventory": "weekly snapshot (Mondays) per warehouse and SKU, in cases; warehouses are WH-EAST, "
                           "WH-CENTRAL and WH-WEST",
    "promo_calendar": "retail promos; retailer is the parent company, chain is the store banner; authorized is "
                      "the authorization flag; ad_week is the ISO week of the start",
    "distributor_depletions": "each distributor's weekly depletion report by SKU, in cases; week_ending is a Friday",
}
assert tuple(NOTES) == tools.ALLOWED


def tool_specs():
    schema = "\n".join(f"- {t}({index.SCHEMA[t]}): {NOTES[t]}" for t in tools.ALLOWED)
    return [
        {"name": "run_sql",
         "description": f"Run one read-only DuckDB SELECT over these tables and return the rows. At most "
                        f"{tools.ROW_LIMIT} rows: aggregate or filter. Only these tables exist:\n{schema}",
         "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "one SELECT"}},
                        "required": ["query"], "additionalProperties": False}},
        {"name": "search_docs",
         "description": "Search ABC-BEV-CO's documents: the metric library, policies (PO changes, allocation, "
                        "promo authorization, escalation ownership, returns, distributor onboarding), product "
                        "sheets and operations notes. Returns the best-matching passages, each with an id to cite.",
         "parameters": {"type": "object", "properties": {
             "query": {"type": "string", "description": "what to look for, as a question or phrase"},
             "k": {"type": "integer", "description": f"passages to return, default {tools.settings()['k']}"}},
                        "required": ["query"], "additionalProperties": False}},
    ]


def passage_block(p):
    """D62: each passage is delimited and labelled as data."""
    return f'<passage id="{p["id"]}" doc="{p["doc_id"]}" title="{p["title"]}">\n{p["text"]}\n</passage>'


def run_tool(name, args):
    """(tool result text for the model, record for the evidence). Never raises: errors go back to the model."""
    try:
        if name == "run_sql":
            out = tools.run_sql(str(args.get("query", "")))
            shown = {k: out[k] for k in ("ok", "columns", "rows", "error") if k in out}
            if out["ok"] and not out["rows"]:
                shown["note"] = ZERO_ROWS
            content = json.dumps(shown, default=str)
            return content, {"tool": name, "sql": out["sql"], "ok": out["ok"], "error": out.get("error"),
                             "rows": len(out.get("rows", []))}
        if name == "search_docs":
            out = tools.search_docs(str(args.get("query", "")), args.get("k"))
            if not out["ok"]:
                content = json.dumps({"ok": False, "error": out["error"]})
            elif not out["passages"]:
                content = "No passage scored above the threshold."
            else:
                content = "\n\n".join(passage_block(p) for p in out["passages"])
            return content, {"tool": name, "query": args.get("query"), "ok": out["ok"], "error": out.get("error"),
                             "passages": [{"id": p["id"], "score": p["score"]} for p in out["passages"]]}
        error = f"unknown tool {name!r}; the tools are run_sql and search_docs"
    except Exception as e:      # the box unreachable, a bad k, ...
        error = f"{type(e).__name__}: {e}"
    return json.dumps({"ok": False, "error": error}), {"tool": name, "args": args, "ok": False, "error": error}


def split_confidence(text):
    """(answer without the confidence line, 'level - reason' or None)."""
    lines = text.rstrip().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if m := CONFIDENCE.match(lines[i].strip()):
            reason = m.group(2).strip(" -:")
            return "\n".join(lines[:i]).rstrip(), m.group(1).lower() + (f" - {reason}" if reason else "")
    return text.strip(), None


def ask(question, path="claude", model=None, max_tokens=MAX_TOKENS, budget="dev"):
    """Answer one question. Returns a dict: answer, confidence, flags, evidence, usage (see README)."""
    start = time.monotonic()
    messages = [{"role": "system", "content": SYSTEM_PROMPT.read_text()}, {"role": "user", "content": question}]
    specs, calls, steps, usage = tool_specs(), [], 0, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    text, stopped, last = "", "step_cap", {}
    while steps < STEP_CAP:
        try:
            last = adapter.call(path, messages, specs, model=model, max_tokens=max_tokens, budget=budget)
        except spend.CapReached as e:
            text, stopped = f"I don't know: the spend cap refused the model call ({e}).", "spend_cap"
            break
        except Exception as e:
            text, stopped = f"I don't know: the model call failed ({type(e).__name__}: {e}).", "error"
            break
        steps += 1
        for k in usage:
            usage[k] += last[k]
        if not last["tool_calls"]:
            text, stopped = last["text"], "answer"
            break
        messages.append(last["message"])
        for c in last["tool_calls"]:
            content, record = run_tool(c["name"], c["args"])
            calls.append(record)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": content})
    if stopped == "step_cap":
        text = f"I don't know: the step limit ({STEP_CAP} model calls) was reached before an answer."

    answer, confidence = split_confidence(text)
    returned = {p["id"] for c in calls for p in c.get("passages", [])}
    cited = list(dict.fromkeys(CITATION.findall(answer)))
    flags = []
    if stopped != "answer":
        flags.append(f"stopped: {stopped}")
        confidence = "low - no answer was reached"
    elif confidence is None:
        flags.append("the model gave no confidence line")
    if last.get("stop") in ("max_tokens", "length"):
        flags.append(f"the last model call stopped at max_tokens ({max_tokens})")
    if any(c["tool"] == "search_docs" and c["ok"] and not c["passages"] for c in calls):
        flags.append("a search returned no passage above the threshold")
    if any(not c["ok"] for c in calls):
        flags.append("a tool call returned an error")
    if missing := [p for p in cited if p not in returned]:
        flags.append(f"cites passages the search never returned: {', '.join(missing)}")

    result = {
        "question": question, "path": path, "model": last.get("model") or model or adapter.DEFAULT[path],
        "answer": answer, "confidence": confidence or "unstated", "flags": flags,
        "evidence": {"sql": [{k: c[k] for k in ("sql", "ok", "error", "rows")} for c in calls if c["tool"] == "run_sql"
                             and "sql" in c],
                     "passages_cited": [p for p in cited if p in returned],
                     "passages_retrieved": sorted(returned)},
        "tool_calls": calls, "stopped": stopped, "steps": steps,
        **usage, "cost_usd": round(usage["cost_usd"], 6), "latency_s": round(time.monotonic() - start, 2),
    }
    RUN_LOG.parent.mkdir(exist_ok=True)
    with RUN_LOG.open("a") as f:
        f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), **result}) + "\n")
    return result


def render(r):
    """The CLI's text form of a result."""
    out = [r["answer"], "", "Evidence:"]
    for s in r["evidence"]["sql"]:
        out.append(f"  SQL ({'ok, ' + str(s['rows']) + ' rows' if s['ok'] else 'refused: ' + s['error']}):")
        out += [f"    {line}" for line in s["sql"].strip().split("\n")]
    cited = r["evidence"]["passages_cited"]
    out.append(f"  Passages cited: {', '.join(cited) if cited else 'none'}")
    if not r["evidence"]["sql"] and not r["evidence"]["passages_retrieved"]:
        out.append("  (no tool was used)")
    out += ["", f"Confidence: {r['confidence']}"]
    out += [f"Flag: {f}" for f in r["flags"]]
    out.append(f"\n[{r['path']} {r['model']}: {r['steps']} model calls, {r['input_tokens'] + r['output_tokens']:,} "
               f"tokens, ${r['cost_usd']:.4f}, {r['latency_s']:.1f} s]")
    return "\n".join(out)
