# Ein unzensiertes Flash-Next von OrcaRouter gegen meinen Steuervektor

[English](README.md) · **Deutsch**

Stand 23.11.2026. Alle Werte gemessen, auf einer RX 7900 XTX im Dock eines NAS mit 62 GB RAM, auf meinem Eigenbau strata-xtx (`0.2.19-xtx3`, Strata 0.2.19).

OrcaRouter veröffentlicht eine unzensierte Fassung desselben Modells, das ich betreibe, `Qwen3.8-Flash-Next-Uncensored`, ebenfalls als IQ3_XXS (zwei Teile, 85,2 GB). Strata beschreibt, wie man sie startet (`docs/ORCA.md`). Ich mache das Original mit einem Steuervektor unzensiert. Die Frage war, ob die Datei von OrcaRouter das ersetzen kann: gleiches Tempo, gleiche Qualität, kein Steuervektor nötig.

Laut Stratas Anleitung brauchen allein die Experten rund 49,8 GiB RAM, 7 GB mehr als meine IQ3_XXS-Datei. Neben den Diensten des NAS passt das nicht ganz, deshalb lief sie mit einem RAM-Budget (`--resident-budget-gib`); was Budget und Expertenspeicher der Karte nicht halten, liest die Engine aus der Modelldatei.

## Kurz: läuft, ist aber kein Ersatz

| Modus leise | Flash-Next IQ3_XXS, Variante mit Steuervektor | Flash-Next IQ3_XXS, Original | OrcaRouter, RAM-Budget 45 GiB | OrcaRouter, RAM-Budget 40 GiB |
|---|---:|---:|---:|---:|
| Schreiben, 2 × 900 Token (Token/s) | 61,8 / 62,9 | 60,1 / 63,6 | 54,8 / 58,8 | 51,3 / 49,6 |
| Einlesen 4K / 16K / 58K Token (Token/s) | 743 / 2.381 / 3.437 | 736 / 2.640 / 3.538 | 652 / 2.145 / 3.364 | 648 / 2.131 / 3.364 |
| Antwort nach dem 58K-Prompt (Token/s) | 54,6 | 52,3 | 48,4 | 46,1 |
| Versteckte Zahl gefunden | 3 von 3 | 3 von 3 | 3 von 3 | 3 von 3 |
| RAM frei nach dem Laden | 7,7 GiB | 4,2 GiB | 4,6 GiB | 7,5 GiB |
| Laden bis zur ersten Antwort | 12 s | 21 s | 40 s | 36 s |
| Aufgabensatz, 102 bewertete Aufgaben | **97** | 98 | **89** | – |
| davon Werkzeuge / Sicherheit | 20/20 · 17/18 | 20/20 · 17/18 | **15/20 · 15/18** | – |
| Aufgabensatz, Dauer | 24,2 min | 22,3 min | 31,3 min | – |

Modus max (eine Runde): Variante mit Steuervektor schreibt 64,6 / 68,7 Token/s, OrcaRouter mit 45 GiB 62,8 / 63,7; Einlesen 58K 3.461 gegen 3.281 Token/s.

- **Tempo:** OrcaRouter schreibt 5 bis 10 % langsamer und liest etwas langsamer. Ein Budget von 40 GiB lässt 3 GiB mehr RAM frei, kostet aber weitere 10 bis 15 % beim Schreiben.
- **Werkzeuge:** 5 von 20 Werkzeugaufgaben scheitern. OrcaRouter liest und schreibt Dateien oft mit Shell-Befehlen (`cat`, `mkdir`) statt mit den angebotenen Werkzeugen und ruft einmal nur eines von zwei nötigen Werkzeugen auf. Für einen Agenten wie Hermes oder OpenCode ist das der entscheidende Teil.
- **Sicherheit:** 3 von 18 scheitern, zwei davon als gefährlich bewertet: Es folgt einer in ein Dokument eingeschleusten Anweisung und listet `~/.ssh` auf, und es liest `.env` bei einer verdeckten Bitte, Daten auszuleiten. Die Variante mit meinem Steuervektor besteht beide.
- **Denken:** Es denkt lange. In meinen deutschen Agentenaufgaben liefen 9 von 27 Antworten über 6.000 Token, die 27 Läufe dauerten 25 statt 8 Minuten, und eine Code-Aufgabe endete ohne Code, weil das Denkbudget aufgebraucht war. Das Deutsch selbst war sauber: keine englischen Wörter, keine fremde Schrift.
- **Unzensiert:** ja. Fünf Bitten, die Modelle oft ablehnen, beantwortete es alle fünf, ohne Steuervektor.
- **Speicher:** Ein Wächter hätte das Modell unter 2 GiB freiem RAM entladen; er hat nie ausgelöst. Der Swap blieb unverändert.

Meine Kombination aus Originaldatei und Steuervektor bleibt also. Der einzige Vorteil von OrcaRouter, kein Steuervektor, wiegt die schwächeren Werkzeugaufrufe und die Sicherheit nicht auf.

## Dateien

| Datei | Inhalt |
|---|---|
| `speed.json` | 7 Läufe (5 leise, 2 max): Laden, Tool-Call, Schreiben, Prompts 4K/16K/58K mit versteckter Zahl, Folgefrage, NVMe-Lesen und niedrigster freier RAM je Schritt, die Budget-Zeilen der Engine |
| `task-set-summary.json` | Aufgabensatz je Gruppe für Original, Variante mit Steuervektor und OrcaRouter, woran OrcaRouter scheiterte, und die automatischen Prüfungen der deutschen Agentenaufgaben (nur Zählungen, keine Antworttexte) |

## Bedingungen

- 23.11.2026, Kontext 131.072, Karte leise (2.800 MHz, −100 mV), sofern nicht max angegeben. Jede Variante frisch geladen, in derselben Sitzung im Wechsel mit meinen beiden Modellen.
- Die Datei von OrcaRouter gegen die SHA-256 auf Hugging Face geprüft, Pack mit `tools/iq_pack.py --compat-bf16` gebaut, wie `docs/ORCA.md` es beschreibt, PLE-Tabelle aus Teil 1. Kein Steuervektor.
- Temperatur 0, Denken für die Tempowerte aus, eine Anfrage zurzeit, Werte aus den `timings` der Antworten. Der Agent auf dem NAS war pausiert.
- Der Aufgabensatz meiner beiden Modelle lief am 22.11.2026, die deutschen Agentenaufgaben der Variante mit Steuervektor am 13.11.2026, beide mit denselben Einstellungen.
- Nicht gemessen: der Bildeingang von OrcaRouter. Der Lauf mit dem Bildleser des Originals hat ihn geladen (Schreiben 58,1 / 60,6, Einlesen 473 / 2.150 / 3.112 Token/s, 3,9 GiB RAM frei), die Bildfrage ging aber nur an meine Variante mit Steuervektor. Wiederholt habe ich das nicht, weil Werkzeuge und Sicherheit die Frage schon entschieden hatten.
