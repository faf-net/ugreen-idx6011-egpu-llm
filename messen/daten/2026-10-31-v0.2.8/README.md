# Measurements of 2026-10-31: Strata 0.2.8 on this gfx1100

Prebuilt engine 0.1.54 `hip-rx7900` with control 0.1.54 (SHA-256 checked against the release's `SHA256SUMS.txt`), compared with the 0.2.3.1 packages (engine 0.1.48, control 0.1.48.1) that this machine served with since 23 Oct. Both use the same run config, so only engine and control are swapped: IQ3_XXS native pack, MTP `rt`, `--max-context 262144 --kv int8 --kv-resident 32768 --spec 4 --vram-reserve-mib 832`, conversation cache 4 slots / 9,216 MiB, default pool workers. The Docker image `ghcr.io/niko1221/strata:0.2.8-rocm-gfx110x` is included as well. Script: `messen/t028.py`.

**For this session every NAS service that was not needed was stopped** (photo library, media server, an agent, a search engine, a mail bridge, file sync). Still running, all idle: a reverse tunnel, three small MCP servers, a container agent and llama-swap. Earlier follow-ups ran with those services up, so compare across dates with care; the pairs below are the only same-session comparison.

The same data went to Strata as [PR #4851](https://github.com/Niko1221/Strata/pull/4851).

| File | What |
|---|---|
| `standard-v1/package-0.2.8/` | `strata bench run --suite standard-v1 --track custom` against the 0.2.8 packages with this run config, first thing on a fresh engine: complete |
| `standard-v1/docker-image-0.2.8-default/` | the unchanged Docker image (`MODEL=IQ3_XXS`, `API_KEY` only), `--track default`: complete |
| `strata-bench/`, `needles-32k-128k.json`, `needles-250k.json` | `tools/strata_bench.py --long` and `tools/needle_bench.py` on 0.2.8 |
| `bench-028-b028.json` | `messen/bench.py`: writing, reading, agent, 29 quality tasks |
| `version-pairs.jsonl` | 3 interleaved pairs, 0.2.8 (`b028`) against 0.2.3.1 (`p0231`), a fresh engine per run, warm-up, then 2 measured answers (63-token prompt, 900 tokens out, temperature 0) |
| `fresh-engines.jsonl` | 8 fresh 0.2.8 engines with MTP, two 4K prompts each |
| `tool-calls.jsonl` | 10 agent tasks with four declared tools on each version (`soll` = expected tool, `aufrufe` = tools called, `richtig` = expected tool first and valid JSON arguments) |
| `startup-logs/` | engine log of the package run, the container's engine log and the run config setup wrote in the image |

## Results

| median tok/s | 0.2.8 | 0.2.3.1 |
|---|---:|---:|
| pairs: decode | 61.4 | 61.6 |
| pairs: 63-token prompt | 111.2 | 121.2 |
| `strata_bench.py --long`: chat / agent decode | 68.3 / 75.6 | 67.3 / 78.3 * |
| 4K / 16K / 32K prompt | 785 / 1,212 / 1,199 | 791 / 1,218 / 1,244 * |
| `standard-v1`, package: short decode / 4K / 16K prompt | 68.3 / 791.3 / 1,201.4 | 64.6 / 799.9 / 1,203.0 * |
| `standard-v1`, Docker image defaults: short decode / 4K / 16K prompt | 67.8 / 740.2 / 1,222.2 | 67.2 / 748.6 / 1,220.4 * |

\* from the 0.2.3.1 run of 23 Oct (`../2026-10-23-v0.2.3.1/`), with the NAS services running. Only the pairs ran with both versions in the same session.

- **Decode is unchanged** in the same-session pairs; across dates the other decode numbers move a few percent either way. Prompt reading from 4K up is unchanged as well.
- **Reading the short 63-token prompt was about 8 % slower on 0.2.8 in the pairs** (ranges 90.7-119.2 against 113.3-126.2 tok/s, they overlap). On 23 Oct 0.2.3.1 itself read the same prompt at 111.7 tok/s, so part of the gap may be 0.2.3.1 profiting more from the quiet machine. A small effect where the fixed cost of a request dominates; no cause claimed.
- `standard-v1` complete with 12/12 on both tracks, our task set 29 of 29, needles 6/6 at 32K and 128K and 3/3 at 250K (223-237 s for 251,626 tokens), 8 of 8 fresh engines normal (694-749 tok/s).
- **The unchanged Docker image leaves 854 MiB of VRAM free after loading** and did not warn about low VRAM during the run (0.2.3: 594 MiB and one warning). Setup still chooses `--max-context 131072 --vram-reserve-mib 700 --pool-workers 10`.
- **Tool calls:** all 20 answers on both versions were well-formed tool calls (0.2.8 called the expected tool first 10 of 10 times, 0.2.3.1 9 of 10: it looked at the directory with `run_command` before writing a file). So this sample did not exercise 0.2.8's new recovery of slightly malformed calls.
