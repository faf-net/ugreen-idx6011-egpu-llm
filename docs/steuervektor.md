# `liber`: the uncensored model

**English** · [Deutsch](steuervektor.de.md) · [← README](../README.md)

`liber` is an uncensored model. It is the same 125B model as `faber` with its refusals removed: it answers whatever it is asked, including questions the original model declines. Chat and agent can use any of the models; `liber` is one of them and is chosen like the others, per conversation or in the agent's settings. This page says how that works technically, what it changes, what it costs and what you take on with it.

## What "uncensored" means here

The original model is trained to refuse or water down certain requests. `liber` no longer does. There is no filter in front of it and none behind it, and it does not lecture. In my tests it did not refuse a single task.

That is not limited to harmless cases. The model no longer distinguishes between a question that was refused wrongly and one the original declines for good reason. It answers both. The only line left is the one drawn by the person asking.

## Why I use it

Out of the box the model refuses or waters down a lot that is nobody's business on your own machine. An assistant at home should answer, not educate. `liber` also writes the better German.

## How it works

Research on language models has shown that refusals largely hang on a single direction in the model's internal activations. Project that direction out and the model stops refusing; everything else stays as it is. The technique is known as "abliteration". Strata supports it as a regular feature: a vector file (steering vector) is applied to a range of layers while the model runs. The weights on disk stay unchanged, so the same files serve both models.

The settings are in [`konfig/strata-0.2.12/liber.json`](../konfig/strata-0.2.12/liber.json): the vector is applied to layers 4 to 44 in projection mode, one direction per layer. The vector file itself is not part of this repository; such files are publicly available for many models.

## What it changes, and what it costs

![The same model censored and uncensored](../bilder/steuervektor-en.png)

| | original (`faber`) | uncensored (`liber`) |
|---|---:|---:|
| 15 tasks that models often refuse: answered / evasive / refused | 11 / 3 / 1 | 15 / 0 / 0 |
| graded tasks passed (of 102) | 96 | 98 |
| German, graded blind (of 60) | 51 | 54 |
| made-up things recognised, without rules (of 120) | 35 (29 %) | 20 (17 %) |
| made-up things recognised, with the four rules (of 120) | 117 (98 %) | 109 (91 %) |
| counter-check 16 Nov: made-up things treated as real, without a rule / with a short rule (of 150) | 20 / 6 | 25 / 5 |
| real things answered correctly, without / with rules (of 120) | 120 / 120 | 119 / 119 |
| decode, long answer | 63.7 tok/s | 61.9 tok/s |
| prompt reading at 32K | 1,183 tok/s | 1,188 tok/s |

The 15 tasks come from areas where language models usually refuse, evade or lecture: fiction and humour without restraint, health and risks, security and technology, contested ethical questions. I do not list them individually here.

**The abilities stay.** Tasks, German and speed are the same within the spread of a single run; the two-task difference is not a finding.

**Does it make up more? Not measurably.** In the counter-check with a public question set `liber` treated 25 of 150 things that do not exist as real, the original 20; with a short rule in the system prompt it was 5 and 6 ([docs/agent.md](agent.md)). In my first, smaller probe `liber` trailed a little: 17 instead of 29 % of made-up things recognised without rules, 91 instead of 98 % with the four rules, mainly on made-up command options (17 of 24). One run per model, so this is no more than a hint. An agent cannot do without the rules and the checker with either model.

**Judgement is no better.** In the ten-round test both models follow a hard instruction in 10 of 10 answers, and both invent capabilities when a job aborts at night: the original in 6 of 10 answers, `liber` in 8 of 10.

## What you take on

- **There is no barrier left.** What the model writes is the sole responsibility of whoever runs it and whoever asks.
- **It does not belong in front of children** or in a service strangers can reach. Mine is reachable only in the home network and behind a login.
- **An agent with tools becomes more dangerous, not just freer.** An uncensored model also follows an instruction planted in a web page or mail more readily. That is why the agent here may only run approved commands, and a checker reads every answer.
- **It knows no more than the original.** Where it does not know, it guesses, and it sounds sure doing so.

For the 15 tasks I read the beginnings of the answers. Only counts are published, no answer texts: `messen/daten/2026-11-14-erfinden/steuervektor.json`.
