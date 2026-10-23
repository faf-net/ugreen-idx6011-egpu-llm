# Community benchmark on AMD Radeon

Measured on 2026-10-23 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon, 24 GiB VRAM
- CPU: Intel(R) Core(TM) Ultra 7 255H (16 cores, 16 threads); installed RAM: 62.3 GiB; storage: not measured
- OS: Linux 6.18.15; GPU driver: not read; CUDA: not read
- Strata: project 0.1.44.1, commit 296b59d2; engine 0.1.48
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: b023
- Context: 262144 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

## Method

Run by `python tools/strata_bench.py --long` against the HTTP API of a Strata server (already running); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 67.3 (56.0-89.7) | 0.35 (0.30-0.38) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 791.4 (781.0-796.5) | not measured | 5.12 (5.07-5.17) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 1218.1 (1160.5-1240.9) | not measured | 13.21 (12.98-13.87) |
| 32K prompt, fresh | 32049 (32049-32049) | 0 (0-0) | 24 cap | 3 | 1243.6 (1239.1-1245.0) | not measured | 25.81 (25.78-25.92) |
| agent session, follow-up turns | 14594 (14571-14605) at the last turn | see below | up to 64 | 3 | see below | 78.3 (41.4-99.4) | 5.01 (4.73-5.19) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 68.8 % (68.8-68.8); earlier-turn tokens read again per session: 3 (2-4) (earlier turns that the cache did not hold; the 13729 (13728-13729) new tokens of the files are read once); first turn (nothing cached) first token: 3.77 s (3.61-3.91).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 169.9 | 3.61 | 49.2 |
| 1 | 3744 | 624 | 3120 | 604.3 | 5.192 | 75.9 |
| 2 | 5277 | 3807 | 1470 | 312.7 | 4.728 | 67.3 |
| 3 | 8721 | 5341 | 3380 | 662.4 | 5.149 | 63.9 |
| 4 | 11647 | 8785 | 2862 | 581.4 | 4.966 | 86.0 |
| 5 | 14605 | 11706 | 2899 | 582.7 | 5.009 | 57.3 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 256 s.
