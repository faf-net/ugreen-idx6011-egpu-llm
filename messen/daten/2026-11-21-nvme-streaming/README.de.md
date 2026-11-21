# Ein größeres Quant mit Experten von der NVMe

[English](README.md) · **Deutsch**

Stand 21.11.2026. Alle Zahlen sind gemessen, auf einer RX 7900 XTX im Dock eines NAS mit 62 GB RAM, auf meinem Eigenbau strata-xtx (xtx-2 auf Strata 0.2.17).

Strata kann ein Modell betreiben, das nicht ganz in VRAM und RAM passt: Was der Expertencache der Karte und ein RAM-Budget (`--resident-budget-gib`) nicht halten, liest die Engine während der Antwort aus der Modelldatei. Das NAS hat einen schnellen NVMe-Verbund (2 × 2 TB, RAID 1). Deshalb habe ich geprüft, ob sich ein größeres und genaueres Quant desselben 125B-Modells lohnt. Meine Datei im Betrieb ist IQ3_XXS mit 75,8 GB und passt in VRAM + RAM. Die Kandidaten waren Unsloths UD-IQ4_XS (93,7 GB) und UD-Q4_K_XL (111 GB), jeweils mit einem RAM-Budget von 45 GiB.

## Ergebnis in Kürze: Es lohnt sich nicht

| Modus leise, Median aus 2 × 900 Token | IQ3_XXS (im Betrieb) | UD-IQ4_XS | UD-Q4_K_XL |
|---|---:|---:|---:|
| Schreiben, Original (Token/s) | 61,6 | 45,8 | 23,6 |
| Schreiben, unzensierte Fassung (Token/s) | 61,0 | 43,6 | 24,2 |
| von der NVMe gelesen je Antwort mit 900 Token | 0,1 GB | 0,1–0,2 GB | 21–23 GB |
| Einlesen eines 58K-Prompts, unzensiert (Token/s) | 3.237 | 2.605 | 2.050 |
| dafür von der NVMe gelesen | 0,04 GB | 19,6 GB | 61,3 GB |
| Folgefrage nach dem 58K-Text (Token/s) | 55,6 | 35,1 | 21,3 |
| RAM verfügbar nach dem Laden, unzensiert | 7,7 GiB | 2,4 GiB | 2,3 GiB |
| Aufgabensatz, 102 bewertete Aufgaben (Original / unzensiert) | 96 / 96 | 95 / 96 | nicht gemessen |
| Aufgabensatz, Laufzeit (Original / unzensiert) | 22,0 / 23,3 min | 35,1 / 36,6 min | – |

- **Kein Qualitätsgewinn.** In meinem deutschen Aufgabensatz besteht UD-IQ4_XS so viele Aufgaben wie die IQ3_XXS-Datei im Betrieb (eine Aufgabe mehr oder weniger liegt in der Streuung zwischen zwei Läufen), braucht für den ganzen Satz aber rund 55 % länger.
- **UD-IQ4_XS ist langsamer, ohne beim Schreiben viel von der NVMe zu lesen.** Die größeren Experten passen seltener in den Cache der Karte, mehr davon werden aus dem RAM auf der CPU gerechnet: −28 % beim Schreiben. Die NVMe kommt erst bei langen Prompts ins Spiel (19,6 GB für 58K Token).
- **UD-Q4_K_XL liest bei jeder Antwort von der NVMe**, 21–23 GB für 900 Token, und schreibt mit weniger als halbem Tempo. Mit kleinerem Budget (35 GiB) bleibt mehr RAM frei (10,2 GiB), das Schreiben fällt aber auf 21 Token/s, und eine Antwort liest 41 GB.
- **Der Arbeitsspeicher wird für ein NAS zu knapp.** Mit beiden größeren Dateien bleiben neben den NAS-Diensten nur rund 2,3 GiB RAM verfügbar; meine Regel für den Alltagsbetrieb sind mindestens 3 GiB.
- **Der Modus max ändert das Bild nicht** (unzensierte Fassung: 64,8 gegen 42,5 und 24,5 Token/s).
- Alles andere lief auf allen Dateien: Tool-Call, Bildeingang, die versteckte Zahl in jedem Prompt gefunden, keine Fehlerzeilen, Auslagerung unverändert. Die Variante mit Steuervektor lädt auf beiden Unsloth-Dateien, und der Vektor wirkt (fünf Bitten, die Modelle oft ablehnen: je 5 von 5 beantwortet).

Das Nachladen von der NVMe ergibt hier nur Sinn, wenn es ein deutlich besseres Modell nur in einer Größe gibt, die nicht passt. Für dieses Modell ist das nicht so.

## Dateien

| Datei | Inhalt |
|---|---|
| `speed.json` | 10 Läufe (7 leise, 3 max): Laden, Schreiben, Prompts 4K/16K/58K mit Nadel, Folgefrage, von der NVMe gelesene Bytes und kleinster verfügbarer RAM je Schritt, die Budget- und Cache-Zeilen der Engine |
| `task-set-summary.json` | der Aufgabensatz für Original und unzensierte Fassung, IQ3_XXS gegen UD-IQ4_XS, je Kategorie und Laufzeit |

## Bedingungen

- 20.11.2026 (Tempo) und 21.11.2026 (Aufgabensatz), Kontext 131.072, Karte leise (2.800 MHz, −100 mV), sofern nicht max vermerkt.
- Packs der Unsloth-Dateien mit `tools/iq_pack.py --compat-bf16` gebaut.
- Die Engine kürzt ein Budget von 45 GiB auf das, was verfügbar ist: 44,02 GiB auf diesem NAS. Ihre eigene Warnung für lange Prompts steht in `speed.json` (`engine_notes`).
- NVMe-Bytes aus den Zählern der Blockgeräte, RAM aus `MemAvailable`, beides während jedes Schritts abgetastet.
- Der Aufgabensatz lief im Wechsel (Original IQ3, Original IQ4, unzensiert IQ3, unzensiert IQ4) ohne andere Last; der Agent auf dem NAS war pausiert.
