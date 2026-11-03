# bench/

Prefill and decode benchmarks from the GEEKOM box (`results.csv`, T3) and the GPU projection
(`PROJECTION.md`, T11). Every GPU figure is labeled **projected, not measured**.

## Running the box benchmark (T3)

`run_bench.py` sends requests to Ollama on the box and records the timings Ollama measures on the
server (D34). Standard library only. Its only network call goes to `OLLAMA_HOST`, and it refuses
any address that is not private or loopback.

```sh
make bench                       # all three models, OLLAMA_HOST from the environment or .env
python3 bench/run_bench.py --models qwen3:14b-q4_K_M   # one model, e.g. on another night
```

It runs from any machine on the home network, or on the box itself with
`--host 127.0.0.1:11434`. The numbers are the same either way, because Ollama times the work on
the box.

The models have to be pulled on the box first (D35):

```sh
ollama pull qwen3.5:4b-q4_K_M
ollama pull qwen3.5:9b-q4_K_M
ollama pull qwen3:14b-q4_K_M
```

## What one run does

For each model and each prompt length of 512, 2,048 and 8,192 tokens (D36):

1. Warm-up requests, discarded. They load the model and tune a plain-English filler prompt to
   within 3% of the target token count (D37).
2. Three measured requests. Each one generates 128 tokens with `num_ctx` set to the prompt length
   plus 192, so the prompt is never cut.
3. When a model is done, it is unloaded so that the next one has the RAM.

Every request starts with a fresh random nonce, because Ollama skips prompt tokens it has cached.
If a measured run reports fewer prompt tokens than expected, the script stops with an error
instead of writing the row.

## `results.csv`

One row per measured run, appended (D38):

| Column | Meaning |
|---|---|
| `timestamp` | UTC time of the run |
| `host` | a label (`GEEKOM-A5`), never an address |
| `ollama_version` | from `/api/version` |
| `model`, `quant`, `size_gb` | Ollama tag, quantization level and file size from `/api/tags` |
| `num_ctx` | context window for the request: the prompt length plus 192 |
| `prompt_tokens` | `prompt_eval_count`, the prompt tokens Ollama actually read |
| `gen_tokens` | `eval_count`, normally 128 |
| `repeat` | 1 to 3 |
| `prefill_tps` | `prompt_eval_count / prompt_eval_duration` |
| `decode_tps` | `eval_count / eval_duration` |
| `load_s` | `load_duration`, near zero once the model is warm |

If a run stops partway, the rows it already wrote are real measurements and stay in the file.
