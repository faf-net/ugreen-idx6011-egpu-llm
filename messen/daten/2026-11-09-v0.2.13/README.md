# Measurements of 2026-11-09: Strata 0.2.13 on this gfx1100

Prebuilt engine 0.1.59 `hip-rx7900` with control 0.1.59 (SHA-256 checked against the release's `SHA256SUMS.txt`), compared with the 0.2.12 packages (engine and control 0.1.58) that this machine serves with. Same run config as for 0.2.12 (`konfig/strata-0.2.12/faber.json`), only engine and control swapped: IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB, default pool workers. The production config sets `STRATA_HIPBLASLT_TUNING` to the gfx1100 table explicitly. The Docker image `ghcr.io/niko1221/strata:0.2.13-rocm-gfx110x` is included with its defaults, and once more with only `STRATA_HIPBLASLT_TABLE=on` added.

Everything ran in the afternoon of 9 Nov with the NAS services running; only my agent was paused.

The same data went to Strata as [issue #5666](https://github.com/Niko1221/Strata/issues/5666).

| File | What |
|---|---|
| `standard-v1/package-0.2.13/` | `strata bench run --suite standard-v1 --track custom` against the 0.2.13 packages with this run config: complete |
| `standard-v1/docker-image-0.2.13-default/` | the unchanged Docker image (`MODEL=IQ3_XXS`, `API_KEY` only), `--track default`: complete |
| `standard-v1/docker-image-0.2.13-table-on/` | the same image with only `STRATA_HIPBLASLT_TABLE=on` added: complete |
| `strata-bench/`, `needles-32k-128k.json`, `needles-250k.json` | `tools/strata_bench.py --long` and `tools/needle_bench.py` on 0.2.13 |
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.13 (`t-neu`) against 0.2.12 (`t-prod`), fresh engine per run, 63-token prompt, 900 tokens out, temperature 0 |
| `fresh-engines.jsonl` | 8 fresh 0.2.13 engines with MTP, two ~3.8K prompts each |
| `task-set-summary.json` | my own task set (114 German-language tasks, 102 auto-graded, temperature 0, thinking on, up to 8,000 tokens): 0.2.12 (8 Nov) and 0.2.13 (9 Nov), per category |

## 0.2.13 against 0.2.12

| | 0.2.13 | 0.2.12 |
|---|---:|---:|
| pairs, same session: decode tok/s | 60.0 (58.1-61.4) | 60.7 (57.4-61.9) |
| pairs: 63-token prompt tok/s | 111.8 | 108.7 |
| task set: passed (of 102 auto-graded) | 97 | 98 * |
| task set: wall time, 114 tasks / output tokens | 1,381 s / 70,716 | 1,430 s / 72,321 * |
| task set: decode median | 75.8 | 75.6 * |
| `standard-v1`, package: short decode / 4K / 16K prompt | 67.7 / 798.6 / 1,203.3 | 63.6 / 788.4 / 1,201.7 * |
| `strata_bench.py --long`: chat / agent decode, 4K / 16K / 32K prompt | 64.1 / 73.7, 782 / 1,203 / 1,217 | 68.1 / 73.2, 781 / 1,200 / 1,217 * |

\* 0.2.12 runs of 8 Nov, not the same session. Only the pairs ran both versions back to back.

- **Equal.** Decode within the noise in the pairs, same prompt speed. The task set differs by one task: `code-2-iban` passed on 0.2.12 and fails on 0.2.13 (the model maps IBAN letters to one digit instead of two in the mod-97 loop). On this set a single task flips between runs of the same version too, so I read nothing into it. 41 of 114 answers are identical to 0.2.12 at temperature 0 (text and tool calls).
- `standard-v1` complete, sanity 12/12 on all three runs. Needles 7/7: 32K about 28 s, 128K 99-112 s, 250K 238 s. Fresh engines read their prompts at 680-746 tok/s.

## The Docker image no longer uses the gfx1100 hipBLASLt table on Linux

| `standard-v1`, Docker image, track default | short decode | 4K prompt | 16K prompt |
|---|---:|---:|---:|
| 0.2.12 image, defaults (8 Nov) | 69.1 | 756.3 | 1,185.8 |
| **0.2.13 image, defaults** | 61.9 | **649.2** | **769.2** |
| 0.2.13 image, `STRATA_HIPBLASLT_TABLE=on` | 67.4 | 765.8 | 1,192.5 |

The 0.2.13 engine logs `hipBLASLt tuning table: gfx1100-hipblaslt-100200.txt is in this package and not used by default (faster prompts, but answers can differ in the last digits); STRATA_HIPBLASLT_TABLE=on uses it`. The release notes mention this for Windows RX 7900 / RX 9070; in the Linux image `0.2.13-rocm-gfx110x` it applies too, and prompt reading drops by 14 % at 4K and 35 % at 16K. With the switch on it is back at the 0.2.12 level. My own run config sets the table explicitly and is not affected.
