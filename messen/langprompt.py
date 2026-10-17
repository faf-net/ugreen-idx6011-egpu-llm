#!/usr/bin/env python3
"""Einlesezeit eines frischen langen Prompts über llama-swap — 17.10.2026, Test STRATA_SCORES_THREAD (Strata 0.1.45).

Baut einen Text mit ~ZIEL Token (zufällige Sätze, fester Seed, in der Mitte eine versteckte Zahl), schickt ihn
mit max_tokens 24 und ohne Denken, misst die Zeit bis zur Antwort und prüft, ob die Zahl gefunden wurde.
Jeder Lauf hängt eine neue Zufallszeile an den Anfang, damit kein Gesprächs-Cache greift.

  python3 langprompt.py --url http://127.0.0.1:8090 --model t045-scores --ziel 131000 --out ergebnisse/lang.json
"""
import argparse, json, random, time, urllib.request

WOERTER = ("Haus Garten Fluss Rechner Netz Strom Licht Wolke Brücke Straße Fenster Tür Lampe Buch Seite Karte Zug "
           "Hafen Markt Feld Wald Berg Tal Stadt Dorf Kabel Platte Speicher Schalter Turm Mauer Brunnen Weg").split()
VERBEN = "steht liegt wartet leuchtet fällt dreht läuft hält zeigt bleibt".split()


def text(ziel_token, rng, zahl):
    saetze, n = [], 0
    while n < ziel_token:                      # grob 1,6 Token je Wort bei deutschem Text
        s = f"Der {rng.choice(WOERTER)} {rng.choice(VERBEN)} neben dem {rng.choice(WOERTER)} und dem {rng.choice(WOERTER)}."
        saetze.append(s); n += 14
    saetze.insert(len(saetze) // 2, f"Die geheime Prüfzahl lautet {zahl}.")
    return " ".join(saetze)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True); p.add_argument("--model", required=True)
    p.add_argument("--ziel", type=int, default=131000); p.add_argument("--out", required=True)
    a = p.parse_args()
    rng = random.Random(17102026)
    zahl = 48213
    t = text(a.ziel, rng, zahl)
    kopf = f"Lauf {time.time_ns()}.\n"
    body = {"model": a.model, "max_tokens": 24, "temperature": 0, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": kopf + t + "\n\nWie lautet die geheime Prüfzahl? Antworte nur mit der Zahl."}]}
    req = urllib.request.Request(a.url + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.load(r)
    dauer = time.time() - t0
    antwort = d["choices"][0]["message"].get("content") or ""
    erg = {"modell": a.model, "prompt_token": d.get("usage", {}).get("prompt_tokens"), "sekunden": round(dauer, 1),
           "gefunden": str(zahl) in antwort, "antwort": antwort.strip()[:80]}
    print(json.dumps(erg, ensure_ascii=False), flush=True)
    with open(a.out, "a") as f:
        f.write(json.dumps(erg, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
