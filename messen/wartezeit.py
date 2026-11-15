#!/usr/bin/env python3
"""Wartezeit bis zum ersten Wort: erste Anfrage mit frischem Text und Folgefrage im selben Gespräch.

Für mehrere Textlängen (kurze Frage bis ganzes Buch) wird ein noch nie gesehener Text geschickt und die Zeit
bis zum ersten Wort gemessen. Danach folgt im selben Gespräch eine zweite Frage; dort greift der Gesprächs-Cache.

  URL=http://<host>:8090 python3 wartezeit.py --model faber --aus wartezeit.json
"""
import argparse, json, time, uuid

import betrieb

# Name, Zeilen des Fülltexts (eine Zeile sind rund 31 Token), Wiederholungen
FAELLE = [("kurze_frage", 0, 3), ("eine_seite", 22, 3), ("artikel_10_seiten", 225, 3), ("bericht_50_seiten", 1130, 2), ("buch_300_seiten", 6450, 1)]


def text(zeilen):
    lauf = uuid.uuid4().hex
    kopf = f"Batch {lauf[:8]}. "
    if not zeilen:
        return kopf + "What is the capital of Portugal? Answer in one sentence."
    daten = "\n".join(f"Record {i} of batch {lauf[:8]}: station {uuid.uuid4().hex[:6]} reported value {i * 37 % 1000}." for i in range(zeilen))
    return daten + "\n\nWhich value did record 3 report? Answer in one sentence."


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="faber")
    p.add_argument("--aus", required=True)
    a = p.parse_args()
    betrieb.anfrage(a.model, "Reply with the single word OK.", 4)  # Modell laden
    aus = {"model": a.model, "beginn": time.strftime("%Y-%m-%dT%H:%M:%S"), "faelle": {}}
    for name, zeilen, n in FAELLE:
        laeufe = []
        for _ in range(n):
            frage = text(zeilen)
            erst = betrieb.anfrage(a.model, frage, 60)
            verlauf = [{"role": "user", "content": frage}, {"role": "assistant", "content": erst["text"] or "OK."},
                       {"role": "user", "content": "And which value did record 5 report? One sentence." if zeilen else "And of Spain? One sentence."}]
            folge = betrieb.anfrage(a.model, None, 60, nachrichten=verlauf)
            laeufe.append({"prompt_token": erst["prompt_token"], "erste_anfrage_s": erst["erste_antwort_s"], "folgefrage_s": folge["erste_antwort_s"],
                           "folge_prompt_token": folge["prompt_token"]})
            print(name, laeufe[-1], flush=True)
        aus["faelle"][name] = laeufe
        json.dump(aus, open(a.aus, "w"), indent=1)


if __name__ == "__main__":
    main()
