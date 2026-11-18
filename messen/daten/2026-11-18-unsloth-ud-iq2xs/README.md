# Unsloth UD-IQ2_XS v3.1 against my IQ3_XXS file on Strata

**English** · [Deutsch](README.de.md)

As of 18 Nov 2026. Every number is measured, on an RX 7900 XTX in the dock of a NAS with 62 GB RAM, Strata 0.2.14.

I checked whether the Unsloth quants in version 3.1 (since 4 Nov 2026) would be a better base for my model `faber` (Qwen3.8-Flash-Next 125B, ISTA GSQ-RCO IQ3_XXS). UD-IQ2_XS v3.1 is the same size on disk as my file (75.8 GB, experts 47.0 GB) and runs with the same run config.

## Result in short

| | faber | UD-IQ2_XS v3.1 | difference |
|---|---:|---:|---:|
| perplexity overall (lower is better) | 4.153 | 3.854 | −7.2 % |
| perplexity, agent transcript | 4.927 | 4.119 | −16.4 % |
| chat decode, quiet (tok/s) | 63.9 | 68.8 | +7.7 % |
| agent decode, quiet (tok/s) | 77.2 | 71.5 | −7.4 % |
| reading a 16K prompt, quiet (tok/s) | 1,404.8 | 1,261.5 | −10.2 % |
| reading a 16K prompt with 28 switches, quiet (tok/s) | 2,361.3 | 2,106.2 | −10.8 % |

- On the yardstick the Unsloth file is better than mine in all five sections.
- Speed is mixed: faster in chat, a little slower in the agent test, and it reads long prompts about 10 % slower. That disadvantage remains with the switches from the rdna3 measurement; they lift both files by about two thirds.
- Memory and power draw are the same.
- The variant with control vector loads on the Unsloth file, and the vector takes effect (five requests that models often refuse: 5 answered instead of 1).

## What is still missing

- The task set with tool chains. Better perplexity does not necessarily mean more solved tasks.
- For the variant with control vector: speed, memory on long prompts, image input, tool call and a run with the switches.
- A comparison against the original (Q8_0 does not fit into 62 GB). "Same token" and KL therefore only say how different two files are, not which is closer to the original.
- I have not measured where the reading disadvantage comes from.

For comparison: the larger UD-IQ3_XXS v3.1 scored 3.929 on the same yardstick but needs 7.8 GB more memory and was slower in my setup; I discarded it.

## Files

| File | Content |
|---|---|
| `massstab.json` | perplexity, same token and KL per section, four comparisons |
| `tempo-ohne-schalter.json` | 12 runs (2 files × 3 rounds × quiet/max), single values and medians |
| `tempo-mit-schaltern.json` | the same with the 28 environment switches on both files |
| `ladeprobe.json` | loading with the faber config and with the variant with control vector, counts only |

## Conditions

- Yardstick: `tools/quant_quality.py`, experts on the CPU, FP16 K/V, 5 × 999 positions, teacher-forced. A single text set.
- Speed: `tools/strata_bench.py` without `--long`, 3 rounds in alternating order, per load one run with the card capped ("quiet") and one at full power ("max"). Given is the median of 3 rounds. My agent kept running alongside; every run was checked for not having been disturbed.
- Pack of the Unsloth file built with `tools/iq_pack.py --compat-bf16` (195 tensors rounded, largest error 0.0184).
- Without and with switches were measured at different times. The pairs within one file are cleanly comparable.
