# The hosted demo's image (T14, D112-D114). Built by Hugging Face Spaces from the folder that
# demo/build_space.sh writes; see demo/README.md. Runtime outbound hosts are the same two as the
# CLI: api.anthropic.com and openrouter.ai. Ollama listens on loopback only.

# Ollama, the same version as the GEEKOM box (0.40.14), CPU only: the GPU libraries are dropped.
FROM ollama/ollama:0.40.14 AS ollama
RUN rm -rf /usr/lib/ollama/cuda* /usr/lib/ollama/rocm* /usr/lib/ollama/vulkan*

FROM python:3.12-slim
COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama /usr/lib/ollama

RUN useradd -m -u 1000 user
WORKDIR /app
# WORKDIR makes /app root-owned and COPY --chown only covers what it copies, so the app could not
# create logs/ (first Space build, 2026-11-14) and start.sh could not link it to /data.
RUN chown user:user /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
ENV HOME=/home/user OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS=/home/user/.ollama/models \
    DEMO_PROXY_HOPS=1 PYTHONUNBUFFERED=1

# Build both stores in the image with the same embedder the app queries at run time, then check
# retrieval as T5 did: five questions must find the right document first and six off-topic ones
# nothing (D56's threshold). The build fails if they do not. The model pull is the only
# build-time download besides the base images and pip (D112).
RUN python -m agent.index db \
 && (ollama serve >/tmp/ollama.log 2>&1 &) \
 && python demo/wait_for_ollama.py \
 && ollama pull qwen3-embedding:0.6b \
 && python -m agent.index docs \
 && python -m unittest -v agent.test_retrieval \
 && python -m unittest demo.test_server

EXPOSE 7860
CMD ["sh", "demo/start.sh"]
