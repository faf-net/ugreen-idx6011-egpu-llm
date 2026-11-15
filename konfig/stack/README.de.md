# Chat und Websuche für das NAS

[English](README.md) · **Deutsch**

Open WebUI und SearXNG in einer Compose-Datei, beide nur im Heimnetz. Die Sprachmodelle kommen von llama-swap
(siehe `konfig/strata-0.2.12/`).

```bash
cp .env.beispiel .env        # ADRESSE, LLAMA_SWAP_URL und SEARXNG_SECRET eintragen
docker compose up -d
```

Danach `http://<Adresse des NAS>:3000` öffnen. Das erste Konto, das man anlegt, wird Verwalter; danach ist die
Anmeldung geschlossen, weitere Konten legt der Verwalter an.

Getestet am 15.11.2026 auf dem iDX6011 Pro (UGOS Pro 1.21.1, Docker Compose 5.1.3), neben dem laufenden Betrieb:
Das erste Konto wird Verwalter, eine zweite Anmeldung wird abgelehnt, die Modellliste zeigt die Modelle von
llama-swap, die Websuche liefert Treffer, eine Chat-Antwort kommt zurück. Speicher: Open WebUI 689 MiB, SearXNG
139 MiB. Mit geladenem 125B-Modell blieben rund 5 GiB der 64 GB verfügbar.

Was man wissen sollte:

- **Open WebUI rechnet hier nichts selbst.** Embedding-, Reranking- und Sprachmodelle sind abgeschaltet, weil der
  Arbeitsspeicher neben dem 125B-Modell knapp ist. Hochgeladene Dokumente gehen ganz in den Kontext des Modells.
- **Den Port an die Adresse des NAS binden**, nicht an `0.0.0.0`: Veröffentlichte Docker-Ports umgehen die
  Firewall von UGOS.
- **llama-swap lauscht an der Adresse des NAS, nicht an localhost.** Diese Adresse gehört in `LLAMA_SWAP_URL`.
- **Ein Modell für alle.** Zwei Personen am selben Modell warten ein paar Sekunden aufeinander; zwei Personen an
  zwei verschiedenen Modellen lassen die Karte bei jedem Wechsel umladen, rund 20 s jedes Mal.
- Neue Ordner unter `/volume1/docker` erben unter UGOS eine ACL; kann ein Container nicht nach `./daten`
  schreiben, Besitzer und Rechte ausdrücklich setzen.

Der Agent steckt nicht in dieser Datei: Hermes Agent so installieren, wie seine eigene Dokumentation es
beschreibt, und die Einstellungen aus [docs/agent.de.md](../../docs/agent.de.md) übernehmen.
