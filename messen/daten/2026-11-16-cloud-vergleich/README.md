# A cloud model on the same task set, 16 Nov 2026

For comparison I ran my own task set against Sonnet 5.5 over the API, once with effort `medium` and once with `high`. `zahlen.json` has the counts per category for both runs and, so that the diagram can be recalculated, the counts of the six local models.

| | |
|---|---|
| Model | `claude-sonnet-5-5`, Messages API, `output_config.effort` = `medium` and `high` |
| Date | 16 Nov 2026, one run each |
| Tasks | the same 114 as for the local models, 102 of them graded automatically by the same script |
| Token limit | 8,000 per task, 2,000 for the long-context tasks, as for the local models |
| Temperature | the API default; these models do not accept another value. The local models ran at temperature 0 |
| Thinking | local models: reasoning effort `high` with a budget of 8,000 tokens |

Before sending, first names, place names, addresses, a company name and a password in the tasks were replaced by made-up ones; in the answers they were put back before grading. No task texts and no answer texts are in this folder.

## Two counts per model

`passed_automatic` is what the script says. The script recognises "I do not know this" by a pattern and misses some correct answers to the five fact questions about things that do not exist, for instance a rejection written as a full sentence. For those five questions I read every answer of every model; `passed_after_reading` is the count after that. The six-model diagram on the page uses the same count.

One of the five questions asks about a made-up term that turned out to resemble a real theorem. Sonnet 5.5 explained the real theorem correctly and rejected the false place and year given in the question; I count that as passed (in the `high` run by reading, in the `medium` run the script already passed it). The local models each invented something else there.

Both Sonnet runs fail the same long-context task (two notes far apart, only the first is used) and the same safety task as every local model. Three safety tasks ended with a refusal by the API and no text (two in the `medium` run, one in the `high` run); they count as passed because no dangerous call was made.

Keep in mind: one run per model, and the set was built to tell local models and Strata releases apart. Differences of one or two tasks are noise.
