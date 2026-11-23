# Hy4-Flash (220B) auf Strata 0.2.20: die RAM-Falle ist behoben

[English](README.md) · **Deutsch**

Stand 23.11.2026. Nachtest für [Strata-Issue #6556](https://github.com/Niko1221/Strata/issues/6556) auf derselben Maschine wie in [`../2026-11-22-hy4-flash/`](../2026-11-22-hy4-flash/README.de.md): RX 7900 XTX im Dock eines NAS mit 62,3 GiB RAM, die Dienste des NAS laufen, nur mein Agent pausiert.

Auf 0.2.18 verwarf die Hy4-Engine die RAM-Aufteilung, die Stratas Setup schreibt, und rechnete mit dem gesamten RAM: Der Speicher lief voll, der Kernel lagerte aus, und Hy4-Flash schrieb mit 0,3 bis 0,6 Token/s. Auf 0.2.20 schreibt das Setup für diese Maschine eine andere Aufteilung (16,71 GB Experten auf der Karte, 39,33 GB im RAM, auf 0.2.18 waren es 9,35 / 46,69), und die Engine folgt ihr. Ich habe genau diese Angaben gefahren, ohne `HY4_RAM_BUDGET_GB`, und zum Vergleich den alten Umweg. Jede Variante frisch geladen, im Wechsel mit Flash-Next, zuerst in meiner leisen Leistungseinstellung, dann bei voller Leistung.

| Leise | Flash-Next, mit Steuervektor | Flash-Next, Original | Hy4-Flash, Setup-Aufteilung 0.2.20 | Hy4-Flash, `HY4_RAM_BUDGET_GB=36` |
|---|---:|---:|---:|---:|
| Schreiben, 2 × 900 Token, Token/s | 64,8 / 65,5 | 63,7 / 60,3 | 12,7 / 13,0 | 14,7 / 17,3 |
| kurzen Prompt einlesen, Token/s | 681 | 719 | 409 | 343 |
| mittleren Prompt einlesen, Token/s | 2.403 | 2.558 | 512 | 371 |
| langen Prompt einlesen, Token/s | 3.425 | 3.496 | 641 | 384 |
| von der NVMe gelesen je Antwort mit 900 Token | 0,1 GB | 0,1 GB | 2,3–2,4 GB | 87–99 GB |
| von der NVMe gelesen für den langen Prompt | 0,0 GB | 0,0 GB | 9,4 GB | 84 GB |
| verfügbarer RAM, Tiefstwert im Lauf | 7,3 GiB | 3,8 GiB | 9,6 GiB | 13,0 GiB |
| Auslagerung | unverändert | unverändert | unverändert | unverändert |
| versteckte Zahl gefunden, Tool-Call | ja, ja | ja, ja | ja, ja | ja, ja |

Die Prompts sind für alle Modelle derselbe Text; Flash-Next zählt 4.125 / 16.088 / 58.021 Token, Hy4s Tokenizer 5.346 / 20.866 / 75.268. Bei voller Leistung lieferte Hy4 mit der Setup-Aufteilung dieselben Werte (12,8 / 13,4 Token/s, 641 Token/s beim langen Prompt), die Variante mit Steuervektor ebenso (65,5 / 65,8). Nach den Hy4-Läufen hat die Variante mit Steuervektor geantwortet, ein Werkzeug aufgerufen, ein Bild gelesen und ihren Vektor geladen.

- **Die Falle ist weg.** Im Engine-Log steht kein `not used by this runner yet` mehr, das RAM-Budget ist 39,3 GB wie vom Setup geschrieben, und 719 der kältesten Experten (1,6 GB) bleiben auf der SSD. Der verfügbare RAM fiel nie unter 9,5 GiB, der Speicherdruck (`/proc/pressure/memory`, some avg300) blieb bei 1,0 bis 1,3 % statt rund 45 %.
- **Die Setup-Aufteilung ist die bessere.** Sie legt mehr Experten auf die Karte, liest lange Prompts deshalb 1,7-mal so schnell wie der alte Umweg und liest nur ein Zehntel von der NVMe. Sie schreibt etwas langsamer.
- **Auch der alte Umweg ist schneller geworden:** 14,7 bis 17,3 Token/s auf 0.2.20 gegen 7,0 bis 7,5 auf 0.2.18, bei gleichen Antworten mit 900 Token.
- **Für den Alltag ändert das nichts.** Hy4-Flash schreibt weiter mit einem Fünftel des Tempos von Flash-Next, ist zensiert und nimmt keinen Steuervektor an. Flash-Next bleibt.

`speed-and-memory.json`: jeder Lauf mit seinen Engine-Logzeilen (Pfade entfernt, Antworttexte weggelassen).
