# Unsloth UD-IQ2_XS v3.1 gegen meine IQ3_XXS-Datei auf Strata

[English](README.md) · **Deutsch**

Stand: 18.11.2026. Alle Zahlen sind gemessen, auf einer RX 7900 XTX im Dock an einem NAS mit 62 GB RAM, Strata 0.2.14.

Ich habe geprüft, ob die Unsloth-Quants in Fassung 3.1 (seit 04.11.2026) für mein Modell `faber` (Qwen3.8-Flash-Next 125B, ISTA GSQ-RCO IQ3_XXS) eine bessere Grundlage wären. UD-IQ2_XS v3.1 ist auf der Platte gleich groß wie meine Datei (75,8 GB, Experten 47,0 GB) und läuft mit derselben Laufkonfiguration.

## Ergebnis in Kürze

| | faber | UD-IQ2_XS v3.1 | Unterschied |
|---|---:|---:|---:|
| Perplexität gesamt (niedriger ist besser) | 4,153 | 3,854 | −7,2 % |
| Perplexität Agent-Mitschnitt | 4,927 | 4,119 | −16,4 % |
| Schreiben im Chat, leise (T/s) | 63,9 | 68,8 | +7,7 % |
| Schreiben im Agent-Test, leise (T/s) | 77,2 | 71,5 | −7,4 % |
| Einlesen 16K-Prompt, leise (T/s) | 1.404,8 | 1.261,5 | −10,2 % |
| Einlesen 16K-Prompt mit 28 Schaltern, leise (T/s) | 2.361,3 | 2.106,2 | −10,8 % |

- Im Maßstab ist die Unsloth-Datei in allen fünf Abschnitten besser als meine.
- Beim Tempo ist das Bild gemischt: im Chat schneller, im Agent-Test etwas langsamer, lange Prompts liest sie rund 10 % langsamer. Der Nachteil bleibt mit den Schaltern aus der Schalter-Messung vom 17./18.11.2026 bestehen; sie heben beide Dateien um rund zwei Drittel.
- Speicher und Stromaufnahme sind gleich.
- Die Variante mit Steuervektor lädt auf der Unsloth-Datei, und der Vektor wirkt (fünf Bitten, die Modelle oft ablehnen: 5 beantwortet statt 1).

## Was noch fehlt

- Der Aufgabensatz mit Werkzeugketten. Bessere Perplexität heißt nicht zwingend mehr gelöste Aufgaben.
- Für die Variante mit Steuervektor: Tempo, Arbeitsspeicher bei langen Prompts, Bildeingang, Tool-Call und ein Lauf mit den Schaltern.
- Ein Vergleich gegen das Original (Q8_0 passt nicht in 62 GB). „Gleiches Token“ und KL sagen deshalb nur, wie verschieden zwei Dateien sind, nicht welche näher am Original liegt.
- Woher der Einlese-Nachteil kommt, habe ich nicht gemessen.

Zum Vergleich: Die größere UD-IQ3_XXS v3.1 kam im selben Maßstab auf 3,929, braucht aber 7,8 GB mehr Arbeitsspeicher und war in meinem Aufbau langsamer; ich habe sie verworfen.

## Dateien

| Datei | Inhalt |
|---|---|
| `massstab.json` | Perplexität, gleiches Token und KL je Abschnitt, vier Vergleiche |
| `tempo-ohne-schalter.json` | 12 Läufe (2 Dateien × 3 Runden × leise/max), Einzelwerte und Mediane |
| `tempo-mit-schaltern.json` | dasselbe mit den 28 Umgebungsschaltern bei beiden Dateien |
| `ladeprobe.json` | Laden mit der faber-Konfiguration und mit der Variante mit Steuervektor, nur Zählwerte |

## Bedingungen

- Maßstab: `tools/quant_quality.py`, Experten auf der CPU, FP16-K/V, 5 × 999 Positionen, teacher-forced. Ein einzelner Textsatz.
- Tempo: `tools/strata_bench.py` ohne `--long`, 3 Runden in wechselnder Reihenfolge, je Ladung ein Lauf mit gedrosselter Karte („leise“) und einer mit voller Leistung („max“). Angegeben ist der Median aus 3 Runden. Mein Agent lief nebenher weiter; jeder Lauf wurde darauf geprüft, dass ihn niemand gestört hat.
- Pack der Unsloth-Datei mit `tools/iq_pack.py --compat-bf16` gebaut (195 Tensoren gerundet, größter Fehler 0,0184).
- Ohne und mit Schaltern habe ich zu verschiedenen Zeiten gemessen. Sauber vergleichbar sind die Paare innerhalb einer Datei.
