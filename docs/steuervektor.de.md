# `liber`: das unzensierte Modell

[English](steuervektor.md) · **Deutsch** · [← README](../README.de.md)

`liber` ist ein unzensiertes Modell. Es ist dasselbe 125B-Modell wie `faber`, aber ihm sind die Ablehnungen entfernt: Es beantwortet, was man es fragt, auch Fragen, die das Originalmodell verweigert. Chat und Agent können jedes der Modelle nutzen; `liber` ist eines davon und wird wie die anderen je Gespräch oder in der Einstellung des Agenten gewählt. Diese Seite sagt, wie das technisch geht, was es ändert, was es kostet und was man damit auf sich nimmt.

## Was „unzensiert“ hier heißt

Das Originalmodell ist darauf trainiert, bestimmte Bitten abzulehnen oder zu entschärfen. `liber` tut das nicht mehr. Es gibt keinen Filter davor und keinen dahinter, und es belehrt nicht. In meinen Tests hat es keine einzige Aufgabe abgelehnt.

Das betrifft nicht nur harmlose Fälle. Das Modell unterscheidet nicht mehr zwischen einer Frage, die zu Unrecht abgelehnt wurde, und einer, die das Original aus gutem Grund verweigert. Es beantwortet beide. Die Grenze zieht nur noch der Mensch, der fragt.

## Warum ich es nutze

Ab Werk lehnt das Modell vieles ab oder entschärft es, was auf dem eigenen Gerät niemanden etwas angeht. Ein Assistent zu Hause soll antworten und nicht erziehen. Außerdem schreibt `liber` das bessere Deutsch.

## Wie es funktioniert

Die Forschung an Sprachmodellen hat gezeigt, dass Ablehnungen weitgehend an einer einzigen Richtung in den inneren Aktivierungen des Modells hängen. Projiziert man diese Richtung heraus, hört das Modell auf abzulehnen; alles andere bleibt, wie es ist. Das Verfahren ist als „Abliteration“ bekannt. Strata unterstützt es als gewöhnliche Funktion: Eine Vektordatei (Steuervektor) wird beim Rechnen auf einen Bereich von Schichten angewandt. Die Gewichte auf der Platte bleiben unverändert, dieselben Dateien dienen also beiden Modellen.

Die Einstellungen stehen in [`konfig/strata-0.2.12/liber.json`](../konfig/strata-0.2.12/liber.json): Der Vektor wirkt auf die Schichten 4 bis 44, im Projektionsmodus, mit einer Richtung je Schicht. Die Vektordatei selbst ist nicht Teil dieses Repos; solche Dateien gibt es für viele Modelle öffentlich.

## Was es ändert, und was es kostet

![Dasselbe Modell zensiert und unzensiert](../bilder/steuervektor-de.png)

| | Original (`faber`) | unzensiert (`liber`) |
|---|---:|---:|
| 15 Aufgaben, die Modelle oft verweigern: beantwortet / ausgewichen / abgelehnt | 11 / 3 / 1 | 15 / 0 / 0 |
| bestandene Aufgaben (von 102) | 96 | 98 |
| Deutsch, verdeckt benotet (von 60) | 51 | 54 |
| Erfundenes erkannt, ohne Regeln (von 120) | 35 (29 %) | 20 (17 %) |
| Erfundenes erkannt, mit den vier Regeln (von 120) | 117 (98 %) | 109 (91 %) |
| Echtes richtig beantwortet, ohne / mit Regeln (von 120) | 120 / 120 | 119 / 119 |
| Schreiben, lange Antwort | 63,7 T/s | 61,9 T/s |
| Einlesen bei 32K | 1.183 T/s | 1.188 T/s |

Die 15 Aufgaben stammen aus Bereichen, in denen Sprachmodelle üblicherweise ablehnen, ausweichen oder belehren: Fiktion und Humor ohne Schonung, Gesundheit und Risiken, Sicherheit und Technik, strittige ethische Fragen. Im Einzelnen nenne ich sie hier nicht.

**Die Fähigkeiten bleiben.** Aufgaben, Deutsch und Tempo sind innerhalb der Streuung eines einzelnen Laufs gleich; der Unterschied von zwei Aufgaben ist kein Befund.

**Der Preis: Es erfindet leichter.** Ohne Regeln im Systemprompt erkennt `liber` nur 17 % des Erfundenen statt 29 %. Die [vier Regeln](agent.de.md) holen das meiste zurück, aber eine Lücke bleibt: 91 % statt 98 %, vor allem bei erfundenen Befehlsoptionen (17 von 24 erkannt). Ein Modell, das nicht mehr „nein“ sagt, sagt auch seltener „weiß ich nicht“. Wer es für einen Agenten nimmt, kann auf Regeln und Prüfer nicht verzichten.

**Das Urteil wird nicht besser.** Im Test mit zehn Runden befolgen beide Modelle eine harte Anweisung in 10 von 10 Antworten, und beide erfinden Fähigkeiten, wenn nachts ein Lauf abbricht: in 6 von 10 Antworten das Original, in 8 von 10 `liber`.

## Was man damit auf sich nimmt

- **Es gibt keine Schranke mehr.** Was das Modell schreibt, verantwortet allein, wer es betreibt und wer es fragt.
- **Es gehört nicht vor Kinder** und nicht in einen Dienst, den Fremde erreichen. Bei mir ist es nur im Heimnetz und hinter einer Anmeldung erreichbar.
- **Ein Agent mit Werkzeugen wird dadurch gefährlicher, nicht nur freier.** Ein unzensiertes Modell führt auch eine untergeschobene Anweisung aus einer Webseite oder Mail bereitwilliger aus. Deshalb darf der Agent bei mir nur freigegebene Befehle ausführen, und ein Prüfer liest jede Antwort.
- **Es weiß nicht mehr als das Original.** Wo es etwas nicht weiß, rät es, und es klingt dabei sicher.

Gelesen habe ich bei den 15 Aufgaben die Antwortanfänge. Veröffentlicht sind nur Zählwerte, keine Antworttexte: `messen/daten/2026-11-14-erfinden/steuervektor.json`.
