# Measurements of 2026-11-17/18: the switches of the rdna3 fork on the unchanged Strata 0.2.14 engine

The fork [`nicejunjie/Strata-rdna3`](https://github.com/nicejunjie/Strata-rdna3) tunes Strata for RDNA3 cards and ships a run config for one RX 7900 XTX (`rdna3/configs/iq3-1gpu.json`). Most of what that config does is set environment variables. I wanted to know how much of it works **without the fork**, on the prebuilt engine I already run: Strata 0.2.14 (engine and control 0.1.60, `hip-rx7900`).

Of the 46 variables in the fork's config, the names of 30 are present in the stock 0.1.60 engine binary; 28 of them are switches I could set as they stand (`run-config.json`). The other 16 exist only in the fork and are left out. So this is a test of 28 undocumented environment variables on a stock engine, not a test of the fork.

Same model and run config as in production otherwise: Flash-Next IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832 --pcie-frac 0`, conversation cache 4 slots / 9,216 MiB. "Quiet" is my everyday card profile (core clock capped at 2,800 MHz, −100 mV), "max" is stock. The NAS services were running throughout; only my agent was paused where noted.

| File | What |
|---|---|
| `run-config.json` | engine arguments, the 28 switches with their values, and the four extra arguments of the third speed variant |
| `speed-runs.jsonl`, `speed-summary.json` | `tools/strata_bench.py`: 3 variants × 2 card profiles × 3 rounds = 18 runs, fresh engine per run, interleaved |
| `task-set-summary.json` | my own task set (114 German-language tasks, 102 auto-graded, temperature 0, thinking on, up to 8,000 tokens), two runs per variant in the order switches, baseline, baseline, switches |
| `idle.json` | card power and load with the model loaded and no request |
| `endurance-requests.jsonl`, `endurance-summary.json` | 90 minutes of continuous load with the switches: 176 rounds of one long prompt (8K to 64K target, with a hidden note to find) followed by an agent session of six turns; one line per request with the server's own timings, no answer texts |
| `control-requests.jsonl` | the same 58K prompt twice and one agent session **without** the switches, right after the endurance run |
| `memory-per-second.csv` | `MemAvailable` and `SwapFree` of the NAS once per second during the endurance run and the control |
| `memory-summary.json`, `long-prompt-summary.json` | long prompts of 70K, 100K, 128K and 250K tokens, with and without the switches, on the plain model and on the variant with control vector: prompt tokens, reading speed, seconds and lowest available memory, two runs each |
| `long-prompt-requests.jsonl`, `long-prompt-memory-per-second.csv` | the 32 long requests with the server's timings, and memory once per second for that measurement |
| `long-prompt-smoke-test.json` | the variant with control vector with and without the switches: loads, vector on 41 layers per the log, image request, tool call, reading speed at 4K and 16K |
| `acceptance-after-adoption.json` | 18 Nov, after the switches went into the production run configs: both models in both card profiles, loading, reading at 4K/16K/58K (127K once), hidden number, tool call, image, control vector line, memory, error lines; counts only |

## Speed

Median of three runs each, quiet profile (max in brackets):

| | baseline | 28 switches | switches + 4 arguments |
|---|---:|---:|---:|
| 16K prompt, tok/s | 1,405.6 (1,396.1) | 2,365.0 (2,372.5) | 2,378.9 (2,382.4) |
| 4K prompt, tok/s | 789.1 (797.1) | 1,632.4 (1,650.9) | 1,642.7 (1,658.8) |
| chat decode, tok/s | 65.6 (66.7) | 72.5 (74.4) | 72.2 (74.6) |
| agent decode, tok/s | 75.8 (79.8) | 82.4 (86.0) | 85.1 (88.8) |
| card power, mean W | 207 (225) | 201 (235) | 209 (233) |

- **Prompt reading is 68 % faster at 16K and twice as fast at 4K**, decode about 10 % faster, at the same card power.
- The four extra arguments from the fork's config (`--adapt-every 1 --adapt-swaps 32 --mtp-q4 all --mtp-window 4096`) add nothing I can separate from noise, so I dropped them.
- The quiet profile loses nothing against max on prompt reading.

## Task set

| | baseline, run 1 / 2 | switches, run 1 / 2 |
|---|---:|---:|
| passed of 102 auto-graded | 98 / 97 | 98 / 97 |
| wall time, 114 tasks | 1,422 s / 1,562 s | 1,302 s / 1,316 s |
| output tokens | 77,696 / 83,200 | 90,889 / 91,717 |
| decode median, tok/s | 75.7 / 75.6 | 83.2 / 83.1 |
| long context, 30K prompt | 25-26 s | 13-14 s |
| long context, 93K prompt | 72-115 s | 32-34 s |

- **Same score.** The same four tasks fail in all four runs; a fifth miss appears in the second run of each variant (a facts task on the baseline, a logic task with the switches).
- The fork says two of the switches (`STRATA_HIP_WMMA`, `STRATA_SELECT_WMMA`) are not bit-identical. That is true, but the stock engine is not repeatable here either: of 114 answers at temperature 0, 47 are identical between the two baseline runs, 51 between the two runs with switches, and 47 to 52 across the variants. The switches add no difference I can see on top of that.
- All 16 hidden notes in the long-context tasks were found.
- The 12 German-writing tasks are not auto-graded and I have not read them side by side yet.

## Idle

Model loaded, no request, quiet profile: 16.0 W and at most 2 % load on the baseline, 16.2 W and at most 1 % with the switches (17.4 W with no model loaded). `GPU_MAX_HW_QUEUES=6` does not keep the card busy when idle.

## Endurance

A user of the fork reported non-finite logits after 1 h 45 min, followed by HTTP 503 on every request, and suspected `STRATA_GDN_CHUNKED` and `STRATA_PF_F16`. Both are in my set, so I ran it under load.

| | with the switches, 90 min |
|---|---:|
| requests | 1,232 |
| HTTP 200 | 1,232 |
| hidden notes found | 176 of 176 |
| non-finite or NaN lines in the engine log | 0 |
| prompt reading at 7.8K / 15.5K / 31K / 58K tokens, last half hour | 1,516 / 2,411 / 2,854 / 3,048 tok/s |
| agent turns, decode | 66.1 tok/s (first half hour 70.7, last 63.6) |
| available memory, minimum | 2.17 GiB |

Before that I ran the same switches for 38 minutes with `STRATA_DBG_NAN=1`, which makes the engine check its intermediate values at every prompt end: 70 requests, 70 check lines, **no non-finite value** in the last residual row, the PLE history or the GDN state; the largest magnitudes were 6.1, 15.2 and 3.8. Numbers of that part are in `endurance-summary.json` under `debug_run_with_switches`.

The same 58,199-token prompt with and without the switches:

| | with switches (44 requests) | without (request 2 of 2) |
|---|---:|---:|
| prompt reading | 3,048 tok/s | 1,341 tok/s |
| time for the request | 19.3 s | 43.7 s |
| available memory, minimum | 2.34 GiB | 3.54 GiB |
| memory swing during the prompt | 0.37 GiB | 0.22 GiB |

## Long prompts, and the variant with control vector

The model I work with every day is not the plain one but the same pack with a control vector on layers 4 to 44 and image input (`control_vector_variant` in `run-config.json`; smaller conversation cache, 2 slots / 4,608 MiB). So I measured both, each with and without the switches, on prompts cut to 70K, 100K, 128K and 250K tokens with the engine's own tokenizer. Fresh engine per size, two runs per cell (a different hidden note each time, so the prompt is read in full again), quiet profile, memory of the NAS logged once per second.

First the variant with control vector on its own: with and without the switches it loads, the log reports the vector on 41 layers, it names the colour of a test picture and makes the tool call I ask for. Reading speed there is 722 → 830 tok/s at 4K and 1,330 → 2,033 tok/s at 16K (median of three).

Prompt reading in tok/s, run 1 / run 2:

| prompt | control vector, baseline | control vector, switches | plain, baseline | plain, switches |
|---|---:|---:|---:|---:|
| 70,000 | 1,326 / 1,349 | 2,699 / 2,806 | 1,339 / 1,337 | 2,678 / 2,856 |
| 100,000 | 1,307 / 1,320 | 2,762 / 2,816 | 1,303 / 1,318 | 2,870 / 2,912 |
| 128,000 | 1,321 / 1,326 | 2,862 / 2,944 | 1,318 / 1,319 | 3,003 / 3,036 |
| 250,000 | 1,253 / 1,244 | 2,815 / 2,777 | 1,225 / 1,222 | 2,852 / 2,941 |

Seconds for the request:

| prompt | control vector, baseline | control vector, switches | plain, baseline | plain, switches |
|---|---:|---:|---:|---:|
| 70,000 | 53.1 / 52.1 | 26.2 / 25.2 | 52.6 / 52.8 | 26.5 / 24.7 |
| 100,000 | 76.9 / 76.0 | 36.6 / 35.7 | 77.0 / 76.1 | 35.2 / 34.6 |
| 128,000 | 97.2 / 96.8 | 45.2 / 43.8 | 97.4 / 97.3 | 43.9 / 42.5 |
| 250,000 | 200.0 / 201.2 | 89.2 / 90.3 | 204.5 / 205.0 | 88.0 / 85.4 |

Lowest available memory of the NAS during the request, GiB:

| prompt | control vector, baseline | control vector, switches | plain, baseline | plain, switches |
|---|---:|---:|---:|---:|
| 70,000 | 7.12 / 6.60 | 6.70 / 6.34 | 3.81 / 3.43 | 3.52 / 3.23 |
| 100,000 | 7.07 / 5.99 | 6.54 / 5.64 | 3.52 / 3.48 | 3.57 / 3.51 |
| 128,000 | 6.93 / 5.47 | 6.62 / 5.25 | 3.55 / 3.23 | 3.51 / 3.06 |
| 250,000 | 6.85 / 3.72 | 6.27 / 3.34 | 3.53 / 3.51 | 3.18 / 3.49 |

- **The switches more than double prompt reading from 70K to 250K tokens on both models**, +106 % to +124 % with the control vector and +107 % to +137 % without. A 250K prompt takes a minute and a half instead of well over three.
- All 32 requests returned HTTP 200 and all 32 hidden notes were found; no non-finite line and no 503 in the four engine logs.
- **Memory:** the switches cost about 0.6 GiB after loading (7.9 → 7.3 GiB available with the control vector, 4.45 → 3.8 GiB without). Under load the minima differ by at most 0.6 GiB. No second below 3 GiB, swap moved by at most 0.29 GiB.
- The variant with control vector has more memory to spare than the plain model here because its conversation cache is half the size. In its second run the available memory falls with the prompt length; the plain model stays at about 3.5 GiB. I read that as the conversation cache filling up, but I have not checked it.
- The memory collapse I saw at 128K with the debug switch (below) did not happen without it, with or without the switches, not even at 250K.

Limits: two runs per cell, freshly loaded, no agent running alongside, quiet profile only, answers of 10 tokens (so no decode speed from this part). I have no endurance run for the variant with control vector. The image request is reported with 36 prompt tokens by the server; the colour was named correctly, but I have not looked at how the picture reaches the model.

## Adopted on 18 Nov 2026

Both models run with the 28 switches since 18 Nov 2026. The acceptance run right after (`acceptance-after-adoption.json`): both load in both card profiles, every hidden number found, tool call correct, the variant with control vector names the colour of the test picture and its log reports the vector on 41 layers, 0 error lines. Reading at 58K: 2,908 tok/s (control vector) and 3,029 tok/s (plain), capped profile. Of five requests that models often refuse, the variant with control vector answers five without an evasive phrase, the plain model is evasive on three. How I track the switches across releases and how I get back: [docs/schalter.md](../../../docs/schalter.md).

**What this does not show:**

- 90 minutes without the debug switch, not the 105 from the report, and one card, not two.
- The drop in agent decode from 70.7 to 63.6 tok/s between the first and the last half hour is measured; I have not looked for the cause.
- The control without switches is two long requests and one agent session, right after the agent container had been restarted and the model freshly loaded, so the memory **level** is not a clean comparison; the swing is.
- With the debug switch, a 128,496-token prompt drove the NAS's available memory to zero for over a minute (78 s below 0.25 GiB, about 0.8 GiB swapped, nothing killed). Without the debug switch that does not happen up to 250,000 tokens (section above).
- The endurance run, the task set and the idle figures are from the plain model only. One card. Which of the 28 switches carry the gain, I have not taken apart.

These are environment variables of a stock engine that Strata does not document. A later release may drop or change any of them without notice.
