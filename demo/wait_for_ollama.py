"""Wait up to 60 s for the container's own Ollama on loopback (T14)."""
import sys, time, urllib.request

for _ in range(120):
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=2)
        sys.exit(0)
    except OSError:
        time.sleep(0.5)
sys.exit("Ollama did not start on 127.0.0.1:11434")
