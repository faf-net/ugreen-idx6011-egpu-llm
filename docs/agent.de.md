# Dichte Modelle auf derselben Karte, und wie man das Erfinden senkt

[English](agent.md) · **Deutsch** · [← README](../README.de.md)

In Konfigurationen, Skripten und Dateinamen tragen die beiden Modelle Kurznamen: `faber` ist Flash-Next 125B in der Quantisierung IQ3_XXS und im täglichen Einsatz; `velox` ist dasselbe Modell in der kleineren und schnelleren Quantisierung IQ2_XS.

Nachtrag vom 14.11.2026 zum Abschnitt [Ein Agent obendrauf](../README.de.md#ein-agent-hermes-obendrauf).

Der Agent auf diesem NAS betreibt einen Datenbestand mit eigenen Werkzeugen. Er hat zwei Schwächen gezeigt: Er
erfindet Antworten auf Dinge, die es nicht gibt, und er kündigt Schritte an, für die er kein Werkzeug hat („ich
pausiere den Lauf“). Zwei Fragen: Hilft ein anderes Modell auf derselben Karte, und was hilft sonst?

**Dichte Modelle helfen nicht.** Qwen3.8-27B und Gemma 4 31B (je Q4, ganz im VRAM, llama.cpp Vulkan) gegen die beiden
MoE-Modelle dieses NAS (Strata 0.2.12), alle durch dasselbe Messprogramm:

![Sechs Modelle auf einer Karte: Schreibtempo gegen Deutsch](../bilder/dicht-moe-de.png)

| | Aufgaben (102) | Deutsch, blind (60) | Urteil (9) | Schreiben t/s | Einlesen 32K t/s | erstes Token bei 32K |
|---|---|---|---|---|---|---|
| Flash-Next IQ3_XXS (`faber`, MoE) | 96 | 51 | 7,5 | 63,7 | 1.183 | 27,0 s |
| Flash-Next IQ3_XXS, unzensiert ([`liber`](steuervektor.de.md), MoE) | 98 | 54 | 7 | 61,9 | 1.188 | 26,9 s |
| Flash-Next IQ2_XS (`velox`, MoE) | 97 | 46 | 6,5 | 73,5 | 1.321 | 24,3 s |
| Qwen3.8-27B (dicht) | 92 | 52 | 7 | 36,2 | 796 | 40,3 s |
| Gemma 4 31B (dicht) | 97 | 38 | 4 | 34,8 | 602 | 52,9 s |

Die dichten Modelle schreiben halb so schnell und urteilen nicht besser. Qwen3.8-27B schreibt gutes Deutsch, denkt aber
so lange, dass fünf Code-Aufgaben am Denkbudget von 8.000 Token scheitern. Gemma 4 liefert ungefragt Varianten und
durchsucht in der Lage „Werkzeug fehlt“ jedes Mal die eigene Konfiguration. Die Deutsch-Antworten wurden anonymisiert
und blind benotet, erst danach entschlüsselt.

**Vier Sätze im Systemprompt wirken stärker als die Modellwahl.** Die Probe `messen/halluzination.py` fragt in fünf
Bereichen nach je 8 echten und 8 erfundenen Dingen (Gemeinden, Befehlsoptionen, Fachbegriffe, Bücher, Parameter der
eigenen Werkzeuge), drei Runden, Temperatur 0,7. Dann dieselbe Probe mit diesem Zusatz im Systemprompt:

```
- Kennst du einen Ort, ein Buch, eine Person, einen Fachbegriff, einen Befehl oder eine Option nicht sicher,
  antworte „Weiß ich nicht“ oder „Das ist mir nicht bekannt“. Das ist eine richtige Antwort.
- Erfinde nie Bundesländer, Autoren, Formeln, Optionen oder Zahlen, auch nicht als Vermutung.
- Nenne nur Werkzeuge und Parameter, die oben stehen. Gibt es keins, sag: „Dafür habe ich kein Werkzeug.“
- Rufe für Fragen ohne Bezug zur Katalogdatenbank kein katalog-Werkzeug auf.
```

![Erfundenes erkennen, ohne und mit vier Regeln im Systemprompt](../bilder/erfinden-de.png)

Ohne Regeln erkennen die fünf Modelle nur 17 bis 60 % der erfundenen Dinge und erfinden den Rest, am häufigsten
Bundesländer erfundener Gemeinden und Optionen, die es nicht gibt. Mit den Regeln sind es 88 bis 99 %, und **Echtes
beantworten sie genauso richtig wie vorher** (117 bis 120 von 120): Die Regel macht sie nicht übervorsichtig. Am
meisten bleibt bei den dichten Modellen übrig, vor allem bei Gemeinden und Befehlsoptionen. Überraschend ist velox:
Das kleinere Modell mit niedrigerer Denkstufe erfindet schon ohne Regel nur halb so oft wie faber. Zweifelsfälle wurden
nachgelesen; Antworten mit „nicht bekannt“, die trotzdem eine Vermutung lieferten („möglicherweise liegt sie in …“), zählen als erfunden.
Grenzen: einzelne Fragen ohne Gesprächsverlauf und ein kurzer Systemprompt. In einem langen Agenten-Prompt ist die
Wirkung nicht gemessen. Die Regeln nennen außerdem genau die Arten von Dingen, nach denen die Probe fragt
(Bundesländer, Autoren, Optionen); ob sie bei anderen Fragen ebenso gut wirken, prüft die Gegenprobe im nächsten Absatz.

**Gegenprobe mit fremden Fragen (15./16.11.2026): Eine kurze Regel reicht gegen Erfundenes, eine strenge kostet richtige Antworten.**
Die vier Sätze oben nennen genau die Arten von Dingen, nach denen meine Probe fragt. Ob eine allgemein formulierte Regel
bei anderen Fragen wirkt, prüft `messen/erfinden2.py` mit vier öffentlichen Fragensätzen zu je 150 Fragen: Dinge, die es
nicht gibt (HalluLens), schwere Faktenfragen (SimpleQA Verified, deutsch), mittelschwere Alltagsfragen (MKQA, deutsch)
und Agentenfälle mit Werkzeugliste (When2Call). Zwei Regeln im Wortlaut, jeweils an einen kurzen Systemprompt gehängt:

```
Grundregel (E):  Beantworte, was du weißt. Kennst du eine Sache, einen Namen oder ein Werkzeug gar nicht,
                 sag das, statt etwas zu erfinden.

Strenge Regel (B):  Wenn du etwas nicht sicher weißt, sage ausdrücklich „Weiß ich nicht“. Das ist eine richtige
                    Antwort. Erfinde keine Fakten und keine Handlungen. Raten ist schlechter als Nichtwissen.
```

| `faber` (Original) | ohne Regel | Grundregel E | strenge Regel B | Regeln der ersten Probe (D) |
|---|---:|---:|---:|---:|
| Erfundenes als echt behandelt (von 150) | 20 | 6 | 0 | 0 |
| mittelschwere Fragen: richtig / falsch / enthalten | 90 / 58 / 2 | 87 / 60 / 3 | 84 / 30 / 36 | 75 / 23 / 52 |
| schwere Fragen: richtig / falsch / enthalten | 19 / 125 / 6 | 15 / 109 / 26 | 3 / 13 / 134 | 4 / 5 / 141 |

| `liber` (unzensiert) | ohne Regel | Grundregel E | strenge Regel B | Regeln der ersten Probe (D) |
|---|---:|---:|---:|---:|
| Erfundenes als echt behandelt (von 150) | 25 | 5 | 2 | 2 |
| mittelschwere Fragen: richtig / falsch / enthalten | 95 / 54 / 1 | 95 / 53 / 2 | 85 / 31 / 34 | 76 / 30 / 44 |
| schwere Fragen: richtig / falsch / enthalten | 14 / 134 / 2 | 21 / 113 / 16 | 5 / 21 / 124 | 1 / 14 / 135 |

- **Die Grundregel kostet bei diesen Fragen nichts.** Sie senkt das Erfinden nicht existierender Dinge von 20 auf 6 und von 25 auf 5, in
  ganzen Sätzen statt mit einer Formel, und lässt die Antworten auf echte Fragen, wie sie sind. Falsche Antworten auf
  echte Fragen fängt sie nicht ab.
- **Die strenge Regel halbiert die falschen Antworten und kostet richtige.** Auf den mittelschweren Fragen enthält sie
  sich bei 41 % der Antworten, die ohne Regel falsch waren, und bei 11 % derer, die richtig waren. Sie unterscheidet
  also, aber grob. Bei Fragen, die das Modell kaum beantworten kann, bleibt fast nur noch „Weiß ich nicht“ übrig.
- **Die Regeln der ersten Probe sind nicht besser als die strenge Regel,** sie kosten auf mittelschweren Fragen doppelt so viele
  richtige Antworten (90 → 75) für wenig mehr Wirkung.
- **Das unzensierte Modell erfindet etwas mehr,** die Unterschiede zum Original liegen aber im Bereich der Streuung.

**Bei Werkzeugen wirkt nur der ausdrückliche Satz, und auch er hat einen Preis.** In 60 Fällen ohne passendes Werkzeug
ruft faber ohne Regel 15-mal trotzdem eines auf (liber 21-mal). Die Grundregel und die strenge Regel ändern daran
nichts (15 und 14, liber 19 und 24). Mit dem Satz „Nenne nur Werkzeuge und Parameter, die du wirklich hast. Gibt es
keins, sag: „Dafür habe ich kein Werkzeug.““ sind es 10 (10), mit den Regeln der ersten Probe 6 (9). Dafür unterbleiben
berechtigte Aufrufe: von 50 Fällen mit passendem Werkzeug 32 statt 41 Aufrufe (liber 36 statt 46). Allein ist der Satz
also nicht besser als im Paket.

![Gegenprobe: Erfundenes als echt behandelt und der Preis bei echten Fragen, je Regel](../bilder/gegenprobe-de.png)

Vorbehalte: ein Lauf je Frage bei Temperatur 0,7; an der Grundregel gegen „ohne Regel“ sieht man, dass 10 bis 12
Antworten ohne jede Regelwirkung kippen, Unterschiede unter etwa 8 Antworten bedeuten also nichts. Gewertet hat faber
selbst; ich habe über 200 Urteile nachgelesen. Enthaltungen sind genau gezählt, bei „richtig“ gegen „falsch“ irrt der
Richter auf den mittelschweren Fragen bei etwa jedem sechsten Urteil, in beide Richtungen und in allen Spalten gleich.
Die mittelschweren Fragen stammen aus einer Übersetzung mit Mängeln und handeln oft von US-Fernsehen und Musik.
„Erfundenes als echt behandelt“ zählt nur klare Fälle; dazu kommen Antworten, die das Ding verneinen und raten, was
gemeint sein könnte (ohne Regel 35 und 43, mit Grundregel 18 und 25), teils richtig, teils erfunden. Die Spalte „Regeln der ersten Probe“ nutzt die drei
allgemeinen der vier Sätze oben, ohne den zur Katalogdatenbank; für sie und für die strenge Regel stammt die erste Zeile
aus dem einfacheren Urteil „erfunden oder erkannt“. Zählwerte und Urteile: `messen/daten/2026-11-16-erfinden2/`.

**Für Befehle und Optionen reicht die Grundregel nicht.** In den vier öffentlichen Fragensätzen kommen keine Befehlsoptionen
vor. Deshalb lief am 16.11. meine erste Probe noch einmal für das unzensierte Modell, einmal mit der Grundregel und einmal
mit den Regeln der ersten Probe, in einer Sitzung (3 Runden, Temperatur 0,7, je Bereich 24 erfundene Dinge). Erkannt als
erfunden, nach Durchsicht von Hand:

| Bereich | Grundregel | Regeln der ersten Probe |
|---|---:|---:|
| Befehlsoptionen | 7 von 24 | 21 von 24 |
| Ortsnamen | 12 von 24 | 22 von 24 |
| Fachbegriffe | 19 von 24 | 22 von 24 |
| Buchtitel | 24 von 24 | 24 von 24 |
| Werkzeugparameter | 24 von 24 | 24 von 24 |

Mit der Grundregel erklärt das Modell eine erfundene Option weiter flüssig, wenn sie plausibel klingt, etwa
`tar --dedupe-links`. Sie hilft also bei Dingen, die fremd klingen, und beim Werkzeug, aber nicht dort, wo ein Agent am
meisten Schaden anrichten kann. Für Befehle, Optionen und Orte braucht es die ausdrückliche Nennung aus der ersten Probe.
Echtes beantwortet das Modell mit beiden Regeln gleich gut (119 und 120 von 120). Die automatische Wertung des Skripts
übersieht Ablehnungen in ganzen Sätzen und zählt bei der Grundregel 4 statt 7 Befehlsoptionen; beide Zählungen stehen in
`messen/daten/2026-11-16-erfinden2/nachprobe-befehle.json`.

**Beim Urteil helfen drei Runden nicht weiter.** Mit `messen/agent_de.py` bekam faber dieselben Betriebslagen zehnmal
statt dreimal:

![Das 125B-Modell als Betriebsagent: 10 Runden je Lage](../bilder/urteil-de.png)

Eine harte Anweisung („weicht die Zahl ab, hör auf“) hält das Modell in 10 von 10 Antworten ein. Muss es selbst
abwägen, sieht es schlechter aus als nach drei Runden: Bricht ein Sammellauf ab, während niemand wach ist, erfindet es in
6 von 10 Antworten Fähigkeiten („ich pausiere die Sammlung“, „Retry mit Backoff“). Fehlt ein angekündigtes Werkzeug,
meldet es das nur in 3 von 10 Antworten sauber; meist will es die eigene Konfiguration durchsuchen.

**Darum drei Schichten statt einer:**

![Drei Schichten gegen Erfinden, und was jede abfängt](../bilder/schichten-de.png)

Die Regeln im Prompt fangen erfundene Fakten ab, aber nicht angekündigte Schritte. Dafür liefern die Werkzeuge des
Agenten jetzt einen fertigen Satz samt erlaubter nächster Schritte, die Zahlen kommen damit aus dem Code. Und ein kleiner
Prüfer ohne Sprachmodell liest jede Antwort mit: [`konfig/hermes-pruefer/`](../konfig/hermes-pruefer/), ein Plugin für
Hermes Agent. Er meldet unbelegte Zahlen, angekündigte Schritte ohne Werkzeug und unbekannte Werkzeugnamen. Auf den
Agentenantworten fand er alle sechs erfundenen Abbruch-Antworten, ohne Fehlalarm in den übrigen Aufgaben. Erfundene
Fakten in Worten sieht er nicht: Von 269 erfundenen Probeantworten hätte er keine gemeldet. Rohdaten (nur Zählwerte):
`messen/daten/2026-11-14-erfinden/`.
