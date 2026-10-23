# Measurements of 2026-10-23 (evening): Strata 0.2.3.1 on this gfx1100

Prebuilt engine 0.1.48 `hip-rx7900` with control 0.1.48.1 (SHA-256 checked against the release's `SHA256SUMS.txt`), compared with the 0.2.2 packages (engine 0.1.47, control 0.1.47) that this machine served with since 21 Oct. Both use the same run config, so only engine and control are swapped: IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB, default pool workers. The Docker image `ghcr.io/niko1221/strata:0.2.3-rocm-gfx110x` is included as well. Script: `messen/t0231.py`.

| File | What |
|---|---|
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.3.1 (`b023`) against 0.2.2 (`p022`), a fresh engine per run, warm-up, then 2 measured answers (63-token prompt, 900 tokens out, temperature 0) |
| `no-table-env.jsonl` | 0.2.3.1 without `STRATA_HIPBLASLT_TUNING` in the run config (`b023n`) |
| `fresh-engines.jsonl` | 8 fresh 0.2.3.1 engines with MTP, two 4K prompts each |
| `strata-bench/`, `needles-32k-128k.json` | `tools/strata_bench.py --long` and `tools/needle_bench.py` on 0.2.3.1 |
| `bench-0231-b023.json` | `messen/bench.py`: writing, reading, agent, 29 quality tasks |
| `standard-v1/package-0.2.3.1/` | `strata bench run --suite standard-v1 --track custom` against that server: complete |
| `standard-v1/docker-image-0.2.3-default/` | the unchanged Docker image (`MODEL=IQ3_XXS`, `API_KEY` only), `--track default`: complete |
| `startup-logs/` | engine log lines of the package runs (with and without the table variable) and of the container start, plus the run config setup wrote |
| `memory.json` | RAM and VRAM with `faber` loaded and idle, measured the same evening (chart `bilder/speicher-*.png`) |

## Results

| median tok/s | 0.2.3.1 | 0.2.2 |
|---|---:|---:|
| pairs: decode | 62.5 | 61.6 |
| pairs: 63-token prompt | 111.7 | 112.3 |
| `strata_bench.py --long`: chat / agent decode | 67.3 / 78.3 | 66.0 / 72.5 * |
| 4K / 16K / 32K prompt | 791 / 1,218 / 1,244 | 736 / 1,211 / 1,222 * |
| `standard-v1`, package: short decode / 4K / 16K prompt | 64.6 / 799.9 / 1,203.0 | 70.6 / 746.1 / 1,220.7 * |
| `standard-v1`, Docker image defaults: short decode / 4K / 16K prompt | 67.2 / 748.6 / **1,220.4** | 62.0 / 667.1 / 780.8 |

\* from the 0.2.2 run of 21 Oct (`../2026-10-21-v0.2.2/`), before `--kv-resident 32768` and the 9 GiB conversation cache were added. Only the pairs ran with both versions on the identical config.

- **The engine finds its hipBLASLt table by itself now, also on gfx1100.** Without `STRATA_HIPBLASLT_TUNING` the log still says `hipBLASLt tuning enabled (26 rows, gfx1100, version 100200)`. That is why the unchanged Docker image reads 16K prompts 56 % faster than the 0.2.2 image (time to first token 21.0 s → 13.5 s).
- Needles 6/6 at 32K and 128K. 8 of 8 fresh engines read the 4K prompt at normal speed (706-749 tok/s, 0.2.2: 659-701). Quality tasks 29 of 29 (0.2.2: 28 of 29, the difference is one near-tie answer).
- The Docker image setup still chose `--max-context 131072 --vram-reserve-mib 700 --pool-workers 10` and warned once that `only 427 MiB of VRAM free at the start of this request`.
- The first 128K prompt of this run took 217 s, where every earlier run needed about 108 s. A separate A/B (`messen/t128.py`, results in `t128/`), fresh engine each time, identical config, alternating: 0.2.3.1 110.5 / 110.8 s, 0.2.2 111.1 / 111.6 s, needle found each time. No regression; the 217 s was a one-off.
