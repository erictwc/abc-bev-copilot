#!/bin/sh
# Container entry point (T14). The spend log and request log must survive a restart, or the demo
# cap would reset (D113, D115): they go on the Space's persistent disk at /data. Without it, live
# answers are switched off and only the replays work.
set -e
if [ -d /data ] && [ -w /data ]; then
  mkdir -p /data/logs
  rm -rf /app/logs && ln -s /data/logs /app/logs
else
  echo "no writable /data: live answers are off, so the spend cap cannot be reset by a restart" >&2
  export DEMO_LIVE=off
fi
ollama serve >/tmp/ollama.log 2>&1 &
python demo/wait_for_ollama.py
exec python -m demo.server --host 0.0.0.0 --port 7860
