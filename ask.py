"""Ask the assistant one question (T6): python ask.py "question" --model local|cloud|claude

Prints the answer, its evidence (the SQL that ran and the passages cited) and a confidence note.
--json prints the full result dict instead. Paid paths go through the spend cap (D44, D45).
"""
import argparse, json, sys

from agent import loop


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("question")
    parser.add_argument("--model", choices=["local", "cloud", "claude"], default="claude", help="model path")
    parser.add_argument("--name", help="a specific model on that path, e.g. qwen/qwen3-14b")
    parser.add_argument("--max-tokens", type=int, default=loop.MAX_TOKENS, help="per model call (D66)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    a = parser.parse_args()
    r = loop.ask(a.question, path=a.model, model=a.name, max_tokens=a.max_tokens)
    print(json.dumps(r, indent=2) if a.json else loop.render(r))
    sys.exit(0 if r["stopped"] == "answer" else 1)


if __name__ == "__main__":
    main()
