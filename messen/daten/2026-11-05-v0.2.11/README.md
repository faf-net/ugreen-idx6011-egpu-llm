# Measurements of 2026-11-05: Strata 0.2.11 on this gfx1100

Prebuilt engine 0.1.57 `hip-rx7900` with control 0.1.57 (SHA-256 checked against the release's `SHA256SUMS.txt`), compared with the 0.2.10 packages (engine and control 0.1.56) that this machine served with until then. Both use the same run config, so only engine and control are swapped: IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB, default pool workers. The Docker image `ghcr.io/niko1221/strata:0.2.11-rocm-gfx110x` is included as well, with its defaults.

The release notes of 0.2.11 say the `hip-rx7900` package had not been run with a model by the project, so this is, as far as I know, its first run on a real RX 7900 XTX.

**Unlike the 0.2.8 follow-up, the NAS services were running** (photo library, media server, search, mail bridge, file sync); only my agent was paused. The run is my automated release test, which runs every step one after the other on the same afternoon. Compare across dates with care; the pairs below are the only same-session comparison.

The same data went to Strata as [issue #5321](https://github.com/Niko1221/Strata/issues/5321).

| File | What |
|---|---|
| `standard-v1/package-0.2.11/` | `strata bench run --suite standard-v1 --track custom` against the 0.2.11 packages with this run config: complete |
| `standard-v1/docker-image-0.2.11-default/` | the unchanged Docker image (`MODEL=IQ3_XXS`, `API_KEY` only), `--track default`: complete |
| `strata-bench/`, `needles-32k-128k.json`, `needles-250k.json` | `tools/strata_bench.py --long` and `tools/needle_bench.py` on 0.2.11 |
| `bench-0211.json` | `messen/bench.py`: writing, reading, agent, 29 quality tasks |
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.11 (`t-neu`) against 0.2.10 (`t-prod`), a fresh engine per run, warm-up, then 2 measured answers (63-token prompt, 900 tokens out, temperature 0) |
| `fresh-engines.jsonl` | 8 fresh 0.2.11 engines with MTP, two ~3.8K prompts each |
| `power-samples.jsonl` | card power (W) and VRAM in use (GiB) every 0.5 s during `bench.py`, by phase (`test`) |

## Results

| median tok/s | 0.2.11 | 0.2.10 |
|---|---:|---:|
| pairs: decode | 60.9 (57.1-61.1) | 59.8 (47.6-61.8) |
| pairs: 63-token prompt | 118.1 (102.2-120.9) | 109.0 (63.8-120.1) |
| `strata_bench.py --long`: chat / agent decode | 64.3 / 80.9 | |
| 4K / 16K / 32K prompt | 781 / 1,212 / 1,226 | |
| `standard-v1`, package: short decode / 4K / 16K prompt | 67.0 / 796.6 / 1,191.5 | 65.6 / 797.2 / 1,204.4 * |
| `standard-v1`, Docker image defaults: short decode / 4K / 16K prompt | 65.0 / 757.6 / 1,181.7 | |

\* 0.2.10 run of 3 Nov, from my nightly release test with the same services up. Only the pairs ran with both versions in the same session.

- **Decode is unchanged.** The two low 0.2.10 values in the pairs (48.1 and 47.6 tok/s) come from one engine start; the other four are 58.6-61.8. I do not count that as a 0.2.10 problem.
- Reading the short prompt: 118.1 against 109.0 tok/s, but the ranges overlap and 0.2.10's median is pulled down by one outlier (63.8 tok/s, second answer of pair 2). No claim.
- `standard-v1` complete with 12/12 on both tracks, our task set 29 of 29, needles 6/6 at 32K and 128K (28-29 s and 99-113 s) and 1/1 at 250K (239 s for 251,626 tokens), all 8 fresh engines healthy.
- **Fresh engines:** the very first prompt after the first start read at 457 tok/s, the second prompt of that engine at 461; all other engines read at 670-750 tok/s. A slower first start after unpacking, not repeated on the following seven.
- **Needles:** the 128K and 250K times are about 15 % shorter than in the 0.2.10 night run (120-132 s and 283 s), but they match the quiet 0.2.8 run (98-111 s, 223-237 s). Different dates and conditions, so I do not credit 0.2.11 with it.
- **Card power** (median during the phase): idle 50 W, writing 208 W, reading a 32K prompt 264 W, peak 353 W while reading 8K prompts. VRAM in use stays at 23.7 GiB.
- No broken streams, no failed requests.
