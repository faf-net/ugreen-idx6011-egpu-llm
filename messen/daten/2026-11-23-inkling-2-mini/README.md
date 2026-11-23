# Inkling 2 Mini on the same card: fast or long, not both

**English** · [Deutsch](README.de.md)

As of 23 Nov 2026. All figures measured on an RX 7900 XTX in the dock of a NAS with 62 GB RAM, NAS services running, card in my quiet mode.

Strata 0.2.19 added a third model with an engine of its own, Thinking Machines' Inkling 2 Mini, in Strata's own packs SQ-20, SQ-15 and SQ-10. I measured it in three runs against what I use, Flash-Next 125B IQ3_XXS with and without control vector, each variant loaded fresh in the same session. Inkling is censored and takes no control vector, so for me it could at most have replaced the original.

## In short

| | 22 Nov, Strata 0.2.19, setup's split | 23 Nov night, 0.2.19, smaller split | 23 Nov, Strata 0.2.20, new split |
|---|---:|---:|---:|
| SQ-20, 128K: decode, tokens/s | **71–73** (max 75) | 28–34 | **9.5–9.7** |
| SQ-20, 128K: reading 16K / 58K, tokens/s | 2,408 / 2,010 | 1,037 / 975 | 658 / 654 |
| SQ-20, 128K: prompt of 105K tokens | HTTP 503 (out of video memory) | HTTP 503 | read, 620 tokens/s |
| SQ-20, 256K: decode | 19–20 | – | 3.2 (run stopped) |
| SQ-15 / SQ-10, 256K | every prompt HTTP 503 | every prompt HTTP 503 or timeout | not run |
| task set, 102 graded tasks | 93 | 94 | not run |
| RAM available after loading | 51 GiB | 50 GiB | 48 GiB |

For comparison, the uncensored Flash-Next in the same sessions: decode 63 to 66 tokens/s, 16K at 2,385 to 2,406 and 105K at 3,401 to 3,421 tokens/s, hidden number found every time, 97 of 102 tasks, 7.8 GiB RAM available.

- **With all experts on the card (0.2.19, setup's split) Inkling writes faster than Flash-Next** and leaves the NAS's RAM almost untouched. But the KV state grows on the card with the prompt, and at about 100K tokens the engine runs out of video memory (`kv grow v: out of memory` in the engine log); the request ends with HTTP 503. The smaller packs SQ-15 and SQ-10 with 256K context failed on every prompt.
- **Leaving room for the KV costs speed.** With a split computed for 21 instead of 24 GiB the same pack writes at 28 to 34 tokens/s and still fails at 105K. Strata 0.2.20 plans the growing KV in (on HIP the KV stays in video memory) and moves experts to RAM: now 105K is read without an error, but the CPU computes the experts in RAM, and decode drops to 9.5 tokens/s, with 256K context to 3.2.
- **Quality and language:** 93 and 94 of 102 tasks (Flash-Next: 97 and 98), weaker on context and tool tasks; in an agent run over 12 files (about 45K tokens) it gave no final answer. On 0.2.19 it missed the hidden number in 6 of the 12 prompts it read. In my German agent tasks 15 of 27 answers used replacement spellings for umlauts (ue for ü) and twice an English word slipped in. German has to be excellent for me, so that alone rules it out.
- **What I did not measure:** the task set and the German tasks on 0.2.20 (at 9.5 tokens/s they would have taken hours, and the speed had already answered the question), the remaining 256K variants on 0.2.20, `--kv-offload on`.

My conclusion for this machine: Inkling can be fast or reach long contexts, but on a 24 GB card next to the NAS services not both, and its German is not good enough. Flash-Next stays. The engine is young; I will measure it again when a release changes it.

## Files

| File | Contents |
|---|---|
| `speed-and-tasks.json` | all three runs: the split per variant, decode, prompt reading with hidden number and error type, available RAM and VRAM after loading; the task set per category |

## Conditions

- Packs checked against Strata's SHA-256 (unchanged between 0.2.19 and 0.2.20). Engine `strata-inkling` 0.1.65 (0.2.19) and 0.1.66 (0.2.20) from the release packages, the same control as the release.
- Temperature 0, thinking off for the speed figures, one request at a time, figures from the responses' `timings`. The agent on the NAS was paused. The first run used a request timeout of one hour, the later ones 25 minutes and stopped a variant after its first read error.
- Answer texts of the German agent tasks are not published; they contain operating data.
