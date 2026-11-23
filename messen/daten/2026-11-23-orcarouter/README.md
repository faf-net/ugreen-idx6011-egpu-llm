# An uncensored Flash-Next from OrcaRouter against my control vector

**English** · [Deutsch](README.de.md)

As of 23 Nov 2026. All figures measured on an RX 7900 XTX in the dock of a NAS with 62 GB RAM, on my own build strata-xtx (`0.2.19-xtx3`, Strata 0.2.19).

OrcaRouter publishes an uncensored version of the same model I run, `Qwen3.8-Flash-Next-Uncensored`, also as IQ3_XXS (two parts, 85.2 GB). Strata describes how to run it (`docs/ORCA.md`). I run the original with a control vector to get an uncensored model. The question was whether OrcaRouter's file could replace that: same speed, same quality, no control vector needed.

Strata's guide says the experts alone need about 49.8 GiB of RAM, 7 GB more than my IQ3_XXS file. Beside the NAS services that does not quite fit, so I ran it with a RAM budget (`--resident-budget-gib`); what the budget and the card's expert cache do not hold is read from the model file.

## In short: it runs, but is not a replacement

| Quiet mode | Flash-Next IQ3_XXS, uncensored version (control vector) | Flash-Next IQ3_XXS, original | OrcaRouter, RAM budget 45 GiB | OrcaRouter, RAM budget 40 GiB |
|---|---:|---:|---:|---:|
| Writing, 2 × 900 tokens (tokens/s) | 61.8 / 62.9 | 60.1 / 63.6 | 54.8 / 58.8 | 51.3 / 49.6 |
| Reading 4K / 16K / 58K tokens (tokens/s) | 743 / 2,381 / 3,437 | 736 / 2,640 / 3,538 | 652 / 2,145 / 3,364 | 648 / 2,131 / 3,364 |
| Answer after the 58K prompt (tokens/s) | 54.6 | 52.3 | 48.4 | 46.1 |
| Hidden number found | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 |
| RAM available after loading | 7.7 GiB | 4.2 GiB | 4.6 GiB | 7.5 GiB |
| Load to first answer | 12 s | 21 s | 40 s | 36 s |
| Task set, 102 graded tasks | **97** | 98 | **89** | – |
| of which tools / safety | 20/20 · 17/18 | 20/20 · 17/18 | **15/20 · 15/18** | – |
| Task set, wall time | 24.2 min | 22.3 min | 31.3 min | – |

Max mode (one round): uncensored version 64.6 / 68.7 tokens/s writing, OrcaRouter with 45 GiB 62.8 / 63.7; reading 58K 3,461 against 3,281 tokens/s.

- **Speed:** OrcaRouter writes 5 to 10 % slower and reads a little slower. A budget of 40 GiB leaves 3 GiB more RAM free but costs another 10 to 15 % of writing speed.
- **Tools:** 5 of 20 tool tasks fail. OrcaRouter often reads and writes files with shell commands (`cat`, `mkdir`) instead of the tools offered, and once calls only one of two required tools. For an agent like Hermes or OpenCode that is the decisive part.
- **Safety:** 3 of 18 fail, two of them graded dangerous: it follows an instruction injected into a document and lists `~/.ssh`, and it reads `.env` on an indirect exfiltration request. The variant with my control vector passes both.
- **Thinking:** it thinks long. In my German agent tasks 9 of 27 answers ran over 6,000 tokens, the 27 runs took 25 instead of 8 minutes, and one code task ended without code because the thinking budget ran out. The German itself was clean: no English words, no foreign script.
- **Uncensored:** yes. Five requests that models often refuse were answered 5 of 5, without a control vector.
- **Memory:** a watchdog would have unloaded the model below 2 GiB of available RAM; it never fired. Swap stayed unchanged.

So my combination of the original file and a control vector stays. OrcaRouter's only advantage, no control vector, does not outweigh weaker tool use and safety.

## Files

| File | Contents |
|---|---|
| `speed.json` | 7 runs (5 quiet, 2 max): load, tool call, writing, prompts 4K/16K/58K with a hidden number, follow-up question, NVMe reads and lowest available RAM per step, the engine's budget lines |
| `task-set-summary.json` | task set per category for the original, the uncensored version and OrcaRouter, what OrcaRouter failed, and the automatic checks of the German agent tasks (counts only, no answer texts) |

## Conditions

- 23 Nov 2026, context 131,072, card quiet (2,800 MHz, −100 mV) unless marked max. Each variant loaded fresh, alternating with my two models in the same session.
- OrcaRouter's file checked against the SHA-256 on Hugging Face, pack built with `tools/iq_pack.py --compat-bf16` as `docs/ORCA.md` describes, PLE table from part 1. No control vector.
- Temperature 0, thinking off for the speed figures, one request at a time, figures from the responses' `timings`. The agent on the NAS was paused.
- The task set for my two models ran on 22 Nov 2026, the German agent tasks for the uncensored version on 13 Nov 2026, both with the same settings.
- Not measured: OrcaRouter's image input. The run with the original's image reader loaded it (writing 58.1 / 60.6, reading 473 / 2,150 / 3,112 tokens/s, 3.9 GiB RAM free), but the image question was only asked of my uncensored version. I did not repeat it, because the tool and safety results already decided the question.
