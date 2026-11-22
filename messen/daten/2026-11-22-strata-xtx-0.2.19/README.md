# Measurements of 22 Nov 2026 (evening): my own build strata-xtx `0.2.19-xtx3` on Strata 0.2.19

Strata 0.2.19 (engine and control 0.1.65) brings its own defaults for RDNA3 cards. One of them, a rule that allows prompt chunks of up to 32K tokens, also turns on a RAM guard (added as the fix for [#2090](https://github.com/Niko1221/Strata/issues/2090)): bigger chunks are taken only when the extra cache loan plus 6 GiB stays available. With the 125B model loaded, this NAS had 7.7 GiB available, 32K chunks need 9.2 GiB more, so 0.2.19 reads prompts from 16K on in 8K chunks (16K chunks with the steered variant). The unchanged release is still a little faster than 0.2.18, but my previous patch, applied unchanged to 0.2.19, read 58K at half its former speed. The new build `0.2.19-xtx3` adds Strata's own switch `STRATA_GFX11_CHUNK=1` to the table in the code and also turns off `STRATA_GFX11_DEFAULTS` when it restarts without the table after non-finite values; nothing else changed. It runs here since 22 Nov 2026, 20:04. Builds are named `<Strata release>-xtx<patch revision>` from this release on. Card in my quiet power setting unless a folder says `max`; NAS services running, only my agent paused.

"plain" is the original Flash-Next IQ3_XXS (`faber`), "steered" the variant with control vector and image input that my agent works with (`liber`).

| File | What |
|---|---|
| `../tiefe-20261122-0.2.19.jsonl` | `messen/tiefe.py`, 1K to 248K tokens, two to three runs each: plain, steered, and plain without the MTP head |
| `read-brake-0.2.19.json` | the values behind the chart of the read brake: the build that was in use (`0.2.18-xtx2`), the release as shipped, my previous patch on 0.2.19, the release with `STRATA_GFX11_CHUNK=1`, and `0.2.19-xtx3`, with the chunk sizes from the engine log and the RAM guard's arithmetic |
| `checks/brake-diagnosis.json` | single runs that found the cause: the previous patch on 0.2.19 with the chunk switch, with Strata's RDNA3 defaults off, with only the WMMA paths off, and the release with the chunk switch, both models; engine log lines about chunks and defaults |
| `checks/build-test-xtx2-on-0.2.19.json` | my previous patch (`xtx2`) unchanged on 0.2.19 against the build in use: the slowdown |
| `checks/build-test.json` | `0.2.19-xtx3` against the build in use (`0.2.18-xtx2`): both models, the table on and off, tool call, image input, control vector |
| `checks/gdn-pp-comparison.json` | `STRATA_GDN_PP` 1 (my table) against 2 (Strata's RDNA3 default), three alternating rounds, both models |
| `checks/task-set-and-250k.json`, `task-set-summary.json` | task set and 250K prompts on `0.2.19-xtx3` |
| `checks/rescue-steered.json` | restart without the table after injected non-finite values (`STRATA_NAN_INJECT=7,8`), steered variant |
| `strata-bench-alternating/` | `tools/strata_bench.py --long`, three rounds alternating between the unchanged release 0.2.19 and `0.2.19-xtx3`, fresh engine per run, order swapped each round |
| `strata-bench-alternating-max/` | one such round with the card at full power |
| `release-0.2.19/` | test of the unchanged release: three pairs against 0.2.18 (`version-pairs.jsonl`), fresh engines, needles, `standard-v1` with the packages and with the Docker image, `strata_bench.py` |
| `needles-*.json` | `tools/needle_bench.py` at 32K and 128K (10/50/90 % depth) and 250K (50 %), both models |
| `strom-*.json`, `kaltstart-*.json`, `wartezeit*.json`, `zwei.json`, `memory-*.json`, `bench/` | the operating measurements behind the charts (power at the UPS, cold start, waiting times, two people, memory) |

## The read brake and the fix

| Prompt reading, tokens/s | 16K, plain | 58K, plain | 58K, steered | 128K, steered |
|---|---:|---:|---:|---:|
| build in use until 22 Nov, 20:04 (`0.2.18-xtx2`) | 2,510 | 3,206 | 3,197 | 3,292 |
| release 0.2.19 as shipped | 1,511 | 1,430 | – | – |
| previous patch unchanged on 0.2.19 | 1,586 | 1,497 | 2,489 | 2,657 |
| release 0.2.19 with `STRATA_GFX11_CHUNK=1` (one run) | 1,851 | 2,550 | 2,638 | 2,718 |
| **`0.2.19-xtx3`** | **2,537** | **3,433** | **3,414** | **3,516** |

Median of two rounds of two runs each, except the single run marked. The lowest available RAM while reading was 3.5 GiB (plain) and 5.2 GiB (steered) with `0.2.19-xtx3`, 3.6 and 5.5 GiB on 0.2.18; swap stayed unchanged in every run. The release with the chunk switch still reads slower than my build because its reading ring has 96 instead of 384 slots.

## My own build against the unchanged release, both 0.2.19

| Median of three alternating runs | Release 0.2.19 | `0.2.19-xtx3` |
|---|---:|---:|
| 4K / 16K / 32K prompt, tokens/s | 847 / 1,510 / 1,472 | 1,615 / 2,528 / 3,054 |
| chat / agent decode, tokens/s (median over all requests) | 70.6 / 75.9 | 75.3 / 81.7 |
| one round at full power: 4K / 16K / 32K | 846 / 1,513 / 1,439 | 1,617 / 2,532 / 3,062 |
| one round at full power: chat / agent decode | 74.9 / 79.5 | 77.6 / 90.9 |
| needle at 128K / 250K (50 % depth), plain, seconds | 73 / 177 | 35 / 78 |

On the 250K prompt of the task set (247,954 tokens) the build reads 3,346 to 3,393 tokens/s and answers after 73.3 to 74.3 seconds, with both models; the hidden number was found every time.

## Over the context depth

| Prompt tokens | 995 | 4,077 | 16,254 | 65,025 | 130,026 | 248,054 |
|---|---:|---:|---:|---:|---:|---:|
| plain: prompt tokens/s | 766 | 1,555 | 2,538 | 3,439 | 3,379 | 3,324 |
| steered: prompt tokens/s | 724 | 1,460 | 2,400 | 3,469 | 3,480 | 3,381 |
| plain: decode tokens/s | 63.7 | 61.5 | 64.0 | 63.7 | 58.2 | 61.7 |
| steered: decode tokens/s | 60.2 | 64.8 | 65.1 | 60.5 | 62.0 | 62.2 |
| plain without MTP: decode tokens/s | 52.4 | 52.6 | 51.8 | 51.0 | 49.6 | 48.4 |

From 64K on the build reads 7 to 10 % faster than `0.2.18-xtx2` at midday of the same day (`../tiefe-20261122.jsonl`); decode stays within the scatter (16K 64.0 instead of 61.2, 128K 58.2 instead of 61.8). Long answers (`strom-*.json`): 64.6 tokens/s plain, 69.3 steered.

## Checks before it went into use (22 Nov)

| Check | Result |
|---|---|
| comparison with the build in use (`0.2.18-xtx2`) | plain 16K 2,537 against 2,510, 58K 3,433 against 3,206; steered 58K 3,414 against 3,197, 128K 3,516 against 3,292; decode 65.9 (plain) and 64.6 (steered) |
| table switched off (`STRATA_GFX1100_DEFAULTS=0`) | 16K 1,511, 58K 1,430 tokens/s, as slow as the release |
| task set, 102 graded tasks | plain 98, steered 97 (`task-set-summary.json`; on 0.2.18: 96 and 97) |
| self-rescue with injected non-finite values, steered | one restart without the table, the following requests answered, a 16K needle found afterwards |
| 90 minutes of continuous load, steered | 1,316 requests, 0 errors, 188 of 188 hidden numbers found, no non-finite values in the engine log |
| switch-over and acceptance (22 Nov, 20:04) | passed; steered 58K 3,485 and 3,427, 128K 3,544 tokens/s; plain 58K 3,529 and 3,281. The build in use differs from the tested one only in its name string (`0.2.19-xtx3` instead of `xtx-3`) |

## The unchanged release 0.2.19 against 0.2.18

Pairs in one session: decode 65.3 against 61.8 tokens/s. Prompt reading in `strata_bench.py` 8 to 9 % above 0.2.18 (847 / 1,510 / 1,472 against 786 / 1,385 / 1,358 at 4K / 16K / 32K), the 250K needle in 177 instead of 206 seconds. Needles found at 32K, 128K and 250K. New in 0.2.19 is a third model with an engine of its own, Inkling 2 Mini; my measurements of it follow in a separate folder.
