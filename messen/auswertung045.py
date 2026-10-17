#!/usr/bin/env python3
"""Tabelle der Messreihe Strata 0.1.45 (17.10.2026): liest ergebnisse/045-*.json und 045-langprompt.jsonl."""
import json, os, sys

E = sys.argv[1] if len(sys.argv) > 1 else "ergebnisse"
REIHE = ["arbeit", "t045-basis", "t045-pcores", "t045-measure", "t045-exact1"]
SPALTEN = [("schreiben_kurz", "tps_median", "kurz T/s"), ("schreiben_lang", "tps_median", "lang T/s"),
           ("einlesen_8000", "tps_median", "8k ein T/s"), ("einlesen_32000", "ttft_median_s", "32k ein s"),
           ("agent", "gesamt_s_median", "Agent s"), ("schreiben_lang", "ram_max_gib", "RAM GiB")]
de = lambda x: "–" if x is None else (f"{x:.1f}".replace(".", ",") if isinstance(x, float) else str(x))

print(f"{'Variante':14}" + "".join(f"{s[2]:>12}" for s in SPALTEN) + f"{'Qualität':>12}")
for m in REIHE:
    p = os.path.join(E, f"045-{m}.json")
    if not os.path.exists(p):
        continue
    d = json.load(open(p))
    zeile = f"{m:14}" + "".join(f"{de(d.get(t, {}).get(k)):>12}" for t, k, _ in SPALTEN)
    q = d.get("qualitaet", {})
    zeile += f"{(str(q.get('bestanden')) + '/' + str(q.get('geprueft'))) if q else '–':>12}"
    print(zeile)
    if q:
        print(" " * 14 + "  je Art: " + ", ".join(f"{k} {v}" for k, v in q.get("je_art", {}).items()))

lp = os.path.join(E, "045-langprompt.jsonl")
if os.path.exists(lp):
    print("\nLanger Prompt (frisch, ohne Denken):")
    for z in open(lp):
        r = json.loads(z)
        print(f"  {r['modell']:14} {r['prompt_token']:>8} Token  {de(r['sekunden']):>7} s  gefunden: {r['gefunden']}")
