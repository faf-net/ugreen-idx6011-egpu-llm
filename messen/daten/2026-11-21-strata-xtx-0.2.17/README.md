# Measurements of 2026-11-20/21: my own build strata-xtx on Strata 0.2.17

Strata 0.2.17 (engine and control 0.1.63) changes nothing about speed on this card: the unchanged release writes and reads as fast as 0.2.16. My own build [strata-xtx](https://github.com/faf-net/strata-xtx) carries the prompt-path switches in the code; since 20 Nov 2026, 22:16, it runs here on the base of 0.2.17, as build `xtx-2`. The only change against `xtx-1` (0.2.15 and 0.2.16) is the prompt reading buffer `STRATA_PREFILL_RING`, now 384 instead of 192. No switch is set in the run configuration. Card in my quiet power setting unless a folder says `max`; NAS services running, only my agent paused.

The checks before it went into use ran on 20 Nov, the operating measurements behind the charts on 21 Nov. "plain" is the original Flash-Next IQ3_XXS (`faber`), "steered" the variant with control vector and image input that my agent works with (`liber`).

| File | What |
|---|---|
| `../tiefe-20261121.jsonl` | `messen/tiefe.py`, 1K to 248K tokens, two to three runs each: plain, steered, and plain without the MTP head |
| `strata-bench-alternating/` | `tools/strata_bench.py --long`, three rounds alternating between the unchanged release 0.2.17 and my own build, fresh engine per run, order swapped each round |
| `strata-bench-alternating-max/` | one such round with the card at full power |
| `release-0.2.17/` | test of the unchanged release: three pairs against 0.2.16 (`version-pairs.jsonl`), fresh engines, needles, `standard-v1` with the packages and with the Docker image, `strata_bench.py` |
| `checks/build-test.json` | the build before it went into use: both models, the table on and off, tool call, image input, control vector |
| `checks/task-set-and-250k.json`, `task-set-summary.json` | task set and 250K prompts on the build |
| `checks/rescue-plain.json`, `checks/rescue-steered.json` | restart without the table after injected non-finite values (`STRATA_NAN_INJECT=7,8`) |
| `needles-*.json` | `tools/needle_bench.py` at 32K and 128K (10/50/90 % depth) and 250K (50 %), both models |
| `strom-*.json`, `kaltstart-*.json`, `wartezeit*.json`, `zwei.json`, `memory-*.json`, `bench/` | the operating measurements behind the charts (power at the UPS, cold start, waiting times, two people, memory) |

The load test with file download and transcoding was not repeated; the latest one is in `../2026-11-19-strata-xtx-0.2.16/nebenlast.json`.

## My own build against the unchanged release, both 0.2.17

| Median of three alternating runs | Release 0.2.17 | strata-xtx |
|---|---:|---:|
| 4K / 16K / 32K prompt, tokens/s | 785 / 1,390 / 1,352 | 1,576 / 2,481 / 2,848 |
| chat / agent decode, tokens/s (median over all requests) | 67.9 / 72.1 | 77.7 / 80.9 |
| one round at full power: 4K / 16K / 32K | 785 / 1,396 / 1,362 | 1,643 / 2,476 / 2,854 |
| needle at 128K / 250K (50 % depth), plain, seconds | 82 / 207 | 37 / 82 |

On the 250K prompt of the task set (247,954 tokens) the build reads 3,099 to 3,179 tokens/s and answers after 78 to 80 seconds, with both models; the hidden number was found every time.

## Over the context depth

| Prompt tokens | 995 | 4,077 | 16,254 | 65,025 | 130,026 | 248,054 |
|---|---:|---:|---:|---:|---:|---:|
| plain: prompt tokens/s | 759 | 1,511 | 2,478 | 3,193 | 3,103 | 3,093 |
| steered: prompt tokens/s | 734 | 1,505 | 2,366 | 3,214 | 3,252 | 3,128 |
| plain: decode tokens/s | 60.2 | 62.7 | 61.2 | 58.2 | 60.1 | 57.0 |
| steered: decode tokens/s | 62.6 | 63.5 | 62.9 | 60.7 | 58.7 | 60.2 |
| plain without MTP: decode tokens/s | 50.0 | 50.8 | 48.1 | 48.6 | 47.6 | 46.2 |

Prompt reading from 65K up is 5 to 11 % higher than on 0.2.16 (19 Nov). I attribute that to the larger reading buffer, but it is one series per build, not an alternating comparison. Decode is higher too, by up to 7 tokens/s plain and up to 13 steered; the pairs below show no difference between the releases, so I read most of that as scatter between days. Long answers (`strom-*.json`): 70.2 tokens/s plain, 64.3 steered.

## Checks before it went into use (20 Nov)

| Check | Result |
|---|---|
| comparison with the build in use (`xtx-1` on 0.2.16) | equally fast, both models: 58K 3,200 against 3,201 tokens/s steered, decode 60.6 against 61.5 |
| task set, 102 graded tasks | plain 95, steered 97 (`task-set-summary.json`; on 0.2.16: 97 and 96) |
| self-rescue with injected non-finite values | one restart without the table, the following requests answered, both models |
| 90 minutes of continuous load, steered | 1,267 requests, 0 errors, 181 of 181 hidden numbers found, no non-finite values in the engine log |
| switch-over and acceptance | passed; one decode run of the steered variant at 50.5 tokens/s, the second at 58.3 |

## The unchanged release 0.2.17 against 0.2.16

Pairs in one session: decode 61.6 (59.6 to 64.7) against 62.3 (59.0 to 64.5) tokens/s, equally fast. Prompt reading in `strata_bench.py` within 3 % of 0.2.16. Needles found at 32K, 128K and 250K.
