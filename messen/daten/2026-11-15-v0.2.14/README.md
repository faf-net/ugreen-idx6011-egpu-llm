# Measurements of 2026-11-15: Strata 0.2.14 on this gfx1100

Prebuilt engine 0.1.60 `hip-rx7900` with control 0.1.60 (SHA-256 checked against the release's `SHA256SUMS.txt`), compared with the 0.2.12 packages (engine and control 0.1.58) that this machine serves with. Same run config as for 0.2.12 (`konfig/strata-0.2.12/faber.json`), only engine and control swapped: IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB, default pool workers. The run config sets `STRATA_HIPBLASLT_TUNING` to the gfx1100 table explicitly, and the 0.2.14 engine logs `prefill gemm: hipBLASLt tuning enabled (26 rows, gfx1100, version 100200)`.

Everything ran in the evening of 15 Nov with the NAS services running; only my agent was paused. The release notes for 0.2.14 carry no measurement for the RX 7900 under Linux, so this is one. **Tested, not in production yet:** this NAS still serves with 0.2.12 until my own task set has run on 0.2.14.

| File | What |
|---|---|
| `standard-v1/package-0.2.14/` | `strata bench run --suite standard-v1 --track custom` against the 0.2.14 packages with this run config: complete, sanity 11 of 12 |
| `strata-bench/`, `needles-32k-128k.json`, `needles-250k.json` | `tools/strata_bench.py --long` and `tools/needle_bench.py` on 0.2.14 |
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.14 (`t-neu`) against 0.2.12 (`t-prod`), fresh engine per run, 63-token prompt, 900 tokens out, temperature 0 |
| `fresh-engines.jsonl` | 8 fresh 0.2.14 engines with MTP, two ~3.8K prompts each |

There is no Docker image run this time: `ghcr.io/niko1221/strata:0.2.14-rocm-gfx110x` was not published when I measured. The task-set summary follows once that run is done.

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
- **The agent test of `strata_bench.py` decodes slower in this run, cause open.** Median over all 18 agent requests: 63.7 tok/s, against 70.8 on 0.2.13, 71.8 on 0.2.12 and 73.5 on 0.2.11; the tool's own summary (15 requests, without each session's first turn) says 70.4 against 73.7 and 73.2; chat decode is 62.9 against 64.1 and 68.1. The test is small (756 generated tokens in 18 requests, single requests between 41 and 101 tok/s on every version), the answers differ in wording from 0.2.13, and the MTP drafter's proposals were accepted less often (54 % against 56 % and 59 %). The same-session pairs with 900 tokens each show no difference. So I report the number and do not call it a regression.
- **Prompt reading is faster from 16K up.** 4K is unchanged (800 against 799 on 0.2.13), 16K is 17 % faster (1,411 against 1,203), 32K 14 % faster (1,390 against 1,217), and the first token of a 16K prompt comes after 11.6 s instead of 13.7 s. The short 63-token prompt is 10 % faster in the same-session pairs. This fits the release notes: the prompt now runs on Strata's own kernels. The long-prompt comparison is across sessions, so take the size of the gain with that in mind.
- **Needles 7/7**, all found. 128K took 66-96 s and 250K 206 s; on 0.2.13 they took 99-112 s and 238 s.
- **`standard-v1` complete, sanity 11 of 12.** Not passed: T2 ("Use get_weather for Zagreb in celsius", temperature 1.0, thinking on). The model returned no structured tool call; its reasoning says it had already called the tool and got an empty result, and it then answered "No weather data was returned for Zagreb." The other three tool-call checks passed. On 0.2.11, 0.2.12 and 0.2.13 this suite passed 12 of 12 here. One run does not tell me whether that is the sampling or the new version.
- **No driver pauses on this card.** The release notes list "the graphics driver paused the GPU" for a Radeon R9700 under Linux. In 192 kB of engine log from this session the line does not appear, nor a stall or a GPU reset; the kernel log is clean too. The card is an RX 7900 XTX on OCuLink, kernel 6.18.15.
- My small task set: 28 of 29 (0.2.12: 27, 0.2.13: 29). One task either way is what this set does between runs of the same version.
