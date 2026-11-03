"""One-line smoke test per model path (T4): python agent/smoke.py local|cloud|claude [model]

Offers one tool, expects the model to call it, sends the result back and expects the answer in text.
That exercises text, tool calls, tokens, latency, cost and the spend log in two small calls.
Paid paths cost well under a cent; both calls go through the cap like any other.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent import adapter

ADD = {"name": "add", "description": "Add two integers.",
       "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                      "required": ["a", "b"], "additionalProperties": False}}


def main():
    path, model = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    messages = [{"role": "user", "content": "Use the add tool to add 17 and 25, then reply with just the sum."}]
    first = adapter.call(path, messages, [ADD], model=model, max_tokens=2048)
    if not first["tool_calls"]:
        sys.exit(f"FAIL {path}: no tool call; text was {first['text']!r}")
    call = first["tool_calls"][0]
    messages += [first["message"], {"role": "tool", "tool_call_id": call["id"], "content": str(sum(call["args"].values()))}]
    second = adapter.call(path, messages, [ADD], model=model, max_tokens=2048)
    ok = call["name"] == "add" and call["args"] == {"a": 17, "b": 25} and "42" in second["text"]
    cost, tokens = first["cost_usd"] + second["cost_usd"], sum(r["input_tokens"] + r["output_tokens"] for r in (first, second))
    extra = f", host {first.get('host')}, billed ${(first.get('billed_usd') or 0) + (second.get('billed_usd') or 0):.6f}" \
        if path == "cloud" else ""
    print(f"{'PASS' if ok else 'FAIL'} {path} {first['model']}: tool call {call['args']}, answer {second['text'].strip()!r}, "
          f"{tokens} tokens, {first['latency_s'] + second['latency_s']:.1f} s, ${cost:.6f}{extra}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
