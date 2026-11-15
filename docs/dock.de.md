# Die Dock-Störungen und ihre zwei Wochenuhren

[English](dock.md) · **Deutsch** · [← README](../README.de.md)

Was man über das Dock wissen muss, steht im [README](../README.de.md#dock-und-anbindung-was-man-wissen-muss). Diese Seite ist die Untersuchung hinter dem Punkt „Abrisse“ dort.

## Nachtrag 21.10.2026: Die Störungen folgen zwei Wochenuhren

Seit 15.10. sekundengenau mitgeschnitten (`messen/dock-mitschnitt.sh`, nur lesend: Kernel-Meldungen, Linkwechsel, AER-Zähler an Dock-, NVMe- und 10-GbE-Port, Linkstatus und Leistung der Karte). Rückwärts im Kernel-Protokoll zerfallen die Ereignisse in zwei Reihen:

| Reihe | Ereignisse | Schritt je Woche | Deutung |
|---|---|---|---|
| Sonntag | 13.09. 17:14:33 · 20.09. :36 · 27.09. :39 · 04.10. :43 · 18.10. :49,8 | +3,3 s (etwa 5,5 ppm) | eine frei laufende Uhr, wie ein Quarz ohne Zeitabgleich |
| Mittwoch | 23.09. 17:40:00 · 30.09. 18:01:10 · 07.10. 18:22:22 · 14.10. 18:43:32 · **21.10. 19:04:41** | +21 min 9–12 s | ein fester Abstand von 7 Tagen 21 min 10 s: **der wöchentliche Akkutest der USV** (siehe unten) |

**Die Vorhersage für Mittwoch traf auf 2 s genau.** Vorhergesagt 19:04:43, gemessen: Die 10-GbE-Karte verlor um 19:04:41,3 für 5,1 s den Link, 1,5 s später meldete der Dock-Port einen korrigierten Empfangsfehler (`RxErr`). Der OCuLink-Link blieb bei 16 GT/s ×4, kein Modell war geladen, die Karte lag im Leerlauf bei 17 W. Am 14.10. fiel der 10-GbE-Link pünktlich aus, obwohl die Karte gar nicht am Bus hing. Die Quelle sitzt also außerhalb des NAS. Das Kupfer-Netzkabel und das OCuLink-Kabel fangen sie beide ein; das Dock ist ein Opfer, nicht die Ursache. Im Ereignisprotokoll des Routers steht zu diesen Zeiten nichts. Auszug: `messen/daten/dock-2026-10-21/`.

**Nachtrag, dieselbe Nacht: Die Mittwochsreihe ist der Akkutest der USV.** NAS und Dock hängen als einzige Verbraucher an einer Eaton Ellipse PRO 1200, die minütlich über NUT gelesen wird. In sechs Wochen lag ihr Akkustand genau sechsmal unter 100 %, jedes Mal in der Minute direkt nach einem Mittwochsereignis (16.09. 17:18:58, 23.09. 17:40:12, 30.09. 18:01:49, 07.10. 18:22:49, 14.10. 18:44:14, 21.10. 19:05:29): 100 → 99 %, Restlaufzeit 3.814 → 3.775 s, etwa 20 Minuten später wieder 100 %. Drei dieser Messpunkte haben sogar die Laufzeitschätzung im Akkubetrieb erwischt (1.037 s und 2.812 s statt 3.814 s). Laut Datenblatt testet die USV ihren Akku einmal pro Woche; die 21 Minuten Versatz pro Woche kommen von ihrer eigenen Uhr. Mittwochs wird das NAS also nicht von außen gestört: Die eigene USV schaltet es für einige Sekunden auf Akku, und diesen Umschaltvorgang fangen der Netz-Link und der OCuLink-Link ein (bei 5 von 6 Tests; am 16.09. ist nichts protokolliert). Der minütlich gelesene Status bleibt `OL`, deshalb fiel es zuerst nicht auf. NUT bietet bei diesem Modell keinen Befehl, den Test zu starten oder zu planen. Die Sonntagsreihe zeigt keine solche Spur und bleibt offen.

Als Nächstes zeigt die Sonntagsreihe am 25.10. (Ende der Sommerzeit), ob ihr Gerät auf Winterzeit umstellt (17:14:53) oder nicht (16:14:53). Am 28.10. ist die Mittwochsreihe um 18:25:51 Uhr MEZ fällig, wenn sie wirklich ein fester Abstand ist. Wer an einem OCuLink-Port wiederholt `RxErr` sieht: erst sekundengenau mitschneiden und nach einem Wochenmuster suchen, bevor man Kabel oder Dock tauscht.

## Wie oft es wirklich passiert (09.09. bis 15.11.2026)

Aus den Kernelmeldungen des Dock-Ports über 67 Tage, Vorfälle mit mehr als zehn Minuten Abstand getrennt gezählt:

| Ursache | Störungen | Karte vom Bus gefallen |
|---|---:|---:|
| Sonntagsreihe, jede Woche zur selben Uhrzeit, Ursache offen | 7 | 0 |
| Mittwochsreihe, der wöchentliche Akkutest der USV | 5 | 0 |
| von mir ausgelöst: Netzstecker der USV gezogen, Geräte an derselben USV umgesteckt oder geschaltet | 7 | 1 |
| ohne bekannten Anlass | 4 | 3 |
| **gesamt** | **23** | **4, an 3 Tagen** |

Die meisten Störungen sind ein einzelner korrigierter Empfangsfehler und sonst nichts. Vom Bus gefallen ist die Karte an drei Tagen: Zweimal war sie nach rund 20 s elektrisch zurück, am 08.10. blieb sie bis zum nächsten Neustart unbrauchbar. **In diesen zehn Wochen hat kein Abriss das NAS neu gestartet**; jeder aufgezeichnete Kernel-Absturz stammt aus meinen eigenen Tests, bei denen ich die Karte bei geladenem Modell per Software entfernt habe. Meine Lehre daraus: An die USV, die NAS und Dock versorgt, gehört nichts, was schaltet. Die Zuordnung „von mir ausgelöst“ stammt aus meinen Notizen dieser Tage, nicht aus dem Log. Daten: `messen/daten/dock-2026-11-15/vorfaelle.json`.
