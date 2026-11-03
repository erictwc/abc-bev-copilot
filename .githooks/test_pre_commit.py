#!/usr/bin/env python3
"""Prove the secret scan works from a fresh clone, the way a new user gets it.

Clones the committed repo into a temp folder, runs `make setup` there, then
tries commits that must be blocked and one that must go through. The fake keys
are assembled at runtime so that this file does not trip the scan itself.
Nothing leaves the machine: the clone is local and the keys are not real.
"""
import os
import subprocess
import sys
import tempfile

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, check=True).stdout.strip()

FAKE = "x9" * 20
CASES = [
    # (description, file name, content, should_block)
    ("fake Anthropic key", "agent/settings.py", 'KEY = "sk-' + "ant-" + FAKE + '"\n', True),
    ("credential assignment", "agent/conf.py", "service_api_" + "key = " + FAKE + "\n", True),
    ("private key block", "id_test", "-----BEGIN RSA " + "PRIVATE KEY-----\n", True),
    ("staged .env file", ".env", "ANTHROPIC_API_KEY=\n", True),
    ("ordinary code", "agent/hello.py", 'print("no secrets here")\n', False),
]


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        clone = os.path.join(tmp, "clone")
        run(["git", "clone", "-q", ROOT, clone], tmp)
        setup = run(["make", "setup"], clone)
        print(f"make setup in fresh clone: exit {setup.returncode}")
        if setup.returncode != 0:
            print(setup.stdout + setup.stderr)
            return 1

        for desc, name, content, should_block in CASES:
            path = os.path.join(clone, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            run(["git", "add", "-f", name], clone)
            commit = run(["git", "commit", "-q", "-m", f"test: {desc}"], clone)
            blocked = commit.returncode != 0
            ok = blocked == should_block
            failures += not ok
            want = "blocked" if should_block else "allowed"
            got = "blocked" if blocked else "allowed"
            print(f"{'PASS' if ok else 'FAIL'}  {desc}: want {want}, got {got}")
            if blocked:
                print("      " + commit.stderr.strip().replace("\n", "\n      "))
            if blocked:
                run(["git", "reset", "-q", "HEAD", "--", name], clone)
                os.remove(path)

    print(f"\n{len(CASES) - failures}/{len(CASES)} secret-scan cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
