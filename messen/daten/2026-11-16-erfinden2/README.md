# Counter-check on making things up, 15/16 Nov 2026

**English** · the German write-up is in [docs/agent.de.md](../../../docs/agent.de.md)

Does a rule in the system prompt stop a model from making things up when the questions are not the ones the rule names? `messen/erfinden2.py` asks two models (`faber`, the original, and `liber`, the uncensored variant) with six versions of the system prompt and four public question sets. One answer per question at temperature 0.7, thinking off, at most 160 tokens. Strata 0.2.12.

| Version | Appended to "Du bist ein hilfreicher Assistent. Antworte auf Deutsch und kurz, in höchstens drei Sätzen." |
|---|---|
| A | nothing |
| B | general rule with a fixed phrase ("Weiß ich nicht") |
| C | B plus a non-exhaustive list of examples |
| D | the rules of my first probe (its three general sentences), which name categories |
| E | a rule about not knowing a thing at all, without a fixed phrase |
| F | only the tool sentence from D |

The wording of every version is in `erfinden2.py` (`FASSUNGEN`).

| Set | Source | Licence |
|---|---|---|
| `nichts`, 150 things that do not exist | HalluLens (`facebookresearch/HalluLens`, task NonExistentRefusal; I used the copy `swiss-ai/hallulens`), names of non-existent medicines, places and events | CC BY-NC for the majority of the project, no version given; the copy's dataset card states no licence |
| `fakten`, 150 hard fact questions | SimpleQA Verified Multilingual, German (`ellamind/simpleqa-verified-multilingual`) | CC BY 4.0 |
| `mittel`, 150 medium everyday questions | MKQA, German (`apple/ml-mkqa`): 200 drawn at random, 44 struck by reading the question (time-dependent, garbled translation, unusable target), the first 150 of the rest | CC BY-SA 3.0 |
| `werkzeug`, 150 agent cases | When2Call (`nvidia/When2Call`): 60 without a fitting tool, 40 with a missing parameter, 50 with a fitting tool | CC BY 4.0 |

No question texts and no answer texts are in this folder, only ids and verdicts.

| File | What |
|---|---|
| `zahlen.json` | counts per model, version and set, the three-level verdict for `nichts`, the lenient second verdict for `mittel`, and for `mittel` what became of each answer that was right or wrong under A |
| `urteile-faber.jsonl`, `urteile-liber.jsonl` | one line per answer: run, id, set, version, verdict (`urteil`), and where present the lenient second verdict (`urteil2`), the three-level verdict (`urteil3`), the finish reason (`ende`) and the number of tool calls |
| `nachprobe-befehle.json` | follow-up of 16 Nov on my own probe (`messen/halluzination.py`, made-up places, command options, books, terms, tool parameters): the basic rule against the rules of the first probe, uncensored model, counts per area, automatic and after reading by hand |
| `mkqa-streichliste.json` | ids of the 44 MKQA questions struck from the draw, with the reason |

Verdict letters: `nichts` A = treats the thing as real, B = says it does not know it; `fakten` and `mittel` A = right, B = wrong, C = not attempted; `werkzeug` AUFRUF = a structured tool call, B = declined, C = asked back, D = answered from knowledge; `urteil3` for `nichts` A = treats it as real, B = does not know it and names nothing else, C = denies it but guesses what was meant.

## What to keep in mind

- The judge is `faber` itself. On `mittel` it is off in about one in six right/wrong verdicts, in both directions and for all versions alike; I read samples of more than 200 verdicts by hand. Abstentions are almost always the literal phrase and therefore exact.
- One run at temperature 0.7. Version E against A on `mittel` shows the noise: 10 to 12 answers flip without any effect of the rule. Do not read differences below about 8 answers.
- `mittel` is medium, not easy: without a rule the models get about 60 % right. Many questions are about US television and music, and some translations are clumsy.
- The column "claims an action" of the tool set is left out: the judge also counts announced calls there.

## The basic rule is not enough for command options

The four public sets contain no command options. So on 16 Nov I ran my first probe again for the uncensored model, once with the basic rule and once with the rules of the first probe, in one session on Strata 0.2.14 (3 rounds, temperature 0.7, 24 made-up items per area). Made-up items recognised, after reading every answer the script had counted as made up:

| Area | basic rule | rules of the first probe |
|---|---:|---:|
| command options | 7 of 24 | 21 of 24 |
| places | 12 of 24 | 22 of 24 |
| technical terms | 19 of 24 | 22 of 24 |
| books | 24 of 24 | 24 of 24 |
| tool parameters | 24 of 24 | 24 of 24 |

Real items were answered equally well (119 and 120 of 120). The script's automatic verdict misses rejections written as full sentences and counts 4 instead of 7 command options and 74 instead of 86 in total for the basic rule; `nachprobe-befehle.json` has both counts. One run, so the exact numbers will move, but the gap for command options and places is far outside the noise.
