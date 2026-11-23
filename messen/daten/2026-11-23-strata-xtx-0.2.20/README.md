# Measurements of 23 Nov 2026: my own build strata-xtx `0.2.20-xtx3` on Strata 0.2.20

Strata 0.2.20 (engine and control 0.1.66) changes nothing for Flash-Next on this card. The RAM guard that came with 0.2.19 (the fix for [#2090](https://github.com/Niko1221/Strata/issues/2090)) is still there and keeps the unchanged release at 8K prompt chunks on this 64 GB NAS; the engine log lines of 0.2.18, 0.2.19 and 0.2.20 are in [#6687](https://github.com/Niko1221/Strata/issues/6687). My patch applied unchanged, so the build is `0.2.20-xtx3`. It runs here since 23 Nov 2026, 12:10. On top I re-tested the CPU share for short prompts. Card in my quiet power setting unless a folder or a run says `max`; NAS services running, only my agent paused.

"plain" is the original Flash-Next IQ3_XXS (`faber`), "steered" the variant with control vector and image input that my agent works with (`liber`).

| File | What |
|---|---|
| `../tiefe-20261123-0.2.20.jsonl` | `messen/tiefe.py`, 1K to 248K tokens, two to three runs each: plain, steered, and plain without the MTP head |
| `checks/build-test.json` | `0.2.20-xtx3` against the build in use (`0.2.19-xtx3`), two alternating rounds: both models, the table on and off, tool call, image input, control vector, chunk size from the engine log |
| `checks/task-set-and-250k.json`, `task-set-summary.json` | task set and 250K prompts on `0.2.20-xtx3` |
| `checks/rescue-steered.json` | restart without the table after injected non-finite values (`STRATA_NAN_INJECT=7,8`), steered variant |
| `checks/cpu-share-ceiling.json` | `STRATA_PREFILL_CPU_SHARE_MAX` at 3,072, 3,584, 4,096 (my table), 4,608 and 6,144, prompts of 2K to 16K with a hidden number, both models, three alternating rounds quiet and one at full power |
| `checks/cpu-share-and-hipblaslt-0.2.19.json` | night of 22/23 Nov on `0.2.19-xtx3`: CPU share 0.6 / 4,096 (my table) against Strata's ceiling 3,072, share 0.4, 0.8 and off, and the hipBLASLt tuning table off; both models, three alternating rounds |
| `strata-bench-alternating/` | `tools/strata_bench.py --long`, three rounds alternating between the unchanged release 0.2.20 and `0.2.20-xtx3`, fresh engine per run, order swapped each round |
| `strata-bench-alternating-max/` | one such round with the card at full power |
| `release-0.2.20/` | test of the unchanged release: three pairs against 0.2.19 (`version-pairs.jsonl`), fresh engines, needles, `standard-v1` with the packages and with the Docker image, `strata_bench.py` |
| `needles-*.json` | `tools/needle_bench.py` at 32K and 128K (10/50/90 % depth) and 250K (50 %), both models |
| `strom-*.json`, `kaltstart-*.json`, `wartezeit*.json`, `zwei.json`, `memory-*.json`, `bench/` | the operating measurements behind the charts (power at the UPS, cold start, waiting times, two people, memory) |

## My own build against the unchanged release, both 0.2.20

| Median of three alternating runs | Release 0.2.20 | `0.2.20-xtx3` |
|---|---:|---:|
| 4K / 16K / 32K prompt, tokens/s | 818 / 1,503 / 1,475 | 1,694 / 2,524 / 3,053 |
| chat / agent decode, tokens/s (median over all requests) | 65.1 / 79.7 | 72.2 / 83.6 |
| one round at full power: 4K / 16K / 32K | 788 / 1,502 / 1,506 | 1,600 / 2,519 / 3,061 |
| one round at full power: chat / agent decode | 64.8 / 75.6 | 73.4 / 83.2 |
| needle at 128K / 250K (50 % depth), plain, seconds | 73 / 175 | 35 / 77 |

On the 250K prompt of the task set (247,954 tokens) the build reads 3,296 to 3,357 tokens/s and answers after 74 to 76 seconds, with both models; the hidden number was found every time.

## Over the context depth

| Prompt tokens | 1,000 | 4,076 | 16,192 | 64,967 | 130,144 | 247,791 |
|---|---:|---:|---:|---:|---:|---:|
| plain: prompt tokens/s | 757 | 1,548 | 2,502 | 3,449 | 3,406 | 3,322 |
| steered: prompt tokens/s | 735 | 1,506 | 2,397 | 3,461 | 3,498 | 3,346 |
| plain: decode tokens/s | 59.1 | 65.9 | 65.2 | 62.6 | 62.1 | 59.5 |
| steered: decode tokens/s | 68.0 | 63.3 | 61.5 | 61.4 | 63.3 | 58.0 |
| plain without MTP: decode tokens/s | 48.8 | 53.0 | 52.6 | 51.6 | 48.3 | 49.7 |

Within 1 % of `0.2.19-xtx3` on the evening of 22 Nov (`../tiefe-20261122-0.2.19.jsonl`) in reading; decode within the scatter. Long answers (`strom-*.json`): 74.5 tokens/s plain, 67.2 steered (on 0.2.19: 64.6 and 69.3).

## The CPU share for short prompts

My table lets the idle CPU take part of the experts for prompt chunks of up to 4,096 tokens (share 0.6). Median of three quiet rounds, plain, prompt tokens/s:

| Ceiling | 2K | 4K | 6K | 8K | 12K | 16K | decode |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3,072 (Strata's own) | 850 | 714 | 1,171 | 1,496 | 2,093 | 2,545 | 62.4 |
| 3,584 | 814 | 745 | 1,167 | 1,485 | 2,078 | 2,532 | 61.0 |
| **4,096 (my table)** | **851** | **1,131** | **1,038** | **1,482** | **2,071** | **2,530** | **62.0** |
| 4,608 | 859 | 1,158 | 983 | 1,480 | 2,063 | 2,531 | 61.2 |
| 6,144 | 830 | 1,149 | 1,354 | 1,309 | 2,066 | 2,517 | 62.8 |

The steered variant shows the same pattern (4K: 1,086 with 4,096, 660 with 3,072; 16K: 2,363 to 2,407 with every ceiling); the round at full power as well. In the night test on `0.2.19-xtx3` the share was worth 2.7 times at 1K and 26 % at 4K; 0.4 and 0.8 read like 0.6; switching the hipBLASLt tuning table off changed nothing beyond the spread. That night 16K looked 4 to 10 % faster without the share; on 0.2.20 every ceiling reads 16K equally fast, so that did not hold. 6,144 would read 6K 30 % faster but 8K 12 % slower. **The table stays at 4,096.** Every hidden number was found.

## Checks before it went into use (23 Nov)

| Check | Result |
|---|---|
| comparison with the build in use (`0.2.19-xtx3`), two rounds | prompt reading 96 to 105 % (plain 16K 2,533 against 2,534, 58K 3,346 against 3,402; steered 58K 3,413 against 3,402, 128K 3,529 against 3,485); decode 3 to 4 % lower in this comparison (plain 65.1 against 68.1, steered 62.8 against 65.1), faster than the release in the alternating runs above; chunk size 32,768 in the engine log |
| table switched off (`STRATA_GFX1100_DEFAULTS=0`) | 16K 1,454, 58K 1,427 tokens/s, as slow as the release |
| task set, 102 graded tasks | plain 98, steered 97 (`task-set-summary.json`; on 0.2.19 the same) |
| self-rescue with injected non-finite values, steered | one restart without the table, the following requests answered, a 16K needle found afterwards |
| 90 minutes of continuous load, steered | 1,309 requests, 0 errors, 187 of 187 hidden numbers found, no non-finite values in the engine log, available RAM never below 5.5 GiB |
| switch-over and acceptance (23 Nov, 12:10) | passed; steered 58K 3,422 and 3,391, 128K 3,501 tokens/s; plain 58K 3,489 and 3,283 |

## The unchanged release 0.2.20 against 0.2.19

Pairs in one session: decode 64.8 against 65.8 tokens/s, within the noise. Prompt reading in `strata_bench.py` 818 / 1,503 / 1,475 against 847 / 1,510 / 1,472 tokens/s at 4K / 16K / 32K on 22 Nov, the 250K needle in 175 instead of 177 seconds. Needles found at 32K, 128K and 250K; the short quality probe 28 of 29, which scatters by one task between runs.
