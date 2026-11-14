# GPU projection (T11)

**Every GPU figure in this document is projected, not measured.** None of these GPUs was used for
this project. The only measured hardware is the GEEKOM A5 (Ryzen 5 7430U, 16 GB, CPU only, Ubuntu).
The GPU numbers come from the box's measurements and from vendor spec sheets, using the formulas
in `SPEC.md` §7. Decisions D100-D103 (2026-11-14) set the GPUs, the efficiency ranges, the per-case
method and the rented GPU hour.

Quality does not change with hardware. The same model at the same quantization (`q4_K_M`) gives the
same answers on a GPU. A GPU changes only speed. The quality of larger models comes from the cloud
Qwen runs (D39).

## 1. Measured inputs (the box)

Medians of the three measured runs in `bench/results.csv` (T3, Ollama 0.40.14, 2026-11-03,
D34-D38). Each run generated 128 tokens.

| Model (Ollama tag) | Prompt tokens | Prefill tok/s | Decode tok/s |
|---|---:|---:|---:|
| `qwen3.5:4b-q4_K_M` | 512 / 2,048 / 8,192 | 51.2 / 50.1 / 45.3 | 11.78 / 10.34 / 7.71 |
| `qwen3.5:9b-q4_K_M` | 512 / 2,048 / 8,192 | 28.1 / 27.8 / 26.6 | 6.68 / 6.12 / 5.00 |
| `qwen3:14b-q4_K_M` | 512 / 2,048 / 8,192 | 15.1 / 14.3 / 12.0 | 4.10 / 3.54 / 2.43 |

Per-case tokens and latency come from the committed T10 local run,
`evals/results/2026-11-14T0419Z_local_qwen3.5-9b-q4_K_M.csv` (commit `486241d`): 40 cases, median
287.6 s, maximum 950.8 s, 200.3 minutes for all 40. That run used the D40 context guard. The D95
rerun is not committed yet and is not used here.

## 2. Sources

Spec-sheet figures, read on 2026-11-14.

| Hardware | Memory | Bandwidth | Dense FP16 tensor | Source |
|---|---:|---:|---:|---|
| Ryzen 5 7430U (the box) | DDR4-3200, 2 channels | 51.2 GB/s (a) | not used | [AMD product page](https://www.amd.com/en/products/processors/laptop/ryzen/7000-series/amd-ryzen-5-7430u.html): "Max Memory Speed 2x1R DDR4-3200", "Memory Channels 2" |
| GEEKOM A5 | 16 GB DDR4, dual channel | (speed not stated) | - | [GEEKOM A5 page](https://www.geekompc.com/geekom-a5-mini-pc/): "dual-channel DDR4 memory" |
| RTX 5060 Ti 16 GB | 16 GB GDDR7 | 448 GB/s | 94.7 TFLOPS (b) | [NVIDIA 50 Series compare page](https://www.nvidia.com/en-us/geforce/graphics-cards/compare/#50-series): "448 GB/sec"; [RTX 5060 family page](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5060-family/): 4608 CUDA cores, 2.57 GHz boost |
| NVIDIA L4 | 24 GB | 300 GB/s | 121 TFLOPS (c) | [NVIDIA L4 page](https://www.nvidia.com/en-us/data-center/l4/): "GPU memory bandwidth 300GB/s", "FP16 Tensor Core 242 teraFLOPS*", "* Shown with sparsity" |
| RTX 5090 | 32 GB GDDR7 | 1,792 GB/s | 419 TFLOPS (d) | [NVIDIA RTX Blackwell architecture whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf), Appendix A, Table 3: "Peak FP16 Tensor TFLOPS with FP16 Accumulate 419/838", "Memory Bandwidth 1792 GB/sec"; footnote 2: the second figure uses sparsity |
| H100 SXM | 80 GB | 3,350 GB/s | 989.5 TFLOPS (c) | [NVIDIA H100 page](https://www.nvidia.com/en-us/data-center/h100/): "GPU Memory Bandwidth 3.35TB/s", "FP16 Tensor Core* 1,979 teraFLOPS", "* With sparsity" |

Notes:

- (a) 3,200 MT/s × 8 bytes × 2 channels. The GEEKOM page does not give the memory speed, and the
  module layout (2 × 8 GB or 1 × 16 GB) was not checked on the box. The measured decode rate shows
  the box is dual channel (section 3). **The GPU results do not depend on this figure**, because it
  cancels out of the decode formula.
- (b) Derived. NVIDIA does not publish this figure on the pages read. The RTX 5090's 419 TFLOPS
  across 170 SMs at 2,407 MHz (same whitepaper table) is 1.024 TFLOPS per SM per GHz. The 5060 Ti
  has 4,608 / 128 = 36 SMs at 2.57 GHz (128 CUDA cores per SM, whitepaper), so 36 × 2.57 × 1.024 =
  94.7 TFLOPS.
- (c) The vendor page gives the figure with sparsity. The dense figure is half of it.
- (d) For GeForce cards NVIDIA lists two dense FP16 rates. On the 5090 they are 419 TFLOPS (FP16
  accumulate) and 209.5 TFLOPS (FP32 accumulate). This document uses FP16 accumulate, which is half
  of the dense INT8 rate (838 TOPS). If Ollama's kernels run at the FP32-accumulate rate, the
  GeForce prefill figures are halved. Decode does not change.

Model figures:

| Model | Parameters N | Bytes read per token | Source |
|---|---:|---:|---|
| `qwen3.5:9b-q4_K_M` | 8.95 B | 5.6 GB | [Ollama tag page](https://ollama.com/library/qwen3.5:9b-q4_K_M): "parameters 8.95B", text weights 5.6 GB. The 6.55 GB tag also holds a 922 MB vision projector, which a text answer does not read. |
| `qwen3.5:4b-q4_K_M` | 4 B | not used | [Qwen3.5-4B model card](https://huggingface.co/Qwen/Qwen3.5-4B): "Number of Parameters: 4B" |
| `qwen3:14b-q4_K_M` | 14.8 B | 9.28 GB | [Qwen3-14B model card](https://huggingface.co/Qwen/Qwen3-14B): "Number of Parameters: 14.8B"; the size is from `bench/results.csv` (text only, no projector) |

The rule that a forward pass costs about 2N floating-point operations per token comes from Kaplan
et al., *Scaling Laws for Neural Language Models* (2020),
[arXiv:2001.08361](https://arxiv.org/abs/2001.08361), section 2.1.

## 3. Formulas

**Decode** is limited by memory bandwidth. Each new token reads the weights once.

- The box's efficiency is `e_box = decode_box(512) × bytes_per_token / BW_box` = 6.68 × 5.6 / 51.2 =
  **0.73** for the 9B. The 14B gives 4.10 × 9.28 / 51.2 = 0.74. The 9B figure means the box moved
  37.4 GB/s, which is more than one DDR4-3200 channel can carry (25.6 GB/s). That shows the box runs
  dual channel.
- The GPU decode rate is `decode_gpu(ctx) = decode_box(ctx) × (BW_gpu / BW_box) × (e_gpu / e_box)`,
  with **e_gpu from 0.5 to 0.8** (D101).
- At 512 tokens this reduces to `e_gpu × BW_gpu / bytes_per_token`. The box's bandwidth cancels out.
  At longer prompts, the formula keeps the box's measured slowdown from reading the KV cache.
- The 9B's e_box (0.73) is also used for the 4B and the 14B. The 14B check above agrees within 2%.
  The 4B was not checked. Its text weights were not split from its projector.

**Prefill** is limited by compute. Each prompt token costs about 2N operations.

- The GPU prefill rate is
  `prefill_gpu(ctx) = e_gpu × FP16_dense_gpu / (2N) × prefill_box(ctx) / prefill_box(512)`, with
  **e_gpu from 0.3 to 0.6** of dense FP16 tensor peak (D101).
- The last factor carries over the box's measured slowdown at long prompts. This assumes the GPU
  slows by the same fraction. For the 9B the slowdown is small (5% at 8,192). Per its
  [model card](https://huggingface.co/Qwen/Qwen3.5-9B), only 8 of its 32 layers use full attention.
- For comparison, the box's measured 9B prefill is 2 × 8.95 B × 28.1 = 503 GFLOPS achieved.

Speed-up over the box for the 9B:

| GPU | Decode × | Prefill × |
|---|---:|---:|
| RTX 5060 Ti 16 GB | 6.0-9.6 | 56-113 |
| NVIDIA L4 | 4.0-6.4 | 72-144 |
| RTX 5090 | 24-38 | 250-500 |
| H100 SXM | 45-72 | 590-1,180 |

## 4. Projected tokens per second (projected, not measured)

Each cell gives prefill tok/s, then decode tok/s, as low-high ranges. The "Box" column is measured.
Every other column is projected, not measured. All four GPUs hold all three models: the largest
(`qwen3:14b`) is 9.3 GB, and the 9B with `num_ctx` 16,384 was measured loading as 6.7 GB (D95).

| Model | Prompt | Box (measured) | RTX 5060 Ti 16 GB | NVIDIA L4 | RTX 5090 | H100 SXM |
|---|---:|---|---|---|---|---|
| 4B | 512 | 51 / 11.8 | 3,551-7,102 / 71-113 | 4,538-9,075 / 47-76 | 15,712-31,425 / 282-451 | 37,106-74,212 / 527-844 |
| 4B | 2,048 | 50 / 10.3 | 3,480-6,961 / 62-99 | 4,447-8,894 / 41-66 | 15,399-30,798 / 248-396 | 36,366-72,733 / 463-741 |
| 4B | 8,192 | 45 / 7.7 | 3,145-6,290 / 46-74 | 4,019-8,037 / 31-49 | 13,916-27,832 / 185-295 | 32,863-65,727 / 345-552 |
| 9B | 512 | 28 / 6.7 | 1,587-3,174 / 40-64 | 2,028-4,056 / 27-43 | 7,022-14,045 / 160-256 | 16,584-33,168 / 299-479 |
| 9B | 2,048 | 28 / 6.1 | 1,572-3,144 / 37-59 | 2,008-4,017 / 25-39 | 6,955-13,910 / 147-235 | 16,425-32,849 / 274-438 |
| 9B | 8,192 | 27 / 5.0 | 1,501-3,002 / 30-48 | 1,918-3,835 / 20-32 | 6,640-13,280 / 120-192 | 15,681-31,362 / 224-358 |
| 14B | 512 | 15 / 4.1 | 960-1,920 / 25-39 | 1,226-2,453 / 16-26 | 4,247-8,493 / 98-157 | 10,029-20,057 / 184-294 |
| 14B | 2,048 | 14 / 3.5 | 913-1,825 / 21-34 | 1,166-2,332 / 14-23 | 4,038-8,076 / 85-136 | 9,536-19,073 / 159-254 |
| 14B | 8,192 | 12 / 2.4 | 765-1,530 / 15-23 | 977-1,955 / 10-16 | 3,384-6,769 / 58-93 | 7,992-15,985 / 109-174 |

The L4 has more compute than the 5060 Ti but less bandwidth. So it reads prompts faster and writes
answers more slowly.

## 5. Projected eval latency per case, 9B (projected, not measured)

The case token counts cannot simply be divided by the rates in section 4. `input_tokens` in the
result file counts the whole prompt at every agent step, but Ollama reuses the cached prompt prefix
between steps. Its real prefill work is smaller than the count. On the 0419Z run, the measured
latency is a median 0.60 of `input/prefill + output/decode`, and 0.34-0.41 on the 7-8 step cases.
So each case's measured time is split instead (D102):

1. Decode time on the box = `output_tokens / decode_box`. The box rate is taken as 6.12 tok/s (the
   2,048 rate, fast end) to 5.00 tok/s (the 8,192 rate, slow end). For E04, E23, E39 and E40,
   output / 5.00 is more than the whole measured latency. At the slow end those cases are counted as
   all decode.
2. Everything else in the measured latency is prefill plus overhead.
3. Each part is divided by its own speed-up from section 3. The fast end uses the high efficiencies
   with the 6.12 split. The slow end uses the low efficiencies with the 5.00 split.

| | Median per case | Slowest case | All 40 cases |
|---|---:|---:|---:|
| Box, measured (0419Z) | 287.6 s | 950.8 s | 200 min |
| RTX 5060 Ti 16 GB, projected | 19-37 s | 72-138 s | 15-28 min |
| NVIDIA L4, projected | 28-55 s | 105-204 s | 22-42 min |
| RTX 5090, projected | 4.7-9.1 s | 18-34 s | 3.7-7.1 min |
| H100 SXM, projected | 2.5-4.9 s | 9.5-18 s | 2.0-3.8 min |
| Cloud Qwen 9B, measured (0302Z, bf16 on a hosted GPU) | 13.7 s | 56.4 s | - |
| Claude Sonnet, measured (0412Z) | 7.1 s | 14.6 s | - |

The two cloud rows are measured, from `evals/results/2026-11-14T0302Z_cloud_qwen-qwen3.5-9b.md` and
`evals/results/2026-11-14T0412Z_claude_claude-sonnet-5-5.md`. Those runs wrote different answers with
different token counts, so they are context, not a like-for-like comparison.

Limits of this table:

- **Tool calls and network time are scaled as if they were prefill.** T10 did not time them
  separately. The SQL, the doc-search embeddings (which run on the box's CPU) and the hops from the
  Mac to the box would not get faster on a GPU. The fast end of each range is therefore optimistic,
  most of all on the H100 and the 5090.
- At the slow end, about 98% of the projected time is decode. On a GPU the answer is
  bandwidth-bound, as on the box.
- The 0419Z run includes cases that ended in errors (E03, E26 and E33 hit the old context guard; on
  E31 the box dropped the connection) and cases that hit the step cap. They are projected as they
  ran.

## 6. Not done

- **No GPU was measured.** The optional rented GPU hour (SPEC §7) was skipped for v1 (D103). Running
  `bench/run_bench.py` on one rented card would test the decode efficiency range directly. That is a
  v2 item.
- The D95 rerun is not used. If it is committed later, section 5 can be recomputed with the same
  script.

## Appendix: the script that produced sections 3-5

The script uses only the standard library and makes no network calls. Run it from the repo root.

```python
import csv, statistics as st
rows = list(csv.DictReader(open("bench/results.csv")))
acc = {}
for r in rows:
    k = (r["model"], int(r["num_ctx"]) - 192)
    acc.setdefault(k, ([], []))
    acc[k][0].append(float(r["prefill_tps"])); acc[k][1].append(float(r["decode_tps"]))
med = {k: (st.median(p), st.median(d)) for k, (p, d) in acc.items()}
NINE = "qwen3.5:9b-q4_K_M"
BOX_BW, TEXT_GB = 51.2, 5.6
E_BOX = med[(NINE, 512)][1] * TEXT_GB / BOX_BW                  # 0.73
GPU = {"RTX 5060 Ti 16 GB": (448, 94.7), "NVIDIA L4": (300, 121),
       "RTX 5090": (1792, 419), "H100 SXM": (3350, 989.5)}      # GB/s, dense FP16 TFLOPS
N = {"qwen3.5:4b-q4_K_M": 4e9, NINE: 8.95e9, "qwen3:14b-q4_K_M": 14.8e9}
ED, EP = (0.5, 0.8), (0.3, 0.6)                                  # D101
md = lambda g, e: GPU[g][0] / BOX_BW * e / E_BOX                 # decode speed-up
gp = lambda g, m, e: e * GPU[g][1] * 1e12 / (2 * N[m])           # prefill tok/s at 512
for m in N:                                                      # section 4
    for c in (512, 2048, 8192):
        bp, bd = med[(m, c)]
        print(m, c, *[[round(gp(g, m, e) * bp / med[(m, 512)][0]) for e in EP] for g in GPU],
              *[[round(bd * md(g, e)) for e in ED] for g in GPU])
cases = list(csv.DictReader(open("evals/results/2026-11-14T0419Z_local_qwen3.5-9b-q4_K_M.csv")))
D_FAST, D_SLOW = med[(NINE, 2048)][1], med[(NINE, 8192)][1]
P512 = med[(NINE, 512)][0]
for g in GPU:                                                    # section 5
    fast, slow = [], []
    for c in cases:
        L, o = float(c["latency_s"]), int(c["output_tokens"])
        td = min(o / D_FAST, L); fast.append(td / md(g, ED[1]) + (L - td) / (gp(g, NINE, EP[1]) / P512))
        td = min(o / D_SLOW, L); slow.append(td / md(g, ED[0]) + (L - td) / (gp(g, NINE, EP[0]) / P512))
    print(g, st.median(fast), st.median(slow), max(fast), max(slow), sum(fast) / 60, sum(slow) / 60)
```
