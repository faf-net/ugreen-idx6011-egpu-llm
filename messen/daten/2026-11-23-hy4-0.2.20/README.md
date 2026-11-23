# Hy4-Flash (220B) on Strata 0.2.20: the RAM trap is fixed

**English** · [Deutsch](README.de.md)

As of 23 Nov 2026. Re-test for [Strata issue #6556](https://github.com/Niko1221/Strata/issues/6556) on the same machine as in [`../2026-11-22-hy4-flash/`](../2026-11-22-hy4-flash/): RX 7900 XTX in the dock of a NAS with 62.3 GiB RAM, NAS services running, only my agent paused.

On 0.2.18 the Hy4 engine ignored the RAM split that Strata's setup writes and budgeted with the whole RAM: memory ran full, the kernel swapped, and Hy4-Flash wrote at 0.3 to 0.6 tokens/s. On 0.2.20 setup writes a different split for this machine (16.71 GB of experts on the card, 39.33 GB in RAM, on 0.2.18 it was 9.35 / 46.69), and the engine follows it. I ran exactly those flags, without `HY4_RAM_BUDGET_GB`, and the old workaround for comparison. Each variant was loaded fresh, alternating with Flash-Next, first in my quiet power setting, then at full power.

| Quiet mode | Flash-Next, with control vector | Flash-Next, original | Hy4-Flash, setup split 0.2.20 | Hy4-Flash, `HY4_RAM_BUDGET_GB=36` |
|---|---:|---:|---:|---:|
| writing, 2 × 900 tokens, tokens/s | 64.8 / 65.5 | 63.7 / 60.3 | 12.7 / 13.0 | 14.7 / 17.3 |
| reading a short prompt, tokens/s | 681 | 719 | 409 | 343 |
| reading a medium prompt, tokens/s | 2,403 | 2,558 | 512 | 371 |
| reading a long prompt, tokens/s | 3,425 | 3,496 | 641 | 384 |
| read from the NVMe per answer of 900 tokens | 0.1 GB | 0.1 GB | 2.3–2.4 GB | 87–99 GB |
| read from the NVMe for the long prompt | 0.0 GB | 0.0 GB | 9.4 GB | 84 GB |
| RAM available, lowest during the run | 7.3 GiB | 3.8 GiB | 9.6 GiB | 13.0 GiB |
| swap | unchanged | unchanged | unchanged | unchanged |
| hidden number found, tool call | yes, yes | yes, yes | yes, yes | yes, yes |

The prompts are the same text for every model; Flash-Next counts 4,125 / 16,088 / 58,021 tokens, Hy4's tokenizer 5,346 / 20,866 / 75,268. At full power Hy4 with the setup split gave the same figures (12.8 / 13.4 tokens/s, 641 tokens/s on the long prompt), the variant with control vector as well (65.5 / 65.8). After the Hy4 runs the variant with control vector answered, called a tool, read an image and loaded its vector.

- **The trap is gone.** The engine log no longer says `not used by this runner yet`, the RAM budget is 39.3 GB as setup wrote it, and 719 of the coldest experts (1.6 GB) stay on the SSD. Available RAM never went below 9.5 GiB, and memory pressure (`/proc/pressure/memory`, some avg300) stayed at 1.0 to 1.3 % instead of about 45 %.
- **The setup split is the better one.** It puts more experts on the card, so it reads long prompts 1.7 times as fast as the old workaround and reads a tenth as much from the NVMe. It writes a little slower.
- **The old workaround also got faster:** 14.7 to 17.3 tokens/s on 0.2.20 against 7.0 to 7.5 on 0.2.18, with the same answers of 900 tokens.
- **For daily use it changes nothing.** Hy4-Flash still writes at a fifth of Flash-Next's speed, is censored and takes no control vector. Flash-Next stays.

`speed-and-memory.json`: every run with its engine log lines (paths removed, answer texts left out).
