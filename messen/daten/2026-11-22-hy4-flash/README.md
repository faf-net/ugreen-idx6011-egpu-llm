# A bigger model: Tencent Hy4-Flash (220B) on the same card

**English** · [Deutsch](README.de.md)

As of 22 Nov 2026. All figures measured on an RX 7900 XTX in the dock of a NAS with 62 GB RAM, card in my quiet mode.

Strata 0.2.18 adds a second model, Hy4-Flash, with an engine of its own (`strata-hy4`). Hy4-Flash has 220 billion parameters, 12 billion of them active, almost twice the size of Flash-Next. Strata ships it only in its own quants. I took the smallest (SQ-64, 62.0 GB, plus the 67.6 GB Engram file and the image part) and compared it with what I run, Flash-Next 125B IQ3_XXS, the original and the variant with a control vector.

Hy4-Flash is a censored model, and the Hy4 engine takes no control vector. So for me it could only have replaced the original, not the uncensored version.

## In short: it runs, but eight times slower

| Quiet mode | Flash-Next IQ3_XXS, uncensored | Flash-Next IQ3_XXS, original | Hy4-Flash SQ-64, RAM budget 36 GB |
|---|---:|---:|---:|
| Writing, 2 × 900 tokens (tokens/s) | 60.0 / 61.9 | 64.4 / 57.9 | 7.0 / 7.5 |
| Reading a short prompt (tokens/s) | 669 (4,126 tokens) | 757 (4,126) | 433 (5,346) |
| Reading a medium prompt (tokens/s) | 2,392 (16,088) | 2,308 (16,092) | 438 (20,868) |
| Reading a long prompt (tokens/s) | 3,094 (58,023) | 3,161 (58,024) | 414 (75,266) |
| Answer after the long prompt (tokens/s) | 57.5 | 51.3 | 6.8 |
| Hidden number found | 4 of 4 | 4 of 4 | 3 of 3 |
| Tool call | yes | yes | yes |
| RAM available after loading | 7.7 GiB | 4.1 GiB | 15.7 GiB, at least 7.3 during the run |
| Read from the NVMe per answer of 900 tokens | 0.1–0.2 GB | 0.1–0.2 GB | 162–165 GB |
| Load to first answer | 20 s | 20 s | 86 s |

The three prompts are the same text for all models. Hy4's tokenizer needs about 30 % more tokens for it than Qwen's, hence the token counts in brackets. A prompt of 105K Qwen tokens no longer fits Hy4's 128K context.

- **Writing is the bottleneck.** With 24 GB of VRAM, the NAS's CPU computes 36 GB of experts from RAM, and the engine reads the 9 GB of coldest experts from the NVMe on demand. The drafter (DFly2) barely helps: 0.19 accepted tokens per verify step.
- **Reading is up to 7.5 times slower.** Long prompts do not slow Hy4 further (414 to 438 tokens/s), while Flash-Next gets faster with length.
- **The NVMe reads all the time,** about 160 GB per answer of 900 tokens. Reads barely wear an SSD, but they keep the pool busy while the model writes.

## The trap: with Strata's own split, memory runs full

Strata's setup computes 9.35 GB of experts in VRAM and 46.69 GB in RAM for this machine, nothing from the SSD, and writes both into the run config (`--vram-experts-gb`, `--ram-experts-gb`). The Hy4 engine ignores both ("not used by this runner yet") and computes its RAM budget from the total memory, as if nothing else ran on the machine. So it locks all 55.8 GB of experts into RAM. On a NAS whose services keep running next to it, nothing is left:

| Split as Strata's setup writes it, night of 21/22 Nov 2026 | Result |
|---|---:|
| Writing (128K, 32K, without drafter) | 0.3–0.6 tokens/s |
| RAM available | 0 GiB, 7 GB swapped out |
| Read from the NVMe per answer of 900 tokens | 1.2–2.2 TB |
| Reading a short and a medium prompt | 217–307 tokens/s |

The fix is the environment variable `HY4_RAM_BUDGET_GB` in the run config; with 36 GB it runs stably (table above). Reported to Strata: [issue #6556](https://github.com/Niko1221/Strata/issues/6556).

## And with my own build?

strata-xtx changes nothing for Hy4. The Hy4 engine is a separate program and reads none of the 27 switches in my table (checked in the 0.2.18 source). Hy4 ran as fast with the release's control as with my build's (4K: 224 against 228, 16K: 307 against 282 tokens/s, both measured in the setup's split).

## Not measured

Task set and quality, agent runs, max mode, image input in the run with the RAM budget, a cgroup memory limit instead of `HY4_RAM_BUDGET_GB`. At 7 tokens/s the task set alone would have taken many hours, and the speed had already answered my question.

## Files

| File | Contents |
|---|---|
| `speed.json` | 7 runs in quiet mode: Flash-Next uncensored and original, Hy4-Flash with a RAM budget of 36 GB and in the setup's split (128K, 128K with the release's control, 32K, without drafter). Per run: load, tool call, writing, prompts with a hidden number, NVMe reads, lowest available RAM, mean power of NAS and dock |

## Conditions

- 21/22 Nov 2026, context 131,072, card quiet (2,800 MHz, −100 mV). Flash-Next on my own build strata-xtx on Strata 0.2.18, Hy4-Flash with `strata-hy4` 0.1.64 from the release (package `hip-rx7900`), model files checked against Strata's SHA-256.
- Temperature 0, thinking off, one request at a time, figures from the responses' `timings`. The agent on the NAS was paused during the measurements.
- NVMe bytes from the block device counters, RAM from `MemAvailable`, power of NAS and dock at the UPS, all sampled during every step.
- A round with Hy4's own CPU switches (core pinning, threads) only ran in the setup's split, i.e. while swapping, and says nothing; it is not in `speed.json`.
