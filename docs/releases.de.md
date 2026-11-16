# Strata-Versionen auf dieser Karte, eine nach der anderen

[English](releases.md) · **Deutsch** · [← README](../README.de.md)

In Konfigurationen, Skripten und Dateinamen tragen die beiden Modelle Kurznamen: `faber` ist Flash-Next 125B in der Quantisierung IQ3_XXS und im täglichen Einsatz; `velox` ist dasselbe Modell in der kleineren und schnelleren Quantisierung IQ2_XS.

Die neueste zuerst. Jede Version ist gegen ihre Vorgängerin gemessen, mit identischer Laufkonfiguration, nur Engine und Control getauscht. Übersichtstabelle und Diagramm: [README](../README.de.md#strata-versionen-auf-dieser-karte).

## Nachtrag 15.11.2026: Strata 0.2.14 liest lange Prompts schneller, getestet und noch nicht in Betrieb

Engine 0.1.60 `hip-rx7900` mit Control 0.1.60 gegen 0.2.12, gleiche Laufkonfiguration (`konfig/strata-0.2.12/`), NAS-Dienste an, nur mein Agent angehalten. Die Version verlegt das Prompt-Einlesen auf AMD und NVIDIA auf Stratas eigene Kernel, und die Release-Notiz enthält keine Messung für die RX 7900 unter Linux. Hier ist eine.

| Median Token/s | 0.2.14 | 0.2.12 | 0.2.13 |
|---|---:|---:|---:|
| 3 verschränkte Paare, gleiche Sitzung: Schreiben / Prompt mit 63 Token | 59,3 / 117,9 | 60,5 / 107,5 | |
| `standard-v1`, Paket: kurz Schreiben / 4K / 16K Prompt | 67,8 / 800 / 1.411 | 63,6 / 788 / 1.202 * | 67,7 / 799 / 1.203 * |
| `strata_bench.py --long`: 4K / 16K / 32K Prompt | 789 / 1.405 / 1.390 | 781 / 1.200 / 1.217 * | 782 / 1.203 / 1.217 * |
| Nadeln, Sekunden: 128K / 250K | 66–96 / 206 | 120–158 / 294 * | 99–112 / 238 * |

\* frühere Sitzungen (08. und 09.11.). Nur die Paare liefen mit beiden Versionen direkt nacheinander.

**Schreiben ist gleich, das Prompt-Einlesen ab 16K schneller.** In den Paaren derselben Sitzung liegt das Schreiben im Rauschen, der kurze Prompt ist 10 % schneller. Gegen die früheren Läufe ist 4K unverändert, 16K 17 % schneller und 32K 14 % schneller; das erste Token eines 16K-Prompts kommt nach 11,6 s statt 13,7 s, und die Nadel bei 250K ist nach 206 s statt 238 s gefunden. Nadeln 7/7, 8 von 8 frischen Engines gesund (637–758 Token/s), mein kleiner Aufgabensatz 28 von 29.

Eine Zahl geht in die andere Richtung: Im Agenten-Test von `strata_bench.py` liegt der Median des Schreibtempos über alle 18 Anfragen bei 63,7 Token/s, gegen 70,8 bei 0.2.13 und 71,8 bei 0.2.12 (die eigene Zusammenfassung des Werkzeugs ohne die ersten Züge: 70,4 gegen 73,7 und 73,2). Dieser Test erzeugt nur 756 Token, einzelne Anfragen streuen bei jeder Version zwischen 41 und 101 Token/s, und die Vorschläge des Drafters wurden diesmal seltener angenommen (54 % gegen 56 % und 59 %). Die Paare, die beide Versionen direkt nacheinander mit je 900 Token fuhren, zeigen keinen Unterschied. Deshalb habe ich in der Nacht zum 16.11. `strata_bench.py --long` je dreimal auf 0.2.12 und 0.2.14 in einer Sitzung gefahren, jede Engine frisch geladen, Reihenfolge je Runde gewechselt. **Es war Streuung:** Das Schreibtempo im Agenten-Test liegt bei 72,7 gegen 72,5 Token/s (Median der drei Läufe), und die erste Agenten-Sitzung nach einem frischen Start ist bei beiden Versionen die langsame (rund 70 Token/s gegen rund 84 in den späteren). Dieselbe Sitzung bestätigt den Gewinn beim Prompt-Einlesen ohne den Vorbehalt verschiedener Tage: 16K mit 1.387 gegen 1.196 Token/s (+16 %), 32K mit 1.380 gegen 1.215 (+14 %), 4K +2 %.

Zwei Dinge habe ich gezielt gesucht. Die Release-Notiz nennt für eine Radeon R9700 unter Linux Treiberpausen und einen Karten-Reset; in 192 kB Engine-Log dieser Sitzung steht keine solche Zeile, und das Kernel-Log ist sauber. Und `standard-v1` ist vollständig, besteht aber 11 von 12 Plausibilitätsprüfungen statt 12: Bei T2 kam kein strukturierter Tool-Call, das Modell schrieb, es habe das Werkzeug schon aufgerufen. Ein Lauf sagt mir nicht, ob das am Sampling bei Temperatur 1,0 liegt oder an der neuen Version.

Diesmal ohne Lauf im Docker-Image, `0.2.14-rocm-gfx110x` war zum Messzeitpunkt nicht veröffentlicht. Mein großer Aufgabensatz (114 Aufgaben, 102 automatisch bewertet) besteht auf 0.2.14 98 gegen 96 auf 0.2.12 (13.11.): Eine Code- und eine Logik-Aufgabe, die durchgefallen waren, bestehen jetzt, keine bestandene fällt durch; auf diesem Satz heißt das gleich, nicht besser. Er brauchte 1.489 s gegen 1.622 s, Schreiben im Median 75,2 gegen 73,5 Token/s. **Dieses NAS läuft vorerst weiter mit 0.2.12.** Rohdaten: `messen/daten/2026-11-15-v0.2.14/`, an Strata gemeldet als [#6056](https://github.com/Niko1221/Strata/issues/6056).

## Nachtrag 09.11.2026: Strata 0.2.13, und ohne gfx1100-Tabelle liest das Docker-Image 16K-Prompts 35 % langsamer

Engine 0.1.59 `hip-rx7900` mit Control 0.1.59 gegen 0.2.12, gleiche Laufkonfiguration (`konfig/strata-0.2.12/`), NAS-Dienste an. **0.2.13 ist hier gleich gut wie 0.2.12**: Paare in derselben Sitzung 60,0 gegen 60,7 Token/s beim Schreiben, `standard-v1` im Paket vollständig mit 12/12 (kurz schreiben / 4K / 16K: 67,7 / 799 / 1.203), `strata_bench.py --long` 4K / 16K / 32K mit 782 / 1.203 / 1.217, Nadeln 7/7 bis 250K (238 s bei 250K). Mein Aufgabensatz: 97 von 102 gegen 98 bei 0.2.12, eine Code-Aufgabe ist gekippt, 1.381 s gegen 1.430 s. Dieses NAS bleibt vorerst bei 0.2.12.

**Das unveränderte Docker-Image `0.2.13-rocm-gfx110x` nutzt die hipBLASLt-Tabelle für gfx1100 nicht mehr.** Die Engine schreibt ins Log, dass die Tabelle im Paket liegt und standardmäßig aus ist; die Release-Notiz nennt das nur für Windows. Unter Linux kostet es beim Prompt-Einlesen 14 % bei 4K und 35 % bei 16K (649 und 769 statt 756 und 1.186 Token/s mit dem Image von 0.2.12). `-e STRATA_HIPBLASLT_TABLE=on` holt es zurück (766 / 1.193). Wer das Image auf einer RX 7900 betreibt, sollte diese Variable setzen. Meine Laufkonfiguration setzt `STRATA_HIPBLASLT_TUNING` ausdrücklich und ist nicht betroffen. Rohdaten: `messen/daten/2026-11-09-v0.2.13/`, an Strata als [Issue #5666](https://github.com/Niko1221/Strata/issues/5666).

## Nachtrag 08.11.2026: Strata 0.2.12, jetzt in Betrieb, und der getunte DFlash2-Drafter auf gfx1100

Engine 0.1.58 `hip-rx7900` mit Control 0.1.58 gegen 0.2.11, gleiche Laufkonfiguration, NAS-Dienste an. **0.2.12 ist hier gleich gut wie 0.2.11**: Auf meinem eigenen Aufgabensatz (114 Aufgaben, 102 automatisch bewertet) bestehen beide 98 und brauchen 1.430 s; Paare in derselben Sitzung 59,9 gegen 61,2 Token/s beim Schreiben, im Rauschen. `standard-v1` vollständig mit 12/12 im Paket (kurz schreiben / 4K / 16K: 63,6 / 788 / 1.202) und im unveränderten Docker-Image (69,1 / 756 / 1.186), Nadeln 7/7 bis 250K. **Seit 08.11. läuft dieses NAS mit 0.2.12**, weiter mit MTP.

![Getunter DFlash2 gegen MTP: im festen Test schneller je Token, bei echten Aufgaben langsamer](../bilder/dflash2-0.2.12-de.png)

Das Release bringt einen **getunten DFlash2-Drafter** mit, meines Wissens auf gfx1100 bisher nicht gemessen. Er lädt sauber (591 MiB VRAM, keine MTP-Schicht) und schreibt im festen Test mit 900 Token bei Konfidenz 0,7 um 10–15 % schneller als MTP (92,6 gegen 83,0 Token/s im leisen Kartenprofil, 90,5 gegen 79,0 bei Werkstakt), wobei deutsche Prosa langsamer wird und nur Code gewinnt. Auf dem echten Aufgabensatz mit natürlicher Antwortlänge verliert er: Je Token gleich schnell (+1 %), aber nur 51 von 114 Antworten gleichen bei Temperatur 0 denen mit MTP, die geänderten werden länger (+28 % Token), die Gesamtzeit steigt um 16 %, und zwei mehrstufige Preisrechnungen gehen schief (96 gegen 98). Halb so viele CPU-Pool-Worker ändern nichts. DFlash2 bleibt auf dieser Karte aus. Startkonfigurationen (Betrieb und DFlash2-Test): `konfig/strata-0.2.12/`. Rohdaten: `messen/daten/2026-11-08-v0.2.12/`, an Strata als [Issue #5615](https://github.com/Niko1221/Strata/issues/5615).

## Nachtrag 05.11.2026: Strata 0.2.11, jetzt in Betrieb

Engine 0.1.57 `hip-rx7900` mit Control 0.1.57, gegen die Pakete von 0.2.10 (0.1.56) mit identischer Laufkonfiguration, nur Engine und Control getauscht. Laut Release-Notiz hatte das Projekt dieses Paket noch nicht mit einem Modell laufen lassen; auf dieser Karte lädt es, antwortet und besteht alles unten. Anders als beim Nachtrag zu 0.2.8 liefen die NAS-Dienste, nur mein Agent war angehalten.

| Median Token/s | 0.2.11 | 0.2.10 |
|---|---:|---:|
| 3 verschränkte Paare, gleiche Sitzung: Schreiben / Prompt mit 63 Token | 60,9 / 118,1 | 59,8 / 109,0 |
| `standard-v1`, Paket: kurz Schreiben / 4K / 16K Prompt | 67,0 / 797 / 1.192 | 65,6 / 797 / 1.204 * |
| `standard-v1`, unverändertes Docker-Image: kurz Schreiben / 4K / 16K Prompt | 65,0 / 758 / 1.182 | |
| `strata_bench.py --long`: 4K / 16K / 32K Prompt | 781 / 1.212 / 1.226 | |

\* nächtlicher Lauf mit 0.2.10 vom 03.11. Schreiben ist gleich; der Unterschied beim kurzen Prompt liegt in überlappenden Spannen. `standard-v1` auf beiden Wegen vollständig mit 12/12, unser Aufgabensatz 29 von 29, Nadeln 6/6 bei 32K und 128K und 1/1 bei 250K (239 s für 251.626 Token), 8 von 8 frischen Engines gesund (die erste, direkt nach dem Entpacken, las mit 457 Token/s, die übrigen sieben mit 670–750). Die Nadeln bei 128K und 250K waren rund 15 % schneller als im Nachtlauf von 0.2.10, aber nicht schneller als auf der ruhigen Maschine vom 31.10.; das schreibe ich deshalb nicht dem Release zu. Leistung der Karte beim Schreiben: 208 W im Median. **Seit dem 05.11. läuft dieses NAS mit 0.2.11**, dazwischen liefen 0.2.9 (Korrektur für still falsch gelesene lange Prompts, wenn der Engine-Stack im gepinnten Expertenspeicher lag, #3431) und 0.2.10. Laufkonfigurationen unverändert (`konfig/strata-0.2.11/`). Rohdaten: `messen/daten/2026-11-05-v0.2.11/`, an Strata als [Issue #5321](https://github.com/Niko1221/Strata/issues/5321).

## Nachtrag 31.10.2026: Strata 0.2.8, jetzt in Betrieb, gemessen auf ruhiger Maschine

Engine 0.1.54 `hip-rx7900` mit Control 0.1.54, gegen die Pakete von 0.2.3.1 mit identischer Laufkonfiguration, nur Engine und Control getauscht. Für diese Messung habe ich alle Dienste des NAS gestoppt, die nicht gebraucht wurden (Fotoverwaltung, Mediathek, Agent, Suche, Mail-Brücke, Dateiabgleich). Die Daten verschiedener Tage sind deshalb nicht streng vergleichbar, die Paare schon.

| Median Token/s | 0.2.8 | 0.2.3.1 |
|---|---:|---:|
| 3 verschränkte Paare, gleiche Sitzung: Schreiben / Prompt mit 63 Token | 61,4 / 111,2 | 61,6 / 121,2 |
| `strata_bench.py --long`: Chat / Agent schreiben | 68,3 / 75,6 | 67,3 / 78,3 * |
| Prompt 4K / 16K / 32K | 785 / 1.212 / 1.199 | 791 / 1.218 / 1.244 * |
| `standard-v1`, Paket / unverändertes Docker-Image: Prompt 4K / 16K | 791 / 1.201 und 740 / 1.222 | 800 / 1.203 und 749 / 1.220 * |

\* Lauf mit 0.2.3.1 vom 23.10., NAS-Dienste liefen. Schreiben ist gleich, Einlesen ab 4K ebenso. Nur den kurzen Prompt mit 63 Token las 0.2.8 in den Paaren rund 8 % langsamer, bei überlappenden Spannen; dort überwiegen die festen Kosten einer Anfrage. `standard-v1` auf beiden Wegen vollständig mit 12/12, unser Aufgabensatz 29 von 29, Nadeln 6/6 bei 32K und 128K und 3/3 bei 250K (223–237 s für 251.626 Token), 8 von 8 frischen Engines normal. **Seit dem 31.10. läuft dieses NAS mit 0.2.8.** Die Laufkonfigurationen sind unverändert (`konfig/strata-0.2.8/`, mit dem llama-swap-Makro). Skript: `messen/t028.py`. Rohdaten: `messen/daten/2026-10-31-v0.2.8/`; dieselben Daten gingen als [PR #4851](https://github.com/Niko1221/Strata/pull/4851) an Strata.

Was sich für diese Karte sonst geändert hat:

- **Das unveränderte Docker-Image lässt nach dem Laden 854 MiB VRAM frei** (0.2.3: 594 MiB) und hat im Lauf nicht mehr vor knappem VRAM gewarnt.
- **0.2.8 rettet leicht fehlerhafte Tool-Calls standardmäßig** (`"tool_call_recovery": false` schaltet das ab). In meiner kleinen Prüfung, 10 Agenten-Aufgaben je Version mit vier deklarierten Werkzeugen, war jede Antwort auf beiden Versionen schon ein sauberer Tool-Call; der neue Weg wurde also nicht berührt.
- **Die ruhige Maschine zeigt sich bei langen Prompts:** Der erste 128K-Prompt brauchte 98–111 s, in einem Nachtlauf mit allen Diensten 129–149 s.

## Nachtrag 23.10.2026: Strata 0.2.3.1, jetzt in Betrieb, und vier Versionen im Vergleich

In den Notes zu 0.2.3 steht die RX 7000 als gebaut, aber nicht auf echter Hardware getestet. Hier lief sie: Engine 0.1.48 `hip-rx7900` mit Control 0.1.48.1, gegen die Pakete von 0.2.2 mit identischer Laufkonfiguration, nur Engine und Control getauscht.

| Median Token/s | 0.2.3.1 | 0.2.2 |
|---|---:|---:|
| 3 verschränkte Paare: Schreiben / Prompt mit 63 Token | 62,5 / 111,7 | 61,6 / 112,3 |
| `strata_bench.py --long`: Chat / Agent schreiben | 67,3 / 78,3 | 66,0 / 72,5 * |
| Prompt 4K / 16K / 32K | 791 / 1.218 / 1.244 | 736 / 1.211 / 1.222 * |

\* Lauf mit 0.2.2 vom 21.10., vor `--kv-resident 32768` und dem Gesprächs-Cache von 9 GiB. Einlesen bei 4K ist in jedem Test rund 7 % schneller, Schreiben im Rahmen des Rauschens gleich. Nadeln 6/6 bei 32K und 128K und 3/3 bei 250K, `standard-v1` vollständig mit 12/12, unser Aufgabensatz 29 von 29, 8 von 8 frischen Engines normal. **Seit dem Abend des 23.10. läuft dieses NAS mit 0.2.3.1.** Die Modelle heißen hier jetzt `faber` (vorher `arbeit`) und `velox` (vorher `schnell`); Konfigurationen und das llama-swap-Makro mit den alten Namen als Aliase liegen in `konfig/strata-0.2.3.1/`. Skript: `messen/t0231.py`. Rohdaten: `messen/daten/2026-10-23-v0.2.3.1/`.

![Strata-Versionen auf derselben Karte](../bilder/versionen-de.png)

Von 0.2.0-beta bis 0.2.3.1 ist auf dieser Karte nichts langsamer geworden. Das Schreiben stieg von 61 auf 67 Token/s, vor allem durch die Worker-Planung von 0.2.1 für Hybrid-CPUs (#3262); das Einlesen bei 16K und 32K lag schon an seiner Grenze.

**Der erste 128K-Prompt brauchte im Lauf mit 0.2.3.1 217 s, wo jede frühere Version etwa 108 s brauchte.** Ein eigener A/B-Test (`messen/t128.py`) hat das geklärt: jedes Mal eine frische Engine, identische Laufkonfiguration, im Wechsel, je zweimal. 0.2.3.1 las den ersten 128K-Prompt in 110,5 und 110,8 s, 0.2.2 in 111,1 und 111,6 s, die Nadel wurde jedes Mal gefunden. Also kein Rückschritt; die 217 s waren ein Ausreißer in einem langen Testlauf, am wahrscheinlichsten durch Gesprächs-Cache und RAM, die die Tests davor gefüllt hatten.

## Nachtrag 21.10.2026, abends: Strata 0.2.2, ebenfalls im Betrieb

0.2.2 (Engine 0.1.47 `hip-rx7900`, Control 0.1.47) ändert an der Geschwindigkeit dieser Kombination nichts, macht sie aber robuster: Tool-Aufrufe mit falsch geschriebener Einleitung werden als Aufruf erkannt, ein NaN im langen Prompt bricht die Anfrage nicht mehr ab, ein seltener Hänger im ersten Verify-Fenster auf HIP ist behoben. Gemessen gegen die 0.2.1-Pakete mit derselben Startkonfiguration, nur Engine und Control getauscht:

| Median tok/s | 0.2.2 | 0.2.1 |
|---|---:|---:|
| 3 verschränkte Paare: Schreiben / 63-Token-Prompt | 62,1 / 93,6 | 60,5 / 93,9 |
| `strata_bench.py --long`: Chat / Agent Schreiben | 66,0 / 72,5 | 65,9 / 74,6 |
| Einlesen 4K / 16K / 32K | 736 / 1.211 / 1.222 | 742 / 1.204 / 1.210 |

Recall 6/6 bis 128K, 8 von 8 frischen Engines normal schnell, unser Aufgabensatz 28 von 29 (der eine Fehlschlag ist ein Fehlalarm der Prüfung: Die Phishing-Mail wurde geschrieben, mit einem Hinweis davor). **`strata bench run` aus dem Release-Paket ist jetzt vollständig („complete“)**, weil dem Control-Archiv eine `COMMIT`-Datei beiliegt. Das Docker-Image `0.2.2-rocm-gfx110x` läuft ebenfalls, mit denselben langsamen Voreinstellungen wie 0.2.1 (700 MiB Reserve, keine hipBLASLt-Tabelle, 16K mit 781 tok/s), der Rat oben gilt also weiter. **Seit dem Abend des 21.10. läuft dieses NAS mit 0.2.2.** Die Konfigurationen sind unverändert, nur das Makro bindet die neuen Pakete ein (`konfig/strata-0.2.2/`). Skript: `messen/t022.py`. Rohdaten: `messen/daten/2026-10-21-v0.2.2/`. Gemeldet in #3263 und PR #2904.

## Nachtrag 21.10.2026: Strata 0.2.1, jetzt hier im Betrieb

**Der Fix für die Hybrid-CPU aus Strata-Issue #3262 wirkt.** 0.2.1 zählt die zwei LP-E-Kerne (`cpu_lowpower`) als Effizienzkerne. Ohne `--pool-workers` plant es 10 Worker auf CPU 1–10 und lässt CPU 14/15 frei, das Setup im Docker-Image schreibt ebenfalls 10. Gemessen in 3 verschränkten Paaren, je Lauf eine frische Engine:

| | Schreiben tok/s | Prompt mit 63 Token, tok/s |
|---|---:|---:|
| 0.1.44.1, `--pool-workers 9` (zwei davon auf den LP-E-Kernen) | 63,3 | 66,1 |
| 0.2.1, `--pool-workers 9` (CPU 1–9) | 61,5 | 88,0 |
| **0.2.1 Standard, 10 Worker** | **61,1** | **97,6** |

Alles andere bleibt wie bisher: `strata_bench.py --long` 65,9 tok/s beim Schreiben, 742 / 1.204 / 1.210 tok/s bei 4K / 16K / 32K, Recall 6/6 bis 128K, unser Aufgabensatz 28 von 29, 8 von 8 frischen Engines normal schnell. Beide Verpackungsfehler aus #3263 sind in 0.1.46 behoben. **Seit 21.10. läuft dieses NAS mit den fertigen Release-Paketen** (Engine 0.1.46 `hip-rx7900`, Control 0.1.46.2) und ohne `--pool-workers`. Konfigurationen und das llama-swap-Makro liegen in `konfig/strata-0.2.1/`.

**Das Docker-Image `ghcr.io/niko1221/strata:0.2.1-rocm-gfx110x` läuft auf der XTX.** Laut Release war es gebaut, aber auf keiner Karte gestartet. Sein unveränderter `strata bench run --suite standard-v1 --track default` ist vollständig, 12/12 Prüfungen. Mit seinen eigenen Voreinstellungen liest es lange Prompts aber langsamer als unsere Konfiguration: 3 Slots, GPU-Bildleser, 128K, 700 MiB Reserve und keine hipBLASLt-Tabelle ergeben 772 tok/s bei 16K. **Die gfx1100-Tabelle liegt im Paket, ist in 0.2.1 aber nur Opt-in. Sie bringt +23 % bei 4K und +60 % bei 16K** (`STRATA_HIPBLASLT_TABLE=on` → 1.238 tok/s). Wer das Image nutzt, sollte sie setzen.

| `standard-v1`, Median aus 3, tok/s | kurz Prompt / Schreiben | 4K Prompt / Schreiben | 16K Prompt / Schreiben |
|---|---:|---:|---:|
| Docker-Image, Voreinstellungen | 43,3 / 58,9 | 605,4 / 55,9 | 772,0 / 55,0 |
| + `PARALLEL=1` | 57,8 / 63,7 | 623,9 / 59,3 | 773,8 / 58,7 |
| + `PARALLEL=1 STRATA_HIPBLASLT_TABLE=on` | 60,4 / 65,8 | 768,3 / 62,4 | 1.238,5 / 69,3 |
| Release-Pakete mit `konfig/strata-0.2.1/arbeit.json` | 51,7 / 69,0 | 743,9 / 63,5 | 1.236,7 / 62,5 |

An Strata gemeldet in #3262, #3263 und PR #2904, die Ergebnisse liegen dort mit. Skript: `messen/t021.py`. Rohdaten: `messen/daten/2026-10-21/`.

## Nachtrag 19.10.2026: Strata 0.2.0-beta, Bilder und drei Prüfungen für das Strata-Team

**Die fertig gebaute RX-7000-Engine von 0.2.0-beta läuft auf dieser Karte.** Laut Release ist das Paket `hip-rx7900` nur kompiliert und auf keiner echten RX 7000 gelaufen. Hier lief es auf der XTX, mit denselben Gewichten, Packs und Einstellungen wie `arbeit`. `strata_bench.py --long` ergab 61,3 tok/s beim Schreiben im Chat, 741 / 1.207 / 1.223 tok/s beim Einlesen von 4K / 16K / 32K und 68,6 % Cache-Treffer in der Agentensitzung, also dasselbe wie 0.1.44.1. Recall war 9/9 bis 250K, unser Aufgabensatz kam auf 27 von 29. Der Betrieb bleibt auf 0.1.44.1, weil die neue Version hier nichts Messbares bringt.

| | 0.1.44.1 (17.10.) | 0.2.0-beta `hip-rx7900` |
|---|---:|---:|
| Schreiben im Chat (`strata_bench --long`) | 63,7 | 61,3 tok/s |
| Einlesen 4K / 16K / 32K | 741 / 1.195 / 1.224 | 741 / 1.207 / 1.223 tok/s |
| Recall 32K / 128K / 250K | 9/9 | 9/9 |
| neue Standard-Workerzahl von 0.2.0 (hier 15) | – | 39,8 / 41,2 tok/s statt 59,7 / 64,0 mit `--pool-workers 9` |

**Auf einer Hybrid-CPU `--pool-workers` behalten.** 0.2.0 plant einen Worker je physischem Kern außer dem des Hosts. Auf der 255H sind das 15, und damit war es ein Drittel langsamer als mit 9. Außerdem hält Strata die zwei LP-E-Kerne (unter Linux `cpu_lowpower`, ohne L3) für P-Kerne und belegt sie früh. Auf CPU 0–13 begrenzt, las der Container kurze Prompts rund 40 % schneller (66 → 94 tok/s bei 63 Token); das Schreibtempo blieb gleich.

**Bilder direkt ins 125B-Modell.** Flash-Next hat einen eigenen Bildleser (mmproj, 907 MB). Auf der CPU (`--vision cpu`) kostet er keinen VRAM und rund 1 GiB RAM. Alle Testbilder hat er richtig gelesen, in 1,2–5 s je Bild. Unsere Engine 0.1.44.1 kann das schon, sobald `tools/vision` gebaut ist (`-DSTRATA_VISION_CUDA=OFF`). 0.2.0 nimmt auf 24-GB-Karten standardmäßig den GPU-Leser. Auf der XTX kostet der 776 Expertenslots (1,28 GiB), ein großes Bild dauert dafür 3,5 s statt 5,6 s. Wer aktualisiert und diesen Tausch nicht will, setzt `--vision cpu` ausdrücklich.

**Strata-Issue #3177** (MTP-Verify-Timeout auf einer einzelnen 7900 XTX bei ~54K Token) lässt sich hier nicht nachstellen. 6 von 6 Agentenanfragen mit 55.019 Token und je 2.500 Token Antwort liefen durch, auf 0.1.45 und 0.1.44.1, mit und ohne MTP-Kopf.

**Frische Engines.** Laut 0.2.0-Release liest auf der R9700 etwa jede zweite frische Engine mit MTP Prompts 10–23 % langsamer. Hier: Eine von 24 frischen 0.2.0-Engines las beide 4K-Prompts rund 38 % langsamer (420 statt etwa 675 tok/s), mit 0.1.44.1 keine von 24. Die Startzeilen der langsamen Engine glichen denen der anderen. Auf gfx1100 kommt es also auch vor, aber selten.

Skripte: `messen/visiontest.py`, `messen/r3177.py`, `messen/folgetests.py`, `messen/t020.py`. Rohdaten: `messen/daten/2026-10-19/`.

## Strata 0.1.44.1 gegen 0.1.45 (17.10.2026)

Für Flash-Next auf gfx1100 kein messbarer Unterschied, alle Werte im Rauschen:

| Variante | lang T/s | 8k einlesen T/s | 32k einlesen s | Agent s |
|---|---|---|---|---|
| 0.1.44.1 | 65,5 | 1.175 | 26,0 | 52,6 |
| 0.1.45 | 63,5 | 1.151 | 26,3 | 53,7 |
| 0.1.45 `--pool-affinity p-cores` | 61,0 | 1.134 | 27,2 | 48,1 |
| 0.1.45 `--pool-affinity measure` | 62,5 | 1.111 | 26,7 | 49,5 |
| 0.1.45 `STRATA_CPU_IQ_ALL_EXACT1=1` | 61,4 | 1.143 | 26,8 | 49,8 |

Langer Prompt (103.341 Token, frisch): 87,7 s · 88,1 s · mit `STRATA_SCORES_THREAD=1` 85,3 s. Gierige Antworten
(temperature 0) sind zwischen den Versionen **nicht** byte-identisch, inhaltlich aber gleich. `STRATA_HIP_WMMA`
gilt nur für gfx12.
