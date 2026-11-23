# Inkling 2 Mini auf derselben Karte: schnell oder lang, nicht beides

[English](README.md) · **Deutsch**

Stand 23.11.2026. Alle Werte gemessen, auf einer RX 7900 XTX im Dock eines NAS mit 62 GB RAM, NAS-Dienste laufen, Karte im Modus leise.

Strata 0.2.19 brachte ein drittes Modell mit eigener Engine, Inkling 2 Mini von Thinking Machines, in Stratas eigenen Packs SQ-20, SQ-15 und SQ-10. Ich habe es in drei Läufen gegen das gemessen, was ich betreibe, Flash-Next 125B IQ3_XXS mit und ohne Steuervektor, jede Variante frisch geladen in derselben Sitzung. Inkling ist zensiert und nimmt keinen Steuervektor an, für mich hätte es also höchstens das Original ersetzen können.

## Kurz

| | 22.11., Strata 0.2.19, Aufteilung des Setups | 23.11. nachts, 0.2.19, kleinere Aufteilung | 23.11., Strata 0.2.20, neue Aufteilung |
|---|---:|---:|---:|
| SQ-20, 128K: Schreiben, Token/s | **71–73** (max 75) | 28–34 | **9,5–9,7** |
| SQ-20, 128K: Einlesen 16K / 58K, Token/s | 2.408 / 2.010 | 1.037 / 975 | 658 / 654 |
| SQ-20, 128K: Prompt mit 105K Token | HTTP 503 (Grafikspeicher voll) | HTTP 503 | gelesen, 620 Token/s |
| SQ-20, 256K: Schreiben | 19–20 | – | 3,2 (Lauf abgebrochen) |
| SQ-15 / SQ-10, 256K | jeder Prompt HTTP 503 | jeder Prompt HTTP 503 oder Zeitüberschreitung | nicht gelaufen |
| Aufgabensatz, 102 bewertete Aufgaben | 93 | 94 | nicht gelaufen |
| RAM frei nach dem Laden | 51 GiB | 50 GiB | 48 GiB |

Zum Vergleich das unzensierte Flash-Next in denselben Sitzungen: Schreiben 63 bis 66 Token/s, 16K mit 2.385 bis 2.406 und 105K mit 3.401 bis 3.421 Token/s, versteckte Zahl jedes Mal gefunden, 97 von 102 Aufgaben, 7,8 GiB RAM frei.

- **Mit allen Experten auf der Karte (0.2.19, Aufteilung des Setups) schreibt Inkling schneller als Flash-Next** und lässt den RAM des NAS fast unberührt. Der Gesprächsspeicher wächst aber auf der Karte mit dem Prompt, und bei rund 100K Token geht der Engine der Grafikspeicher aus (`kv grow v: out of memory` im Engine-Log); die Anfrage endet mit HTTP 503. Die kleineren Packs SQ-15 und SQ-10 mit 256K Kontext scheiterten an jedem Prompt.
- **Platz für den Gesprächsspeicher kostet Tempo.** Mit einer Aufteilung für 21 statt 24 GiB schreibt dasselbe Pack mit 28 bis 34 Token/s und scheitert bei 105K trotzdem. Strata 0.2.20 plant das Wachsen des Gesprächsspeichers ein (bei HIP bleibt er im Grafikspeicher) und verlegt Experten in den RAM: Jetzt wird 105K ohne Fehler gelesen, aber der Prozessor rechnet die Experten im RAM, und das Schreiben fällt auf 9,5 Token/s, mit 256K Kontext auf 3,2.
- **Qualität und Sprache:** 93 und 94 von 102 Aufgaben (Flash-Next: 97 und 98), schwächer bei Kontext- und Werkzeugaufgaben; in einem Agentenlauf über 12 Dateien (rund 45K Token) kam keine Schlussantwort. Auf 0.2.19 fand es die versteckte Zahl in 6 der 12 gelesenen Prompts nicht. In meinen deutschen Agentenaufgaben standen in 15 von 27 Antworten Ersatzschreibungen für Umlaute (ue statt ü), zweimal rutschte ein englisches Wort hinein. Deutsch muss für mich hervorragend sein, das allein schließt es aus.
- **Nicht gemessen:** Aufgabensatz und deutsche Aufgaben auf 0.2.20 (bei 9,5 Token/s hätte das Stunden gedauert, und das Tempo hatte die Frage schon beantwortet), die übrigen 256K-Varianten auf 0.2.20, `--kv-offload on`.

Mein Schluss für diese Maschine: Inkling kann schnell sein oder lange Kontexte schaffen, auf einer 24-GB-Karte neben den NAS-Diensten aber nicht beides, und sein Deutsch reicht nicht. Flash-Next bleibt. Die Engine ist jung; ich messe wieder, wenn ein Release sie ändert.

## Dateien

| Datei | Inhalt |
|---|---|
| `speed-and-tasks.json` | alle drei Läufe: Aufteilung je Variante, Schreiben, Einlesen mit versteckter Zahl und Fehlerart, freier RAM und VRAM nach dem Laden; der Aufgabensatz je Gruppe |

## Bedingungen

- Packs gegen Stratas SHA-256 geprüft (zwischen 0.2.19 und 0.2.20 unverändert). Engine `strata-inkling` 0.1.65 (0.2.19) und 0.1.66 (0.2.20) aus den Release-Paketen, dasselbe Control wie das Release.
- Temperatur 0, Denken für die Tempowerte aus, eine Anfrage zurzeit, Werte aus den `timings` der Antworten. Der Agent auf dem NAS war pausiert. Der erste Lauf hatte eine Zeitgrenze von einer Stunde je Anfrage, die späteren 25 Minuten und brachen eine Variante nach dem ersten Fehler beim Einlesen ab.
- Antworttexte der deutschen Agentenaufgaben werden nicht veröffentlicht; sie enthalten Betriebsdaten.
