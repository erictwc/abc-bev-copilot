#!/bin/sh
# Write the Hugging Face Space's files to a folder (T14, D113): the committed tree at HEAD, with the
# Dockerfile and the Space's README at its root. Only tracked files go in, so .env, logs/ and the
# local .duckdb stores never do. Usage: sh demo/build_space.sh <folder, e.g. a clone of the Space repo>
set -e
out=${1:?usage: sh demo/build_space.sh <folder>}
cd "$(git rev-parse --show-toplevel)"
[ -z "$(git status --porcelain -- demo agent data docs_corpus config.toml requirements.txt evals/results)" ] \
  || echo "warning: uncommitted changes in files the image uses; only HEAD is packed" >&2
mkdir -p "$out"
find "$out" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
git archive HEAD | tar -x -C "$out"
cp demo/Dockerfile "$out/Dockerfile"
cp demo/space/README.md "$out/README.md"
printf '.git\n' > "$out/.dockerignore"
echo "Space files from $(git rev-parse --short HEAD) written to $out"
