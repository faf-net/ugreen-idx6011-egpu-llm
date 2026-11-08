# Measurements of 2026-11-08: Strata 0.2.12 on this gfx1100, and the tuned DFlash2 drafter

Prebuilt engine 0.1.58 `hip-rx7900` with control 0.1.58 (SHA-256 checked against the release's `SHA256SUMS.txt`), compared with the 0.2.11 packages (engine and control 0.1.57) that this machine served with until then. Same run config as before, only engine and control swapped: IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB, default pool workers. The Docker image `ghcr.io/niko1221/strata:0.2.12-rocm-gfx110x` is included with its defaults.

New this time: **Strata's tuned DFlash2 drafter** (`qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack`, fetched from the v0.2.12 release assets, SHA-256 `4df2e5ab…664c` as pinned in `strata_control/drafting.py`). As far as I can tell it had not been measured on gfx1100.

The NAS services were running for everything here; only my agent was paused. The automated night run (version pairs, needles, fresh engines, `strata_bench.py`, Docker image) ran at about 02:00 local time with other background jobs active. Its package `standard-v1` came out low (short decode 53.9 tok/s) and is **replaced** by a clean re-run the same evening (`standard-v1/package-0.2.12/`).

The same data went to Strata as [issue #TBD](https://github.com/Niko1221/Strata/issues).

| File | What |
|---|---|
| `standard-v1/package-0.2.12/` | `strata bench run --suite standard-v1 --track custom` against the 0.2.12 packages with this run config (evening re-run): complete |
| `standard-v1/docker-image-0.2.12-default/` | the unchanged Docker image (`MODEL=IQ3_XXS`, `API_KEY` only), `--track default` (night run): complete |
| `strata-bench/`, `needles-32k-128k.json`, `needles-250k.json` | `tools/strata_bench.py --long` and `tools/needle_bench.py` on 0.2.12 (night run) |
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.12 (`t-neu`) against 0.2.11 (`t-prod`), fresh engine per run, 63-token prompt, 900 tokens out, temperature 0 |
| `fresh-engines.jsonl` | 8 fresh 0.2.12 engines with MTP, two ~3.8K prompts each |
| `drafter-fixed-900.jsonl` | drafter test on 0.2.12: 5 variants × 2 clock profiles × 2 rounds, a fresh engine per variant and round, 3 prompts (story, code, code sampled) × 2, capped at 900 tokens |
| `task-set-summary.json` | my own task set (114 German-language tasks, 102 auto-graded, temperature 0, thinking on, up to 8,000 tokens): 0.2.11 MTP, 0.2.12 MTP and 0.2.12 with the tuned DFlash2, per category |

## 0.2.12 against 0.2.11

| | 0.2.12 | 0.2.11 |
|---|---:|---:|
| pairs, same session: decode tok/s | 59.9 (54.9-62.8) | 61.2 (58.6-62.6) |
| pairs: 63-token prompt tok/s | 106.9 | 111.3 |
| task set: passed (of 102 auto-graded) | 98 | 98 |
| task set: wall time, 114 tasks | 1,430 s | 1,431 s |
| task set: decode median | 75.6 | 74.7 |
| `standard-v1`, package: short decode / 4K / 16K prompt | 63.6 / 788.4 / 1,201.7 | 67.0 / 796.6 / 1,191.5 * |
| `standard-v1`, Docker image defaults: short decode / 4K / 16K prompt | 69.1 / 756.3 / 1,185.8 | 65.0 / 757.6 / 1,181.7 * |
| `strata_bench.py --long`: chat / agent decode, 4K / 16K / 32K prompt | 68.1 / 73.2, 781 / 1,200 / 1,217 | 64.3 / 80.9, 781 / 1,212 / 1,226 * |

\* 0.2.11 runs of 5 Nov, not the same session. Only the pairs and the task set ran both versions back to back.

- **Equal.** Same score on every one of the 102 graded tasks, same wall time, decode within the noise. The `standard-v1` short-decode range on the package run is wide (49.9-65.2); the image run, minutes apart from the night package run, gave 69.1.
- `standard-v1` complete, sanity 12/12 on both tracks. Needles 7/7 (32K about 28 s, 128K 120-158 s, 250K 294 s; slower than on 5 Nov, but run at night with background jobs, so I read nothing into it). Fresh engines read their prompts at 592-756 tok/s.

## The tuned DFlash2 drafter on gfx1100

Variants, all on 0.2.12 with the production config otherwise unchanged: `mtp` (production, `--spec 4`); `df2t-05` / `df2t-07` tuned pack, `--draft dflash2 --draft-fallback none --spec 6 --draft-conf 0.5` / `0.7`; `df2s-05` the stock Q4_0-selector pack at 0.5; `w5` MTP with `--pool-workers 5` instead of 10. The drafter loads cleanly: 591 MiB of VRAM, MTP layer not loaded, expert cache 7,953 slots (7,956 with MTP). "Quiet" is my everyday card profile (core clock capped at 2,800 MHz, −100 mV); "max" is stock.

**Fixed test, 900 tokens per answer** (median decode tok/s; acceptance):

| variant | quiet | max | acceptance |
|---|---:|---:|---:|
| mtp | 83.0 | 79.0 | 68 % |
| df2t-05 | 87.7 | 88.8 | 67-69 % |
| df2t-07 | **92.6** | **90.5** | 79-80 % |
| df2s-05 | 86.5 | 88.8 | 69 % |
| w5 | 83.0 | 78.8 | 68-69 % |

Per prompt type it is not uniform: on the story (German prose) every DFlash2 variant is slower than MTP (53-55 against 60 tok/s), on code the tuned pack at 0.7 is 9-15 % faster (97-101 against 85-91 tok/s). The quiet/max difference for MTP is inside the noise.

**Real run, the 114-task set, natural answer length** (MTP = 100):

| | MTP | tuned DFlash2, conf 0.7 |
|---|---:|---:|
| decode median | 75.6 tok/s (100) | 76.1 tok/s (101) |
| output tokens | 72,321 (100) | 92,268 (128) |
| wall time | 1,430 s (100) | 1,660 s (116) |
| passed of 102 auto-graded | 98 | 96 |
| answers identical to MTP | | 51 of 114 |

- Per token the drafter is as fast as MTP, but **the answers change**: only 51 of 114 are identical to the MTP run at temperature 0, and the changed ones are often much longer (some code and fact tasks 6,000 instead of 1,500 tokens). That eats the gain and more: +16 % wall time.
- The two extra misses are multi-step price calculations that MTP got right.
- The notice next to the pack says greedy output can differ on HIP by window length. On this card it differs a lot, and the difference is not neutral.
- `--pool-workers 5` changes nothing: the CPU side is not the limit on this machine.

**Result for this NAS:** 0.2.12 in production since 8 Nov with MTP; DFlash2 stays off on this card.
