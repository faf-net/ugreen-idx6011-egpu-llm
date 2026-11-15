#!/usr/bin/env python3
"""Zwei Personen gleichzeitig: Wartezeit und Tempo, wenn zwei Gespräche zur selben Zeit laufen.

Jede Person führt ein eigenes Gespräch mit fünf Fragen hintereinander (der Verlauf wächst mit). Gemessen wird je
Frage die Wartezeit bis zum ersten Wort, das Schreibtempo und die Gesamtzeit:
  allein       Person A allein
  gleichzeitig Person A und Person B starten zur selben Zeit, am selben Modell
  wechsel      A und B fragen abwechselnd zwei verschiedene Modelle (--model und --zweites): jede Frage lädt um

  python3 zwei.py --model faber --zweites velox --aus zwei.json

Spricht mit llama-swap (URL wie in betrieb.py). Nur Standardbibliothek.
"""
import argparse, json, statistics, threading, time

import betrieb

FRAGEN = {
    "A": ["I want to plan a three-day trip to Hamburg with two teenagers in November. Suggest a plan for day one.",
          "Good. Now day two, with one indoor activity in case it rains.",
          "And day three, ending at the main station by 5 pm.",
          "Put the three days into one short table: day, morning, afternoon, evening.",
          "Write a short message to the family group chat that announces the plan."],
    "B": ["Explain in simple words how a heat pump heats a house.",
          "What does the number called COP mean, with one example calculation?",
          "Which three things should I check before replacing a gas boiler with a heat pump?",
          "Summarise your three answers in five bullet points.",
          "Write a polite e-mail asking an installer for a quote, using those points."],
}


def gespraech(model, person, aus, sperre=None):
    verlauf = []
    for i, frage in enumerate(FRAGEN[person], 1):
        verlauf.append({"role": "user", "content": frage})
        t_start = time.time()
        r = betrieb.anfrage(model, None, 400, nachrichten=verlauf)
        verlauf.append({"role": "assistant", "content": r.pop("text")})
        r.update(person=person, frage=i, beginn_s=round(t_start, 1),
                 tps=round(r["neu_token"] / r["schreib_s"], 1) if r["neu_token"] and r["schreib_s"] else None)
        aus.append(r)
        print(json.dumps(r), flush=True)


def kurz(laeufe):
    w = [l["erste_antwort_s"] for l in laeufe]; t = [l["tps"] for l in laeufe if l["tps"]]; g = [l["gesamt_s"] for l in laeufe]
    return {"fragen": len(laeufe), "warten_median_s": round(statistics.median(w), 2), "warten_max_s": max(w),
            "tps_median": round(statistics.median(t), 1), "gesamt_median_s": round(statistics.median(g), 1), "summe_s": round(sum(g), 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="faber"); p.add_argument("--zweites"); p.add_argument("--aus", default="zwei.json")
    a = p.parse_args()
    aus = {"model": a.model, "beginn": time.strftime("%Y-%m-%dT%H:%M:%S"), "phasen": {}}
    betrieb.anfrage(a.model, "Reply with the single word OK.", 4)  # laden
    allein = []
    gespraech(a.model, "A", allein)
    aus["phasen"]["allein"] = {"A": kurz(allein), "laeufe": allein}
    time.sleep(10)
    beide, t0 = [], time.time()
    fa = [threading.Thread(target=gespraech, args=(a.model, person, beide)) for person in "AB"]
    [f.start() for f in fa]; [f.join() for f in fa]
    aus["phasen"]["gleichzeitig"] = {"A": kurz([l for l in beide if l["person"] == "A"]), "B": kurz([l for l in beide if l["person"] == "B"]),
                                     "dauer_s": round(time.time() - t0, 1), "laeufe": beide}
    if a.zweites:
        time.sleep(10)
        wechsel = []
        for runde in range(3):
            for person, model in (("A", a.model), ("B", a.zweites)):
                r = betrieb.anfrage(model, FRAGEN[person][runde], 200)
                r.pop("text"); r.update(person=person, model=model, runde=runde + 1)
                wechsel.append(r); print(json.dumps(r), flush=True)
        aus["phasen"]["wechsel"] = {"warten_s": [l["erste_antwort_s"] for l in wechsel], "warten_median_s": round(statistics.median([l["erste_antwort_s"] for l in wechsel[1:]]), 1), "laeufe": wechsel}
    json.dump(aus, open(a.aus, "w"), indent=1)
    print(json.dumps({k: {x: y for x, y in v.items() if x != "laeufe"} for k, v in aus["phasen"].items()}, indent=1))


if __name__ == "__main__":
    main()
