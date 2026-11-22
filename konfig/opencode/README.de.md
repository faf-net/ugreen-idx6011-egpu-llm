# OpenCode mit den lokalen Modellen

[English](README.md) · **Deutsch**

[OpenCode](https://opencode.ai) ist ein Programmier-Agent für das Terminal. Mit der `opencode.jsonc` aus diesem
Ordner nutzt er die Modelle auf dem NAS über llama-swap statt eines Dienstes aus der Cloud.

```bash
mkdir -p ~/.config/opencode
cp opencode.jsonc ~/.config/opencode/opencode.jsonc     # danach die Adresse von llama-swap eintragen
opencode
```

Als Dienst im Heimnetz (so läuft es hier seit dem 22.11.2026): Ein Rechner im Heimnetz betreibt OpenCode
dauerhaft, mit Passwort, und jeder Rechner, jedes Handy oder Tablet bedient ihn aus dem Terminal oder im Browser.
Eine Sitzung läuft weiter, wenn der Laptop zugeklappt wird.

```bash
# auf dem Rechner, der den Dienst trägt (zum Beispiel als systemd-Benutzerdienst)
OPENCODE_SERVER_PASSWORD=<Passwort> opencode serve --hostname <seine Adresse im Heimnetz> --port 4096
# auf jedem Rechner im Heimnetz
OPENCODE_PASSWORD=<Passwort> opencode --server http://<Adresse>:4096
```

Im Browser erreicht man dieselben Sitzungen unter `http://<Adresse>:4096`. Den Port im Heimnetz lassen; der
Dienst führt auf diesem Rechner Befehle aus.

Was ich gelernt habe:

- **Eine Anfrage nach der anderen.** Strata beantwortet Anfragen nacheinander. Schreibt gerade der Agent oder
  der Chat, wartet OpenCode, und umgekehrt.
- **Überall dasselbe Modell.** llama-swap hält genau ein Modell auf der Karte. Fragt OpenCode ein anderes an als
  Chat oder Agent, werfen sie sich gegenseitig hinaus, und jeder Wechsel kostet rund 20 Sekunden. Deshalb nutzt
  auch der Titel-Agent dasselbe Modell wie die Arbeit.
- **Wenige Werkzeuge.** Jede Werkzeugbeschreibung wird bei jeder Anfrage mitgelesen. Ein MCP-Server mit mehreren
  hundert Werkzeugen kostete mein lokales Modell Minuten je Schritt; solche Server lasse ich abgeschaltet und
  schalte sie bei Bedarf ein.
- **Die Datei steht im eigenen Format von OpenCode 2.** OpenCode 2 liest das ältere v1-Format noch und übersetzt
  es, hat bei mir dabei aber die Bildeingabe eines Modells verloren.
