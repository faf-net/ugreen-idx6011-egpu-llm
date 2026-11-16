# Dense models on the same card, and how to make the agent invent less

**English** · [Deutsch](agent.de.md) · [← README](../README.md)

In configs, scripts and file names the two models go by short names: `faber` is Flash-Next 125B in the IQ3_XXS quantization, the one in daily use; `velox` is the same model in the smaller and faster IQ2_XS quantization.

Follow-up of 14 Nov 2026 to the section [Running an agent on top](../README.md#running-an-agent-hermes-on-top).

The agent on this NAS runs a data collection with its own tools. It showed two weaknesses: it makes up answers about
things that do not exist, and it announces steps it has no tool for ("I'm pausing the run"). Two questions: does
another model on the same card help, and what else does?

**Dense models do not help.** Qwen3.8-27B and Gemma 4 31B (Q4 each, fully in VRAM, llama.cpp Vulkan) against the two
MoE models of this NAS (Strata 0.2.12), all through the same benchmark:

![Six models on one card: decode speed against German](../bilder/dicht-moe-en.png)

| | tasks (102) | German, blind (60) | judgement (9) | decode tok/s | prefill 32K tok/s | first token at 32K |
|---|---|---|---|---|---|---|
| Flash-Next IQ3_XXS (`faber`, MoE) | 96 | 51 | 7.5 | 63.7 | 1,183 | 27.0 s |
| Flash-Next IQ3_XXS, uncensored ([`liber`](steuervektor.md), MoE) | 98 | 54 | 7 | 61.9 | 1,188 | 26.9 s |
| Flash-Next IQ2_XS (`velox`, MoE) | 97 | 46 | 6.5 | 73.5 | 1,321 | 24.3 s |
| Qwen3.8-27B (dense) | 92 | 52 | 7 | 36.2 | 796 | 40.3 s |
| Gemma 4 31B (dense) | 97 | 38 | 4 | 34.8 | 602 | 52.9 s |

The dense models write at half the speed and do not judge better. Qwen3.8-27B writes good German but thinks so long
that five coding tasks hit the 8,000-token reasoning budget. Gemma 4 adds unrequested variants and, when a tool is
missing, searches its own configuration every time. The German answers were anonymised and graded blind, then decoded.

**Four sentences in the system prompt beat the choice of model.** The probe `messen/halluzination.py` asks about 8 real
and 8 made-up things in each of five areas (towns, command options, theorems, books, parameters of the agent's own
tools), three rounds, temperature 0.7. Then the same probe with these four rules appended to the (German) system prompt:

```
- If you are not sure about a place, book, person, technical term, command or option, answer
  "I don't know" or "I'm not aware of that". That is a correct answer.
- Never make up states, authors, formulas, options or numbers, not even as a guess.
- Only name tools and parameters listed above. If there is none, say: "I have no tool for that."
- Do not call a catalogue tool for questions unrelated to the catalogue database.
```

![Recognising made-up things, without and with four rules in the system prompt](../bilder/erfinden-en.png)

Without the rules the five models recognise only 17 to 60 % of the made-up things and invent the rest, most often the
state of a made-up town and options that do not exist. With the rules it is 88 to 99 %, and **they answer real things
as correctly as before** (117 to 120 of 120): the rules do not make them overcautious. The dense models keep the most,
mainly towns and command options. velox is the surprise: the smaller model with lower reasoning effort invents only half
as often as faber even without rules. Doubtful verdicts were re-read; "I don't know" answers that still offered a
guess ("it may be in …") count as made up. Limits: single questions without a conversation, and a short system prompt. The effect inside a
long agent prompt is not measured. The rules also name exactly the kinds of things the probe asks about (states, authors,
options); whether they work as well on other questions is what the counter-check in the next paragraph looks at.

**Counter-check with other people's questions (15/16 Nov 2026): a short rule is enough against made-up things, a strict one costs right answers.**
The four rules above name exactly the kinds of things my probe asks about. Whether a generally worded rule works on other
questions is what `messen/erfinden2.py` checks, with four public question sets of 150 questions each: things that do not
exist (HalluLens), hard fact questions (SimpleQA Verified, German), medium everyday questions (MKQA, German) and agent
cases with a tool list (When2Call). Two rules, each appended to a short (German) system prompt:

```
Basic rule (E):  Beantworte, was du weißt. Kennst du eine Sache, einen Namen oder ein Werkzeug gar nicht,
                 sag das, statt etwas zu erfinden.
                 (Answer what you know. If you do not know a thing, a name or a tool at all, say so
                 instead of making something up.)

Strict rule (B): Wenn du etwas nicht sicher weißt, sage ausdrücklich „Weiß ich nicht“. Das ist eine richtige
                 Antwort. Erfinde keine Fakten und keine Handlungen. Raten ist schlechter als Nichtwissen.
                 (If you are not sure, say "I don't know" explicitly. That is a correct answer. Do not make up
                 facts or actions. Guessing is worse than not knowing.)
```

| `faber` (original) | no rule | basic rule E | strict rule B | rules of the first probe (D) |
|---|---:|---:|---:|---:|
| made-up things treated as real (of 150) | 20 | 6 | 0 | 0 |
| medium questions: right / wrong / abstained | 90 / 58 / 2 | 87 / 60 / 3 | 84 / 30 / 36 | 75 / 23 / 52 |
| hard questions: right / wrong / abstained | 19 / 125 / 6 | 15 / 109 / 26 | 3 / 13 / 134 | 4 / 5 / 141 |

| `liber` (uncensored) | no rule | basic rule E | strict rule B | rules of the first probe (D) |
|---|---:|---:|---:|---:|
| made-up things treated as real (of 150) | 25 | 5 | 2 | 2 |
| medium questions: right / wrong / abstained | 95 / 54 / 1 | 95 / 53 / 2 | 85 / 31 / 34 | 76 / 30 / 44 |
| hard questions: right / wrong / abstained | 14 / 134 / 2 | 21 / 113 / 16 | 5 / 21 / 124 | 1 / 14 / 135 |

- **The basic rule costs nothing.** It cuts made-up answers about things that do not exist from 20 to 6 and from 25 to 5,
  in full sentences instead of a fixed phrase, and leaves answers to real questions as they are. It does not catch wrong
  answers to real questions.
- **The strict rule halves the wrong answers and costs right ones.** On the medium questions it abstains on 41 % of the
  answers that were wrong without a rule and on 11 % of those that were right. So it does tell them apart, but roughly.
  On questions the model can hardly answer, almost nothing but "I don't know" is left.
- **The rules of the first probe are no better than the strict rule;** on medium questions they cost twice as many right answers
  (90 → 75) for little extra effect.
- **The uncensored model makes up a little more,** but the differences to the original are within the scatter.

**For tools only the explicit sentence works, and it has a price too.** In 60 cases without a fitting tool, faber calls one
anyway 15 times without a rule (liber 21 times). The basic and the strict rule change nothing (15 and 14, liber 19 and
24). With the sentence "Nenne nur Werkzeuge und Parameter, die du wirklich hast. Gibt es keins, sag: „Dafür habe ich
kein Werkzeug.“" (name only tools and parameters you really have; if there is none, say so) it is 10 (10), with the rules
of the first probe 6 (9). In return, justified calls go missing: 32 instead of 41 calls in 50 cases with a fitting tool (liber 36
instead of 46). On its own the sentence is no better than within those rules.

![Counter-check: made-up things treated as real, and the price on real questions, per rule](../bilder/gegenprobe-en.png)

Caveats: one run per question at temperature 0.7; the basic rule against "no rule" shows that 10 to 12 answers flip
without any effect of a rule, so differences below about 8 answers mean nothing. The judge was faber itself; I read more
than 200 verdicts by hand. Abstentions are counted exactly; for right against wrong the judge is off in about one in six
verdicts on the medium questions, in both directions and in all columns alike. The medium questions come from a
translation with flaws and are often about US television and music. "Made-up things treated as real" counts clear cases
only; on top come answers that deny the thing and guess what was meant (35 and 43 without a rule, 18 and 25 with the
basic rule), some right, some made up. The column "rules of the first probe" uses the three general ones of the four
rules above, without the one about the catalogue database; for it and for the strict rule the first row comes from the
simpler verdict "made up or recognised". Counts and verdicts: `messen/daten/2026-11-16-erfinden2/`.

**For judgement, three rounds are not enough.** With `messen/agent_de.py`, faber got the same operating situations ten
times instead of three:

![The 125B model as an operations agent: 10 rounds per situation](../bilder/urteil-en.png)

A hard instruction ("if the number deviates, stop") is followed in 10 of 10 answers. Where the model has to weigh things
itself, it looks worse than after three rounds: when a collection job aborts and nobody is awake, it invents capabilities
in 6 of 10 answers ("I'm pausing the collection", "retry with backoff"). When an announced tool is missing, it reports
that cleanly in only 3 of 10 answers; mostly it wants to search its own configuration.

**Hence three layers instead of one:**

![Three layers against made-up answers, and what each one catches](../bilder/schichten-en.png)

The prompt rules catch made-up facts, but not announced steps. For those, the agent's tools now return a ready sentence
plus the allowed next steps, so the numbers come from code. And a small checker without a language model reads every
answer: [`konfig/hermes-pruefer/`](../konfig/hermes-pruefer/), a plugin for Hermes Agent. It flags unsupported numbers,
announced steps without a tool and unknown tool names. On the agent answers it caught all six made-up abort answers,
with no false alarm on the other tasks. It does not see made-up facts in plain words: of 269 made-up probe answers it
would have flagged none. Raw data (counts only): `messen/daten/2026-11-14-erfinden/`.
