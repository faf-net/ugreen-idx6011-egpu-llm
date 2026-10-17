#!/usr/bin/env python3
"""Gleiche Antworten? Schickt dieselben Prompts gierig (temperature 0) an zwei Modellnamen hinter llama-swap
und vergleicht die Texte zeichengenau. 17.10.2026, Test Strata 0.1.45 gegen 0.1.44.1.

  python3 identitaet.py --url http://127.0.0.1:8090 --a arbeit --b t045-basis --out ergebnisse/identitaet-045.json
"""
import argparse, json, time, urllib.request

PROMPTS = [
    ("kurz", "Erkläre in drei Sätzen, was ein Mixture-of-Experts-Modell ist.", "none"),
    ("code", "Schreibe eine Python-Funktion, die prüft, ob eine Zeichenkette ein Palindrom ist, mit zwei Tests.", "none"),
    ("rechnen", "Ein Zug fährt 2 h mit 80 km/h und 1,5 h mit 120 km/h. Wie hoch ist die Durchschnittsgeschwindigkeit?", "low"),
    ("liste", "Nenne die fünf größten Städte Deutschlands nach Einwohnern, je eine Zeile.", "none"),
]


def frage(url, modell, text, effort):
    body = {"model": modell, "messages": [{"role": "user", "content": text}], "temperature": 0, "top_k": 1,
            "max_tokens": 600, "reasoning_effort": effort, "seed": 1}
    req = urllib.request.Request(url + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.load(r)
    m = d["choices"][0]["message"]
    return {"text": m.get("content") or "", "denken": m.get("reasoning_content") or "",
            "token": d.get("usage", {}).get("completion_tokens"), "s": round(time.time() - t0, 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True); p.add_argument("--a", required=True); p.add_argument("--b", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    erg = {"A": {}, "B": {}}
    for seite, modell in (("A", a.a), ("B", a.b)):                      # erst alle Prompts an A, dann an B: nur ein Modellwechsel
        for name, text, effort in PROMPTS:
            erg[seite][name] = frage(a.url, modell, text, effort)
            print(seite, modell, name, erg[seite][name]["token"], "Token", erg[seite][name]["s"], "s", flush=True)
    vergleich = {}
    for name, _, _ in PROMPTS:
        x, y = erg["A"][name], erg["B"][name]
        gleich = x["text"] == y["text"] and x["denken"] == y["denken"]
        n = next((i for i, (c, d) in enumerate(zip(x["text"], y["text"])) if c != d), min(len(x["text"]), len(y["text"])))
        vergleich[name] = {"gleich": gleich, "erste_abweichung_bei_zeichen": None if gleich else n}
        print(f"{name:8} {'GLEICH' if gleich else 'ANDERS ab Zeichen ' + str(n)}")
    json.dump({"a": a.a, "b": a.b, "ergebnisse": erg, "vergleich": vergleich}, open(a.out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
