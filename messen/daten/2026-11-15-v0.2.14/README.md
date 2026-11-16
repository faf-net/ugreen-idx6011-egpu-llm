# Measurements of 2026-11-15: Strata 0.2.14 on this gfx1100

Prebuilt engine 0.1.60 `hip-rx7900` with control 0.1.60 (SHA-256 checked against the release's `SHA256SUMS.txt`), compared with the 0.2.12 packages (engine and control 0.1.58) that this machine serves with. Same run config as for 0.2.12 (`konfig/strata-0.2.12/faber.json`), only engine and control swapped: IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB, default pool workers. The run config sets `STRATA_HIPBLASLT_TUNING` to the gfx1100 table explicitly, and the 0.2.14 engine logs `prefill gemm: hipBLASLt tuning enabled (26 rows, gfx1100, version 100200)`.

Everything ran in the evening of 15 Nov with the NAS services running; only my agent was paused. The release notes for 0.2.14 carry no measurement for the RX 7900 under Linux, so this is one. **Tested, not in production yet:** this NAS still serves with 0.2.12. My own task set and a second, alternating `strata_bench` session ran in the night to 16 Nov and are below.

| File | What |
|---|---|
| `standard-v1/package-0.2.14/` | `strata bench run --suite standard-v1 --track custom` against the 0.2.14 packages with this run config: complete, sanity 11 of 12 |
| `strata-bench/`, `needles-32k-128k.json`, `needles-250k.json` | `tools/strata_bench.py --long` and `tools/needle_bench.py` on 0.2.14 |
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.14 (`t-neu`) against 0.2.12 (`t-prod`), fresh engine per run, 63-token prompt, 900 tokens out, temperature 0 |
| `fresh-engines.jsonl` | 8 fresh 0.2.14 engines with MTP, two ~3.8K prompts each |
| `strata-bench-alternating/` | night to 16 Nov: `tools/strata_bench.py --long` three times each on 0.2.12 and 0.2.14 in one session, fresh engine per run, order swapped each round; `summary.json` has the figures used below |
| `task-set-summary.json` | my own task set (114 German-language tasks, 102 auto-graded, temperature 0, thinking on, up to 8,000 tokens): 0.2.12 (13 Nov) and 0.2.14 (16 Nov), per category |

There is no Docker image run this time: `ghcr.io/niko1221/strata:0.2.14-rocm-gfx110x` was not published when I measured.

The same data went to Strata as [issue #6056](https://github.com/Niko1221/Strata/issues/6056).

## 0.2.14 against 0.2.12 and 0.2.13

| | 0.2.14 | 0.2.12 | 0.2.13 |
|---|---:|---:|---:|
| pairs, same session: decode tok/s | 59.3 (57.8-61.5) | 60.5 (55.5-61.0) | |
| pairs, same session: 63-token prompt tok/s | 117.9 (102.2-123.9) | 107.5 (101.8-114.3) | |
| `standard-v1`, package: short decode / 4K / 16K prompt | 67.8 / 799.9 / 1,411.2 | 63.6 / 788.4 / 1,201.7 * | 67.7 / 798.6 / 1,203.3 * |
| `standard-v1`: first token of the 16K prompt | 11.6 s | | 13.7 s * |
| `strata_bench.py --long`: chat / agent decode | 62.9 / 70.4 | 68.1 / 73.2 * | 64.1 / 73.7 * |
| `strata_bench.py --long`: 4K / 16K / 32K prompt | 789 / 1,405 / 1,390 | 781 / 1,200 / 1,217 * | 782 / 1,203 / 1,217 * |
| needles: 32K / 128K / 250K, seconds | 27-28 / 66-96 / 206 | 28-29 / 120-158 / 294 * | 28 / 99-112 / 238 * |
| fresh engines, ~3.8K prompt tok/s | 637-758 | 593-756 * | 680-746 * |

\* earlier sessions (0.2.12 on 8 Nov, 0.2.13 on 9 Nov), not the same session. Only the pairs ran both versions back to back.

- **Decode is equal.** 59.3 against 60.5 tok/s in the pairs, with overlapping ranges.
- **The agent test of `strata_bench.py` decodes slower in this run. The alternating session below shows it was scatter.** Median over all 18 agent requests: 63.7 tok/s, against 70.8 on 0.2.13, 71.8 on 0.2.12 and 73.5 on 0.2.11; the tool's own summary (15 requests, without each session's first turn) says 70.4 against 73.7 and 73.2; chat decode is 62.9 against 64.1 and 68.1. The test is small (756 generated tokens in 18 requests, single requests between 41 and 101 tok/s on every version), the answers differ in wording from 0.2.13, and the MTP drafter's proposals were accepted less often (54 % against 56 % and 59 %). The same-session pairs with 900 tokens each show no difference. So I reported the number and did not call it a regression; three alternating runs per version then came out equal.
- **Prompt reading is faster from 16K up.** 4K is unchanged (800 against 799 on 0.2.13), 16K is 17 % faster (1,411 against 1,203), 32K 14 % faster (1,390 against 1,217), and the first token of a 16K prompt comes after 11.6 s instead of 13.7 s. The short 63-token prompt is 10 % faster in the same-session pairs. This fits the release notes: the prompt now runs on Strata's own kernels. The long-prompt comparison is across sessions, so take the size of the gain with that in mind.
- **Needles 7/7**, all found. 128K took 66-96 s and 250K 206 s; on 0.2.13 they took 99-112 s and 238 s.
- **`standard-v1` complete, sanity 11 of 12.** Not passed: T2 ("Use get_weather for Zagreb in celsius", temperature 1.0, thinking on). The model returned no structured tool call; its reasoning says it had already called the tool and got an empty result, and it then answered "No weather data was returned for Zagreb." The other three tool-call checks passed. On 0.2.11, 0.2.12 and 0.2.13 this suite passed 12 of 12 here. One run does not tell me whether that is the sampling or the new version.
- **No driver pauses on this card.** The release notes list "the graphics driver paused the GPU" for a Radeon R9700 under Linux. In 192 kB of engine log from this session the line does not appear, nor a stall or a GPU reset; the kernel log is clean too. The card is an RX 7900 XTX on OCuLink, kernel 6.18.15.
- My small task set: 28 of 29 (0.2.12: 27, 0.2.13: 29). One task either way is what this set does between runs of the same version.

## Night to 16 Nov: three alternating `strata_bench` runs per version, and my task set

The single `strata_bench` run above compared 0.2.14 with runs from other days. To separate scatter from a real difference I ran `strata_bench.py --long` three times each on 0.2.12 and 0.2.14 in one session, with a fresh engine for every run and the order swapped each round.

| median of three runs | 0.2.14 | 0.2.12 |
|---|---:|---:|
| agent decode, all 18 requests: median tok/s | 72.7 | 72.5 |
| agent decode over the whole test (tokens / decode time) | 72.9 | 73.1 |
| agent: accepted MTP draft tokens | 60.5 % | 58.4 % |
| chat decode over the whole test | 67.9 | 67.2 |
| 64-token turns of the first agent session / of the second and third (mean) | 69.8 / 84.7 | 70.9 / 83.3 |
| 4K / 16K / 32K prompt tok/s | 789 / 1,387 / 1,380 | 775 / 1,196 / 1,215 |

- **Agent and chat decode are equal.** The 63.7 tok/s of the single run on 15 Nov was scatter: single runs of this small test range from 66 to 76 tok/s over the whole test on both versions.
- **The first agent session after a fresh start is the slow one on both versions**, about 70 tok/s against about 84 in the second and third. That is a property of the test, not of 0.2.14.
- **The prompt gain holds in the same session:** 16K is 16 % faster (1,387 against 1,196), 32K 14 % (1,380 against 1,215), 4K 2 %. With this the long-prompt numbers above no longer rest on a comparison across days.

My task set on 0.2.14, same run config, against the 0.2.12 run of 13 Nov:

| | 0.2.14 | 0.2.12 |
|---|---:|---:|
| passed, of 102 auto-graded | 98 | 96 * |
| code / logic / facts / tool calls / agent safety / instruction / long context | 15 / 15 / 12 / 20 / 17 / 15 / 4 | 14 / 14 / 12 / 20 / 17 / 15 / 4 |
| wall time, 114 tasks / output tokens | 1,489 s / 82,901 | 1,622 s / 87,007 |
| decode median tok/s | 75.2 | 73.5 |

\* one facts task graded by hand, see `task-set-summary.json`.

Two tasks that failed on 0.2.12 pass on 0.2.14 (one code, one logic task), nothing that passed fails. On this set one or two tasks flip between runs of the same version, so I read it as equal, not as better. 41 of 114 answers are identical to 0.2.12 at temperature 0. Decode on real tasks with 83,000 output tokens is not slower. The engine logs of this night have no "graphics driver paused the GPU" line either.
