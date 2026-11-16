# Re-measured on Strata 0.2.14, 16 Nov 2026

The NAS switched to Strata 0.2.14 on the morning of 16 Nov (engine and control 0.1.60, run configs unchanged, `konfig/strata-0.2.14/`). Right after the switch I repeated the measurements of 15 Nov that the README and the page quote, with the same scripts. The UPS feeds only the NAS and the dock; its idle reading before the run was 47 W. NAS services were running, only my agent was paused.

| File | Script | What |
|---|---|---|
| `strom-faber.json`, `strom-velox.json`, `strom-liber.json` | `messen/betrieb.py strom` | power at the UPS and at the card per phase, decode and prompt speed, Wh per 1,000 tokens |
| `kaltstart-faber.json` | `messen/betrieb.py kaltstart` | empty card to first token, five runs |
| `wartezeit.json` | `messen/wartezeit.py` | wait for the first word by text length, and for a follow-up question |
| `zwei.json` | `messen/zwei.py` | two people at once on one model, and alternating between two models |
| `nebenlast.json` | `messen/nebenlast.py`, `messen/transkodieren.sh` | 16 Nov, 13:30-13:43: transcoding and a 17.7 GB HTTP download (measured by the client, a workstation with a 5 Gbit/s port) without a model and while `faber` writes; every request with start and end. Download 591 / 586 MB/s, transcoding 290 / 241-244 frames/s, decode 66-68 alone and 66.6 / 67.6 in the two requests that overlap the side load |
| `qualitaet.json` | task set of the night before | the 125B model on 0.2.14 (98 of 102) next to UGREEN's model, which was not run again; the file says which column was measured on which version |

## Against 15 Nov on Strata 0.2.12

| | 0.2.14 | 0.2.12 |
|---|---:|---:|
| `faber` decode tok/s | 65.9 | 66.3 |
| `faber` prompt reading tok/s | 1,339 | 1,159 |
| NAS and dock while writing | 336 W | 355 W |
| Wh per 1,000 written tokens | 1.4 | 1.5 |
| cold start, median | 19.5 s | 19.6 s |
| 300-page book, first word | 160 s | 183 s |
| two people at once, wait (median) | 9.5 s and 9.6 s | 8.1 s and 10.5 s |

Writing is as fast as before, reading 16 % faster. `velox` writes at 71.9 and `liber` at 63.1 tok/s (70.8 and 62.9 before).

Notes on reading the files:

- The UPS reports a new value only every 30 s. For `liber` the reading phase shows 311 W at the UPS with 228 W at the card, and its idle phase 53 W; I take both for sampling and quote neither. The idle value I quote is the one from `faber` (49 W).
- In `zwei.json` the median for alternating between two models (19.1 s) leaves out the first question, which hits the model that is already loaded.
- The German grade in `qualitaet.json` (47 of 60) is from the run on 0.2.12 and was not repeated.
