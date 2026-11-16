# Measurements of 2026-11-16: Strata 0.2.15 on this gfx1100

Control 0.1.61 with the prebuilt engine 0.1.60 `hip-rx7900` (SHA-256 checked against the release's `SHA256SUMS.txt`). The engine is the same as in 0.2.14, only the control program is new. Compared with the 0.2.14 packages this machine serves with, same run config (`konfig/strata-0.2.14/faber.json`): IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB.

Everything ran on 16 Nov with the NAS services running; only my agent was paused. **Tested, not adopted:** this NAS stays on 0.2.14.

| File | What |
|---|---|
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.15 (`t-neu`) against 0.2.14 (`t-prod`), fresh engine per run, 63-token prompt, 900 tokens out, temperature 0 |
| `standard-v1/package-0.2.15/` | `strata bench run --suite standard-v1 --track custom` against the 0.2.15 packages with this run config: complete, sanity 12 of 12 |
| `strata-bench-alternating/` | `tools/strata_bench.py --long` three times each on 0.2.14 and 0.2.15 in one session, fresh engine per run, order swapped each round |

## 0.2.15 against 0.2.14

| Median | 0.2.15 | 0.2.14 |
|---|---:|---:|
| pairs, same session: decode tok/s | 59.2 (57.8-61.3) | 59.1 (58.0-61.6) |
| pairs, same session: 63-token prompt tok/s | 118.6 | 118.6 |
| `strata_bench.py --long`, 3 alternating runs: chat / agent decode | 65.1 / 73.4 | 64.0 / 70.8 |
| same runs: 4K / 16K / 32K prompt | 786 / 1,395 / 1,377 | 786 / 1,392 / 1,375 |
| `standard-v1`, package: short decode / 4K / 16K prompt | 68.4 / 747 / 1,416 | |

The pairs measure short answers on text that is hard to predict, so the MTP head is right less often; that is why they come to about 59 tokens/s and not to the 66 of long answers.

Equally fast. Prompt reading is equal to the token in the alternating runs; decode lies within the scatter this test shows for one and the same release (in the night to 16 Nov, 0.2.12 and 0.2.14 came to 72.5 and 72.7 in the agent part). `standard-v1` got 747 tokens/s at 4K in its single run; the three `strata_bench.py` runs give 786 for both releases.

My small task set (35 tasks: tools, code and a few others, temperature 0) passed 34 of 35 on 0.2.15 and 35 of 35 on 0.2.14 the same day: tools 20 of 20, code 14 of 15. The one that failed is a code task that flips between runs. Only the counts are given here.

Reported to Strata as a comment in [#6056](https://github.com/Niko1221/Strata/issues/6056).
