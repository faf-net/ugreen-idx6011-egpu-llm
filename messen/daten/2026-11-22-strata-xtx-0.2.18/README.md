# Measurements of 2026-11-21/22: my own build strata-xtx on Strata 0.2.18

Strata 0.2.18 (engine and control 0.1.64) changes nothing about speed for Flash-Next on this card: the unchanged release writes and reads as fast as 0.2.17. What is new in 0.2.18 is a second model with an engine of its own, Hy4-Flash; my measurements of it are in [`../2026-11-22-hy4-flash/`](../2026-11-22-hy4-flash/). My own build [strata-xtx](https://github.com/faf-net/strata-xtx) runs here on the base of 0.2.18 since 22 Nov 2026, 10:34, as build `xtx-2`, with the patch applied unchanged. No switch is set in the run configuration. Card in my quiet power setting unless a folder says `max`; NAS services running, only my agent paused.

The checks before it went into use ran on 21 Nov, the operating measurements behind the charts on 22 Nov. "plain" is the original Flash-Next IQ3_XXS (`faber`), "steered" the variant with control vector and image input that my agent works with (`liber`).

| File | What |
|---|---|
| `../tiefe-20261122.jsonl` | `messen/tiefe.py`, 1K to 248K tokens, two to three runs each: plain, steered, and plain without the MTP head |
| `strata-bench-alternating/` | `tools/strata_bench.py --long`, three rounds alternating between the unchanged release 0.2.18 and my own build, fresh engine per run, order swapped each round |
| `strata-bench-alternating-max/` | one such round with the card at full power |
| `release-0.2.18/` | test of the unchanged release: three pairs against 0.2.17 (`version-pairs.jsonl`), fresh engines, needles, `standard-v1` with the packages and with the Docker image, `strata_bench.py` |
| `checks/build-test.json` | the build before it went into use, against the build in use (`xtx-2` on 0.2.17): both models, the table on and off, tool call, image input, control vector |
| `checks/task-set-and-250k.json`, `task-set-summary.json` | task set and 250K prompts on the build |
| `checks/rescue-steered.json` | restart without the table after injected non-finite values (`STRATA_NAN_INJECT=7,8`), steered variant |
| `needles-*.json` | `tools/needle_bench.py` at 32K and 128K (10/50/90 % depth) and 250K (50 %), both models |
| `strom-*.json`, `kaltstart-*.json`, `wartezeit*.json`, `zwei.json`, `memory-*.json`, `bench/` | the operating measurements behind the charts (power at the UPS, cold start, waiting times, two people, memory) |

The load test with file download and transcoding was not repeated; the latest one is in `../2026-11-19-strata-xtx-0.2.16/nebenlast.json`.

## My own build against the unchanged release, both 0.2.18

| Median of three alternating runs | Release 0.2.18 | strata-xtx |
|---|---:|---:|
| 4K / 16K / 32K prompt, tokens/s | 786 / 1,385 / 1,358 | 1,641 / 2,479 / 2,851 |
| chat / agent decode, tokens/s (median over all requests) | 69.5 / 73.5 | 76.3 / 78.7 |
| one round at full power: 4K / 16K / 32K | 787 / 1,396 / 1,382 | 1,571 / 2,478 / 2,850 |
| needle at 128K / 250K (50 % depth), plain, seconds | 82 / 206 | 37 / 83 |

On the 250K prompt of the task set (247,954 tokens) the build reads 3,066 to 3,169 tokens/s and answers after 78.5 to 81.1 seconds, with both models; the hidden number was found every time.

## Over the context depth

| Prompt tokens | 995 | 4,077 | 16,254 | 65,025 | 130,026 | 248,054 |
|---|---:|---:|---:|---:|---:|---:|
| plain: prompt tokens/s | 746 | 1,485 | 2,486 | 3,113 | 3,151 | 3,075 |
| steered: prompt tokens/s | 734 | 1,482 | 2,366 | 3,238 | 3,263 | 3,172 |
| plain: decode tokens/s | 62.2 | 62.5 | 61.2 | 61.3 | 61.8 | 56.9 |
| steered: decode tokens/s | 57.4 | 61.0 | 61.4 | 57.7 | 58.3 | 60.5 |
| plain without MTP: decode tokens/s | 49.5 | 48.3 | 47.3 | 47.4 | 47.0 | 46.3 |

Prompt reading stays within 3 % of 0.2.17 (21 Nov) at every depth, decode within the usual scatter between days. Long answers (`strom-*.json`): 67.8 tokens/s plain, 68.5 steered.

## Checks before it went into use (21 Nov)

| Check | Result |
|---|---|
| comparison with the build in use (`xtx-2` on 0.2.17) | equally fast: steered 58K 3,208 against 3,203 tokens/s, 128K 3,294 and 3,297 against 3,292 and 3,236, decode 62.6 against 61.2; plain decode 61.8 against 64.5, one plain run read 58K at only 2,293 (the others 3,027 to 3,277) |
| table switched off (`STRATA_GFX1100_DEFAULTS=0`) | 58K at 1,050 to 1,338 tokens/s, as slow as the release: the table in the code is what makes the difference |
| task set, 102 graded tasks | plain 96, steered 97 (`task-set-summary.json`; on 0.2.17: 95 and 97) |
| self-rescue with injected non-finite values, steered | one restart without the table, the following requests answered, a 16K needle found afterwards |
| 90 minutes of continuous load, steered | 1,260 requests, 0 errors, 180 of 180 hidden numbers found, no non-finite values in the engine log |
| switch-over and acceptance (22 Nov) | passed; steered decode 60.1 and 60.4, 128K read at 3,271 tokens/s; plain decode 60.2 and 61.9 |

## The unchanged release 0.2.18 against 0.2.17

Pairs in one session: decode 61.1 (58.1 to 62.7) against 61.6 (56.3 to 64.5) tokens/s, equally fast. Prompt reading in `strata_bench.py` 1 to 3 % above 0.2.17 (792 / 1,419 / 1,371 against 784 / 1,398 / 1,336 at 4K / 16K / 32K). Needles found at 32K, 128K and 250K. Image input, tool call and control vector work with the steered variant.
