# Measurements of 24 Nov 2026: my own build strata-xtx `0.2.21-xtx3` on Strata 0.2.21

Strata 0.2.21 (engine and control 0.1.67) carries the fix for [#6687](https://github.com/Niko1221/Strata/issues/6687): without pinned experts the RAM guard of [#2090](https://github.com/Niko1221/Strata/issues/2090) now counts half of the cache loan and keeps a 3 GiB instead of a 6 GiB reserve. On this 64 GB NAS that lifts the unchanged release from 8K to 16K prompt chunks; 32K chunks are missed by a hair (see below). My patch applied unchanged, so the build is `0.2.21-xtx3`. It runs here since 24 Nov 2026, 20:38. On top I measured follow-up requests of an agent against the stream floor. Card in my quiet power setting unless a folder or a run says `max`; NAS services running, only my agent paused.

"plain" is the original Flash-Next IQ3_XXS (`faber`), "steered" the variant with control vector and image input that my agent works with (`liber`).

| File | What |
|---|---|
| `../tiefe-20261124-0.2.21.jsonl` | `messen/tiefe.py`, 1K to 248K tokens, two to three runs each: plain, steered, and plain without the MTP head |
| `checks/build-test.json` | `0.2.21-xtx3` against the build in use (`0.2.20-xtx3`), two alternating rounds: both models, the table on and off, tool call, image input, control vector, chunk size and guard lines from the engine log |
| `checks/task-set-and-250k.json`, `task-set-summary.json` | task set and 250K prompts on `0.2.21-xtx3` |
| `checks/rescue-steered.json` | restart without the table after injected non-finite values (`STRATA_NAN_INJECT=7,8`), steered variant |
| `checks/stream-floor-follow-ups.json` | follow-up requests as an agent sends them: a 4K or 32K prefix from the conversation cache, then about 500, 1,600 or 3,000 new tokens with a hidden number; stream floor 4,096 (my table), 2,048 and 1,024 via `STRATA_PREFILL_CPU_SHARE_MAX`; both models, two alternating rounds quiet and one at full power |
| `strata-bench-alternating/` | `tools/strata_bench.py --long`, three rounds alternating between the unchanged release 0.2.21 and `0.2.21-xtx3`, fresh engine per run, order swapped each round |
| `strata-bench-alternating-max/` | one such round with the card at full power |
| `release-0.2.21/` | test of the unchanged release: three pairs against 0.2.20 (`version-pairs.jsonl`), fresh engines, needles, `standard-v1` with the packages and with the Docker image, `strata_bench.py` |
| `needles-*.json` | `tools/needle_bench.py` at 32K and 128K (10/50/90 % depth) and 250K (50 %), both models |
| `strom-*.json`, `kaltstart-*.json`, `wartezeit*.json`, `zwei.json`, `memory-*.json`, `bench/` | the operating measurements behind the charts (power at the UPS, cold start, waiting times, two people, memory) |

## My own build against the unchanged release, both 0.2.21

| Median of three alternating runs | Release 0.2.21 | `0.2.21-xtx3` |
|---|---:|---:|
| 4K / 16K / 32K prompt, tokens/s | 843 / 1,980 / 2,217 | 1,625 / 2,511 / 3,049 |
| chat / agent decode, tokens/s (median over all requests) | 72.9 / 76.8 | 74.9 / 85.4 |
| one round at full power: 4K / 16K / 32K | 784 / 1,996 / 2,326 | 1,604 / 2,482 / 3,056 |
| one round at full power: chat / agent decode | 74.5 / 81.4 | 80.3 / 80.2 |
| needle at 128K / 250K (50 % depth), plain, seconds | 47 / 103 | 36 / 77 |

**The release caught up a good part of the way.** Against 0.2.20 it reads 16K 32 % and 32K 50 % faster (1,503 → 1,980, 1,475 → 2,217 tokens/s) and the 250K needle in 103 instead of 175 seconds. That is the #6687 fix: 16K instead of 8K chunks. My build is still 1.4 times as fast at 32K and 1.9 times at 4K, because the other 26 switches of the table do most of the work.

On the 250K prompt of the task set (247,954 tokens) the build reads 3,312 to 3,385 tokens/s and answers after 73.5 to 75.1 seconds, with both models; the hidden number was found every time.

## Why the release stays at 16K chunks here

The build without its table reads like the release and logs:

```
strata generate: gfx11: prompt chunks stay at 16384: 32768 would lend 4209 more cache slots (4675 MiB more held in RAM during a prompt), and 7688 MiB of RAM is available for 0 MiB of resident experts plus that and 3072 MiB reserve
```

The 4,675 MiB are already the halved loan. 4,675 + 3,072 = 7,747 MiB are needed, 7,688 (in the second round 7,736) are available: 32K chunks are missed by 59 (11) MiB. The fix is right; this machine sits on the edge.

## Over the context depth

| Prompt tokens | 995 | 4,077 | 16,254 | 65,025 | 130,027 | 248,054 |
|---|---:|---:|---:|---:|---:|---:|
| plain: prompt tokens/s | 756 | 1,531 | 2,538 | 3,451 | 3,411 | 3,312 |
| steered: prompt tokens/s | 740 | 1,501 | 2,388 | 3,474 | 3,463 | 3,356 |
| plain: decode tokens/s | 62.6 | 65.8 | 65.0 | 62.3 | 61.5 | 58.1 |
| steered: decode tokens/s | 61.9 | 63.7 | 63.3 | 59.9 | 60.8 | 61.7 |
| plain without MTP: decode tokens/s | 50.1 | 52.1 | 51.4 | 51.2 | 51.0 | 49.1 |

Within 1.5 % of `0.2.20-xtx3` on 23 Nov (`../tiefe-20261123-0.2.20.jsonl`) in reading; decode within the scatter. Long answers (`strom-*.json`): 72.6 tokens/s plain, 68.1 steered (on 0.2.20: 74.5 and 67.2).

## Follow-up requests and the stream floor

Raised in #6687 by another user: on an RX 7800 XT, lowering the stream floor from 3,072 to 1,024 halved the wait for an agent's follow-up of about 1,600 new tokens. My build streams from 4,095 tokens (the ceiling of the CPU share in my table, which takes precedence over `STRATA_PREFILL_STREAM_MIN`). Median of two quiet rounds, seconds until the short answer, steered:

| Prefix + new tokens | floor 4,096 (my table) | 2,048 | 1,024 |
|---|---:|---:|---:|
| 4K + 500 | 1.60 | 1.62 | 1.58 |
| 4K + 1,600 | 2.66 | 2.62 | 5.16 |
| 4K + 3,000 | 3.41 | 5.29 | 5.29 |
| 32K + 500 | 1.50 | 1.53 | 1.52 |
| 32K + 1,600 | 2.52 | 2.54 | 5.12 |
| 32K + 3,000 | 3.40 | 5.26 | 5.26 |

The plain model shows the same (32K + 3,000: 3.33 against 4.92 s). The engine log confirms the moved floor (1023); the prefix came from the cache (e.g. 32,103 of 35,127 tokens); 108 of 108 hidden numbers were found. **On this card and model a lower floor makes follow-ups up to twice as slow**: the streamed walk sends every expert of every layer through the ring, with a 125B model whose experts sit in RAM that is about 5 seconds whatever the piece. **The table stays at 4,096.**

## Checks before it went into use (24 Nov)

| Check | Result |
|---|---|
| comparison with the build in use (`0.2.20-xtx3`), two rounds | prompt reading 99 to 101 % (steered 4K 720 against 725, 16K 2,379 against 2,393, 58K 3,409 against 3,400, 128K 3,522 against 3,485; plain 58K 3,425 against 3,439); decode equal (steered 66.1 against 65.9, plain 66.6 against 66.3); chunk size 32,768 in the engine log |
| table switched off (`STRATA_GFX1100_DEFAULTS=0`) | plain 16K 2,001, 58K 2,054 tokens/s, 16K chunks (on 0.2.20: 1,454 and 1,427 with 8K chunks) |
| task set, 102 graded tasks | plain 96, steered 97 (`task-set-summary.json`; on 0.2.20: 98 and 97; the two tasks the plain model lost flip between runs) |
| self-rescue with injected non-finite values, steered | one restart without the table, the following requests answered, a 16K needle found afterwards |
| 90 minutes of continuous load, steered | 1,316 requests, 0 errors, 188 of 188 hidden numbers found, no non-finite values in the engine log, available RAM never below 5.5 GiB |
| switch-over and acceptance (24 Nov, 20:38) | passed; steered 58K 3,402 and 3,362, 128K 3,524 tokens/s; plain 58K 3,486 and 3,049 |

## The unchanged release 0.2.21 against 0.2.20

Pairs in one session: decode 65.5 against 66.0 tokens/s, within the noise; a short prompt 133 against 145 tokens/s. Prompt reading in `strata_bench.py` as above. Needles found at 32K, 128K and 250K; the short quality probe 28 of 29, which scatters by one task between runs.
