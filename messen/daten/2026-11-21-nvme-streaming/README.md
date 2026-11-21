# A bigger quant with experts streamed from the NVMe

**English** · [Deutsch](README.de.md)

As of 21 Nov 2026. Every number is measured, on an RX 7900 XTX in the dock of a NAS with 62 GB RAM, on my own build strata-xtx (xtx-2 on Strata 0.2.17).

Strata can run a model that does not fit into VRAM and RAM together: what the expert cache on the card and a RAM budget (`--resident-budget-gib`) do not hold is read from the model file while it answers. The NAS has a fast NVMe pool (2 × 2 TB, RAID 1), so I checked whether a bigger and more exact quant of the same 125B model is worth it. My file in use is IQ3_XXS with 75.8 GB and fits into VRAM + RAM. The candidates were Unsloth's UD-IQ4_XS (93.7 GB) and UD-Q4_K_XL (111 GB), each with a RAM budget of 45 GiB.

## Result in short: it does not pay off

| quiet mode, median of 2 × 900 tokens | IQ3_XXS (in use) | UD-IQ4_XS | UD-Q4_K_XL |
|---|---:|---:|---:|
| decode, original (tok/s) | 61.6 | 45.8 | 23.6 |
| decode, uncensored version (tok/s) | 61.0 | 43.6 | 24.2 |
| read from the NVMe per answer of 900 tokens | 0.1 GB | 0.1–0.2 GB | 21–23 GB |
| reading a 58K prompt, uncensored (tok/s) | 3,237 | 2,605 | 2,050 |
| read from the NVMe for that prompt | 0.04 GB | 19.6 GB | 61.3 GB |
| follow-up question after the 58K text (tok/s) | 55.6 | 35.1 | 21.3 |
| RAM available after loading, uncensored | 7.7 GiB | 2.4 GiB | 2.3 GiB |
| task set, 102 graded tasks (original / uncensored) | 96 / 96 | 95 / 96 | not run |
| task set, wall time (original / uncensored) | 22.0 / 23.3 min | 35.1 / 36.6 min | – |

- **No gain in quality.** On my German task set UD-IQ4_XS passes as many tasks as the IQ3_XXS file in use (one task either way is within the run-to-run spread), but needs about 55 % more time for the whole set.
- **UD-IQ4_XS is slower without touching the NVMe much while writing.** The bigger experts mean fewer of them fit into the card's cache, so more of them are computed from RAM on the CPU: −28 % decode. The NVMe only comes in on long prompts (19.6 GB read for 58K tokens).
- **UD-Q4_K_XL reads from the NVMe on every answer**, 21–23 GB for 900 tokens, and writes at less than half the speed. With a smaller budget (35 GiB) more RAM stays free (10.2 GiB), but decode drops to 21 tok/s and one answer reads 41 GB.
- **Memory gets too tight for a NAS.** With either bigger file only about 2.3 GiB of RAM stay available beside the NAS services; my rule for anything in daily use is at least 3 GiB.
- **Max mode does not change the picture** (uncensored version: 64.8 against 42.5 and 24.5 tok/s).
- Everything else worked on all files: tool call, image input, the hidden number found in every prompt, no error lines, swap unchanged. The variant with control vector loads on both Unsloth files and the vector takes effect (five requests that models often refuse: 5 of 5 answered on each).

Streaming from the NVMe only makes sense here if a clearly better model exists only in a size that does not fit. For this model it does not.

## Files

| File | Content |
|---|---|
| `speed.json` | 10 runs (7 quiet, 3 max): load, decode, prompts 4K/16K/58K with needle, follow-up, NVMe bytes read and lowest available RAM per step, the engine's own budget and cache lines |
| `task-set-summary.json` | the task set for original and uncensored version, IQ3_XXS against UD-IQ4_XS, per category and wall time |

## Conditions

- 20 Nov 2026 (speed) and 21 Nov 2026 (task set), context 131,072, card quiet (2,800 MHz, −100 mV) unless marked max.
- Packs of the Unsloth files built with `tools/iq_pack.py --compat-bf16`.
- The engine caps a budget of 45 GiB at what is available: 44.02 GiB on this NAS. Its own warning for long prompts is in `speed.json` (`engine_notes`).
- NVMe bytes from the block device counters, RAM from `MemAvailable`, both sampled while each step ran.
- The task set ran in alternating order (original IQ3, original IQ4, uncensored IQ3, uncensored IQ4) without other load; the agent on the NAS was paused.
