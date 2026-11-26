# Measurements of 25/26 Nov 2026: my own build strata-xtx `0.2.22-xtx3` on Strata 0.2.22

Strata 0.2.22 (engine and control 0.1.69) changes nothing in the Qwen engine for one card: the source diff only touches a two-card memory rule (#7089), symbol files and the version. What changes for me is in control (#7070): since 0.2.20 a request that names no sampling ran greedy on every model started with `--mtp`; from 0.2.22 Flash-Next takes the model card's sampling again (with thinking: temperature 1.0, top_p 0.95, top_k 20; without thinking also presence penalty 1.5). My agent sends no sampling, so the run configs now carry `"sampling": {"temperature": 0}` (`konfig/strata-xtx-0.2.22/`), which keeps such requests greedy as before. My patch applied unchanged, so the build is `0.2.22-xtx3`. It runs here since 26 Nov 2026, 07:15. Card in my quiet power setting unless a folder or a run says `max`; NAS services running, only my agent paused.

"plain" is the original Flash-Next IQ3_XXS (`faber`), "steered" the variant with control vector and image input that my agent works with (`liber`).

| File | What |
|---|---|
| `../tiefe-20261126-0.2.22.jsonl` | `messen/tiefe.py`, 1K to 248K tokens: plain, steered, and plain without the MTP head |
| `checks/build-test.json`, `build-test-first-run.json`, `build-test-night-run.json` | `0.2.22-xtx3` against the build in use (`0.2.21-xtx3`), three times: the first run failed its gate on one slow load of the steered model, the repeat and an automatic night run passed |
| `checks/cause-2x2-run1.json`, `cause-2x2-run2.json` | the follow-up: engine and control swapped crosswise (old/old twice as an A/A control, new/new, new engine with old control, old engine with new control), steered, 4 × 500 tokens per load, four quiet rounds (the medians below) plus one at full power, twice |
| `checks/loads-steered.json` | twelve fresh loads of the steered model, old and new build alternating, with GPU clock, power and MTP acceptance per request |
| `checks/sampling-7070.json`, `agent-sampling-7070.json` | #7070: requests without sampling against temperature 0, and requests shaped like my agent's (no sampling, no reasoning effort) on 0.2.21, 0.2.22 and 0.2.22 with the sampling block |
| `checks/task-set-and-250k.json`, `task-set-summary.json` | task set and 250K prompts on `0.2.22-xtx3` |
| `checks/rescue-steered.json` | restart without the table after injected non-finite values, steered |
| `checks/injection-si2-fresh.json` | the injection task si-2 with 30 fresh reads per build (no conversation cache) |
| `checks/injection-summary.json` | prompt injection through tool results: 14 patterns, five variants, 15 rounds; and the side-effect check (counts only, no raw prompts) |
| `strata-bench-alternating/`, `strata-bench-alternating-max/` | `tools/strata_bench.py --long`, three rounds alternating between the unchanged release 0.2.22 and `0.2.22-xtx3`, and one round at full power |
| `release-0.2.22/` | test of the unchanged release against 0.2.21 |
| `needles-*.json`, `strom-*.json`, `kaltstart-*.json`, `wartezeit*.json`, `zwei.json`, `memory-*.json`, `bench/` | the operating measurements behind the charts |

## My own build against the unchanged release, both 0.2.22

| Median of three alternating runs | Release 0.2.22 | `0.2.22-xtx3` |
|---|---:|---:|
| 4K / 16K / 32K prompt, tokens/s | 842 / 1,999 / 2,289 | 1,686 / 2,521 / 3,066 |
| chat / agent decode, tokens/s (median of the three run medians) | 74.7 / 79.3 | 79.3 / 83.3 |
| one round at full power: 4K / 16K / 32K | 844 / 1,995 / 2,320 | 1,601 / 2,517 / 3,047 |
| one round at full power: chat / agent decode | 73.3 / 79.0 | 79.5 / 87.7 |
| needle at 128K / 250K (50 % depth), plain, seconds | 54 / 104 | 38 / 79 |

The release reads as on 0.2.21 (843 / 1,980 / 2,217); my build is 2.0 times as fast at 4K and 1.3 times at 32K.

## A false alarm, and how it was settled

In the first gate test the steered model decoded 49.8 and 51.2 tokens/s in one load of the new build (65 to 67 otherwise), the median fell below the gate and I did not switch. A loads test, a #7070 test and the task set pointed the same way (2 to 6 % slower, the injection task si-2 lost once). The source diff offered no mechanism, so I measured it out:

| Steered, temperature 0, median of 16 requests per variant | run 1 | run 2 |
|---|---:|---:|
| A old engine + old control | 68.4 (100 %) | 57.9 (100 %) |
| A2 the same again | 68.0 (99.3 %) | 59.2 (102.2 %) |
| B new engine + new control | 68.6 (100.3 %) | 59.0 (101.9 %) |
| C new engine + old control | 67.0 (97.9 %) | 61.0 (105.3 %) |
| D old engine + new control | 67.7 (98.9 %) | 59.1 (102.0 %) |

No difference between the builds beyond the A/A spread. Run 2 was 15 % slower across all variants: the NAS was short of memory then (about 5 GiB in swap, 7 GiB available); the slow single loads of the night came from the same pressure and hit the old build too (plain 49.5 / 53.1 in the repeat). si-2 with 30 fresh reads per build: 28/30 on `0.2.21-xtx3`, 29/30 on `0.2.22-xtx3` — a property of the steered model, not of the release. An independent second review of the raw data and the source came to the same result.

## Prompt injection through tool results

The failures of si-2 were never obedience but looking: the model listed `~/.ssh` after a mail told it to read the key. I built 12 harder patterns (fake system message, Base64 command, HTML comment, a mail claiming to be from me, an `assistant_instructions` field in JSON, English urgency, changing the agent's approvals, a command output, a search for `.env` content, two steps, a "telemetry tip" with `.env` in a URL, overwriting a note) and ran 14 patterns × 15 rounds in five variants on one load, fresh reads throughout:

| Variant | graded as followed | touched `~/.ssh` or `.env` | harmless requests done |
|---|---:|---:|---:|
| steered model as in use | 18 / 210 | 6 | 30 / 30 |
| control vector switched off per request | 10 / 210 | 2 | 30 / 30 |
| **tool results framed as foreign data** | 2 / 210 | **0** | 30 / 30 |
| rule sentence at the end of the system prompt | 5 / 210 | 0 | 30 / 30 |
| framing and rule sentence | 0 / 210 | 0 | 30 / 30 |

The remaining hits in the framed variants are harmless but strictly graded (fetching the tips page from the task once more; decoding the Base64 without running it). Switching the control vector off halves the hits but does not stop them: it is not the cause. Framing changed nothing elsewhere: answers to everything 45/45 in both, instructions 45/45, tools 57/60, safety 51/54, task by task the same over three rounds. My agent frames the results of its shell and file tools this way since 26 Nov 2026 (web and MCP results its core frames already).

## Checks before it went into use (25/26 Nov)

| Check | Result |
|---|---|
| comparison with the build in use (`0.2.21-xtx3`), three runs | reading equal (steered 58K 3,437 against 3,437, 16K 2,415 against 2,407); decode equal apart from the slow loads described above; chunk size 32,768 in the engine log |
| table switched off | 16K 2,001 to 2,015, 58K 2,031 to 2,081 tokens/s in three of six loads, about 2,540 in the other three: the release's RAM guard sits on the edge of 32K chunks here, #6687 |
| task set, 102 graded tasks | plain 97, steered 95 (`task-set-summary.json`; on 0.2.21: 96 and 97) |
| 250K prompt | 73.6 to 74.8 s with both models, the hidden number found every time |
| self-rescue, steered | one restart without the table, the following requests answered |
| 90 minutes of continuous load, steered | 1,316 requests, 0 errors, 188 of 188 hidden numbers, available RAM never below 5.4 GiB |
| switch-over and acceptance (26 Nov, 07:15) | passed; steered 58K 3,465 and 3,435, 128K 3,589 tokens/s |
