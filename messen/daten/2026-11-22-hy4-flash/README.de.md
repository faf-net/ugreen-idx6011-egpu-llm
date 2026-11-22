# Ein größeres Modell: Tencent Hy4-Flash (220B) auf derselben Karte

[English](README.md) · **Deutsch**

Stand 22.11.2026. Alle Zahlen sind gemessen, auf einer RX 7900 XTX im Dock eines NAS mit 62 GB RAM, Karte im Modus leise.

Strata 0.2.18 bringt mit Hy4-Flash ein zweites Modell und dafür eine eigene Engine (`strata-hy4`). Hy4-Flash hat 220 Milliarden Parameter, davon 12 Milliarden aktiv, also fast doppelt so viele wie Flash-Next. Strata liefert es nur in eigenen Quants. Ich habe das kleinste genommen (SQ-64, 62,0 GB, dazu die Engram-Datei mit 67,6 GB und der Bildteil). Verglichen habe ich es mit meinem Betrieb, Flash-Next 125B IQ3_XXS, im Original und in der Variante mit Steuervektor.

Hy4-Flash ist ein zensiertes Modell, und die Hy4-Engine nimmt keinen Steuervektor an. Für meinen Betrieb kam es deshalb nur als Ersatz für das Original in Frage, nicht für die unzensierte Fassung.

## Ergebnis in Kürze: Es läuft, aber achtmal langsamer

| Modus leise | Flash-Next IQ3_XXS, unzensiert | Flash-Next IQ3_XXS, Original | Hy4-Flash SQ-64, RAM-Budget 36 GB |
|---|---:|---:|---:|
| Schreiben, 2 × 900 Token (Token/s) | 60,0 / 61,9 | 64,4 / 57,9 | 7,0 / 7,5 |
| Einlesen, kurzer Prompt (Token/s) | 669 (4.126 Token) | 757 (4.126) | 433 (5.346) |
| Einlesen, mittlerer Prompt (Token/s) | 2.392 (16.088) | 2.308 (16.092) | 438 (20.868) |
| Einlesen, langer Prompt (Token/s) | 3.094 (58.023) | 3.161 (58.024) | 414 (75.266) |
| Antwort nach dem langen Prompt (Token/s) | 57,5 | 51,3 | 6,8 |
| versteckte Zahl gefunden | 4 von 4 | 4 von 4 | 3 von 3 |
| Tool-Call | ja | ja | ja |
| RAM verfügbar nach dem Laden | 7,7 GiB | 4,1 GiB | 15,7 GiB, im Lauf mindestens 7,3 |
| von der NVMe gelesen je Antwort mit 900 Token | 0,1–0,2 GB | 0,1–0,2 GB | 162–165 GB |
| Laden bis zur ersten Antwort | 20 s | 20 s | 86 s |

Die drei Prompts enthalten jeweils denselben Text. Hy4s Tokenizer braucht dafür rund 30 % mehr Token als der von Qwen, deshalb stehen die Tokenzahlen dabei. Ein Prompt mit 105K Qwen-Token passt bei Hy4 nicht mehr in den Kontext von 128K.

- **Schreiben ist der Engpass.** Bei 24 GB VRAM rechnet die CPU des NAS 36 GB Experten aus dem RAM, und die 9 GB kältesten liest die Engine bei Bedarf von der NVMe. Der Drafter (DFly2) hilft kaum: 0,19 angenommene Token je Prüfschritt.
- **Einlesen ist bis zu 7,5-mal langsamer.** Lange Prompts bremsen Hy4 nicht weiter (414 bis 438 Token/s), Flash-Next wird dagegen mit der Länge schneller.
- **Die NVMe liest dauernd,** pro Antwort mit 900 Token rund 160 GB. Lesen verschleißt eine SSD kaum, belastet den Verbund aber, solange das Modell schreibt.

## Die Falle: Mit Stratas eigener Aufteilung läuft der Speicher voll

Stratas Setup berechnet für diese Maschine 9,35 GB Experten im VRAM und 46,69 GB im RAM, nichts von der SSD, und schreibt beides in die Laufkonfiguration (`--vram-experts-gb`, `--ram-experts-gb`). Die Hy4-Engine verwirft beide Angaben („not used by this runner yet“). Ihr RAM-Budget rechnet sie aus dem gesamten Arbeitsspeicher, als liefe sonst nichts auf der Maschine. Sie legt deshalb alle 55,8 GB Experten fest in den RAM. Auf einem NAS, dessen Dienste daneben weiterlaufen, bleibt dann nichts übrig:

| Aufteilung nach Stratas Setup, Nacht 21./22.11.2026 | Ergebnis |
|---|---:|
| Schreiben (128K, 32K, ohne Drafter) | 0,3–0,6 Token/s |
| RAM verfügbar | 0 GiB, 7 GB ausgelagert |
| von der NVMe gelesen je Antwort mit 900 Token | 1,2–2,2 TB |
| Einlesen, kurzer und mittlerer Prompt | 217–307 Token/s |

Abhilfe ist die Umgebungsvariable `HY4_RAM_BUDGET_GB` in der Laufkonfiguration. Mit 36 GB läuft es stabil (Tabelle oben). Gemeldet an Strata: [Issue #6556](https://github.com/Niko1221/Strata/issues/6556).

## Und mit meinem Eigenbau?

strata-xtx ändert an Hy4 nichts. Die Hy4-Engine ist ein eigenes Programm und liest keinen der 27 Schalter meiner Tabelle, im Quelltext von 0.2.18 geprüft. Hy4 lief mit der Steuerung (Control) des Releases genauso schnell wie mit der meines Eigenbaus (4K: 224 gegen 228, 16K: 307 gegen 282 Token/s, beide in der Aufteilung des Setups gemessen).

## Nicht gemessen

Aufgabensatz und Qualität, Agentenläufe, Modus max, Bildeingang im Lauf mit RAM-Budget, eine cgroup-Speichergrenze statt `HY4_RAM_BUDGET_GB`. Bei 7 Token/s hätte allein der Aufgabensatz viele Stunden gedauert. Für mich war die Frage nach dem Tempo schon beantwortet.

## Dateien

| Datei | Inhalt |
|---|---|
| `speed.json` | 7 Läufe im Modus leise: Flash-Next unzensiert und Original, Hy4-Flash mit RAM-Budget 36 GB sowie in der Aufteilung des Setups (128K, 128K mit Release-Control, 32K, ohne Drafter). Je Lauf Laden, Tool-Call, Schreiben, Prompts mit versteckter Zahl, NVMe-Lesen, kleinster verfügbarer RAM, mittlere Leistung von NAS und Dock |

## Bedingungen

- 21./22.11.2026, Kontext 131.072, Karte leise (2.800 MHz, −100 mV). Flash-Next auf meinem Eigenbau strata-xtx auf Strata 0.2.18, Hy4-Flash mit `strata-hy4` 0.1.64 aus dem Release (Paket `hip-rx7900`), Modelldateien gegen Stratas SHA-256 geprüft.
- Temperatur 0, Denken aus, eine Anfrage nach der anderen, Werte aus den `timings` der Antworten. Der Agent auf dem NAS war während der Messung pausiert.
- NVMe-Bytes aus den Zählern der Blockgeräte, RAM aus `MemAvailable`, Leistung von NAS und Dock an der USV, alles während jedes Schritts abgetastet.
- Ein Durchgang mit Hy4s eigenen CPU-Schaltern (Kernzuordnung, Threads) lief nur in der Aufteilung des Setups, also unter Auslagerung, und ist nicht aussagekräftig. Er steht deshalb nicht in `speed.json`.
