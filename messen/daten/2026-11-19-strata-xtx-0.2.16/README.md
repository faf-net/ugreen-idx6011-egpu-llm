# Measurements of 2026-11-19: my own build strata-xtx on Strata 0.2.16

Strata 0.2.16 (engine and control 0.1.62) brings its own engine code and a new folder layout. On this card the unchanged release is as fast as 0.2.15. My own build [strata-xtx](https://github.com/faf-net/strata-xtx) carries the prompt-path switches in the code; since 19 Nov it runs here on the base of 0.2.16, before that (18 to 19 Nov) on 0.2.15 (`../2026-11-18-strata-xtx/`). No switch is set in the run configuration. Card in my quiet power setting unless a folder says `max`; NAS services running, only my agent paused.

"plain" is the original Flash-Next IQ3_XXS (`faber`), "steered" the variant with control vector and image input that my agent works with (`liber`).

| File | What |
|---|---|
| `../tiefe-20261119.jsonl` | `messen/tiefe.py`, 1K to 248K tokens, two to three runs each: plain, steered, and plain without the MTP head |
| `strata-bench-alternating/` | `tools/strata_bench.py --long`, three rounds alternating between the unchanged release 0.2.16 and my own build, fresh engine per run, order swapped each round |
| `strata-bench-alternating-max/` | one such round with the card at full power |
| `release-0.2.16/` | test of the unchanged release: three pairs against 0.2.15 (`version-pairs.jsonl`), fresh engines, needles, `standard-v1` with the packages and with the Docker image, `strata_bench.py` |
| `checks/build-test.json` | the build before it went into use: both models, the table on and off, tool call, image input, control vector |
| `checks/task-set-and-250k.json`, `task-set-summary.json` | task set and 250K prompts on the build |
| `checks/rescue-plain.json`, `checks/rescue-steered.json` | restart without the table after injected non-finite values (`STRATA_NAN_INJECT=7,8`; 0.2.16 counts the six warm-up windows, so windows 1 and 2 no longer hit a request) |
| `needles-*.json` | `tools/needle_bench.py` at 32K and 128K (10/50/90 % depth) and 250K (50 %), both models |
| `strom-*.json`, `kaltstart-*.json`, `wartezeit*.json`, `zwei.json`, `memory-*.json`, `bench/` | the operating measurements behind the charts (power at the UPS, cold start, waiting times, two people, memory) |
| `strom-first-run/` | the first power run of that morning. For the steered variant it shows 74 W idle instead of 61 W and 57.7 instead of 67.4 tokens/s: something else was running on the NAS, I did not find out what. Discarded; the repeat a few hours later is the one above |
| `nebenlast.json` | file download and transcoding while the model writes, both models |

## My own build against the unchanged release, both 0.2.16

| Median of three alternating runs | Release 0.2.16 | strata-xtx |
|---|---:|---:|
| 4K / 16K / 32K prompt, tokens/s | 783 / 1,357 / 1,321 | 1,645 / 2,295 / 2,650 |
| chat / agent decode, tokens/s (median over all requests) | 69.6 / 72.3 | 72.5 / 81.7 |
| one round at full power: 4K / 16K / 32K | 783 / 1,392 / 1,382 | 1,639 / 2,352 / 2,639 |
| 250K prompt (247,954 tokens), steered | 1,220 tokens/s, 204 s | 2,838 to 2,883 tokens/s, 87 s |

## Over the context depth

| Prompt tokens | 995 | 4,077 | 16,254 | 65,025 | 130,026 | 248,054 |
|---|---:|---:|---:|---:|---:|---:|
| plain: prompt tokens/s | 742 | 1,470 | 2,404 | 3,021 | 2,968 | 2,907 |
| steered: prompt tokens/s | 658 | 1,438 | 2,290 | 2,925 | 2,933 | 2,890 |
| plain: decode tokens/s | 53.7 | 56.2 | 56.4 | 53.5 | 59.0 | 53.5 |
| steered: decode tokens/s | 56.9 | 50.9 | 56.2 | 52.6 | 55.4 | 55.6 |
| plain without MTP: decode tokens/s | 32.6 | 35.2 | 42.2 | 44.7 | 45.6 | 42.7 |

Prompt reading equals the values on the base of 0.2.15 (18 Nov). Decode in this series is mostly lower than on 18 Nov, by up to 8 tokens/s, while long answers (`strom-*.json`: 68.3 and 67.4 tokens/s) and the pairs are unchanged; I read that as scatter between days.

## The unchanged release 0.2.16 against 0.2.15

Pairs in one session: decode 61.4 (56.3 to 62.8) against 59.8 (58.2 to 61.5) tokens/s, equally fast. `standard-v1`: short decode 67.5, 4K 755, 16K 1,414 tokens/s. Needles found at 32K, 128K and 250K.
