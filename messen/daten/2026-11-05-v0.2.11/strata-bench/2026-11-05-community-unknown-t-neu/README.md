# Community benchmark on AMD Radeon

Measured on 2026-11-05 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon, 24 GiB VRAM
- CPU: Intel(R) Core(TM) Ultra 7 255H (16 cores, 16 threads); installed RAM: 62.3 GiB; storage: not measured
- OS: Linux 6.18.15; GPU driver: not read; CUDA: not read
- Strata: project 0.1.44.1, commit 296b59d2; engine 0.1.57
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: t-neu
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
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 64.3 (54.5-88.1) | 0.39 (0.31-0.41) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 781.0 (776.1-784.4) | not measured | 5.17 (5.17-5.22) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 1211.9 (1195.8-1217.9) | not measured | 13.28 (13.22-13.46) |
| 32K prompt, fresh | 32049 (32049-32049) | 0 (0-0) | 24 cap | 3 | 1225.8 (1224.9-1234.0) | not measured | 26.18 (26.01-26.20) |
| agent session, follow-up turns | 14592 (14589-14593) at the last turn | see below | up to 64 | 3 | see below | 80.9 (45.2-99.7) | 5.07 (4.77-5.75) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 68.8 % (68.8-68.8); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 13731 (13730-13731) new tokens of the files are read once); first turn (nothing cached) first token: 3.87 s (3.60-3.88).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 170.2 | 3.603 | 49.9 |
| 1 | 3744 | 621 | 3123 | 606.2 | 5.183 | 67.5 |
| 2 | 5277 | 3807 | 1470 | 308.7 | 4.789 | 70.3 |
| 3 | 8721 | 5340 | 3381 | 647.8 | 5.248 | 68.0 |
| 4 | 11647 | 8784 | 2863 | 556.9 | 5.181 | 73.1 |
| 5 | 14593 | 11694 | 2899 | 580.4 | 5.029 | 52.5 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 260 s.
