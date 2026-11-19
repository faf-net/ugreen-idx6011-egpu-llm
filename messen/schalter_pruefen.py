#!/usr/bin/env python3
"""Kennt eine Strata-Engine die 28 Schalter noch? Prüfung für jedes neue Release, ohne Karte.

Die Schalter sind Umgebungsvariablen, die Strata nicht dokumentiert. Ein Release kann sie umbenennen oder
streichen; die Engine ignoriert einen unbekannten Namen dann stillschweigend, und das Prompt-Einlesen fällt
auf das alte Tempo zurück. Dieses Skript sucht die Namen als Zeichenketten in den Dateien der Engine.

  python3 schalter_pruefen.py <engine-ordner> [schalterliste.json] [--alt <engine-ordner-der-produktion>]

Ausgabe: JSON mit "bekannt", "fehlend" und "urteil". Mit --alt zusätzlich, welche Namen gegenüber der
laufenden Engine verschwunden sind. Endet mit 1, wenn ein Name fehlt.

Ein gefundener Name beweist nicht, dass der Schalter noch dasselbe tut. Dafür ist die Messung da:
derselbe 16K-Prompt mit und ohne Schalter (schalter.py pruefen, strata_bench.py).
"""
import json, os, sys

HIER = os.path.dirname(os.path.abspath(__file__))
LISTE = os.path.join(os.path.dirname(HIER), "konfig", "strata-0.2.14", "prompt-schalter.json")


def namen_in(ordner, namen):
    gefunden = {}
    for wurzel, _, dateien in os.walk(ordner):
        for d in dateien:
            pfad = os.path.join(wurzel, d)
            try:
                if os.path.getsize(pfad) > 2_000_000_000 or os.path.islink(pfad):
                    continue
                inhalt = open(pfad, "rb").read()
            except OSError:
                continue
            for n in namen:
                if n.encode() in inhalt:
                    gefunden.setdefault(n, []).append(os.path.relpath(pfad, ordner))
    return gefunden


def main():
    arg = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not arg:
        sys.exit(__doc__)
    alt = sys.argv[sys.argv.index("--alt") + 1] if "--alt" in sys.argv else None
    if alt:
        arg = [a for a in arg if a != alt]
    engine = arg[0]
    liste = arg[1] if len(arg) > 1 else LISTE
    namen = sorted(json.load(open(liste, encoding="utf-8"))["schalter"])
    da = namen_in(engine, namen)
    aus = {"engine": engine, "schalter": len(namen), "bekannt": sorted(da), "fehlend": [n for n in namen if n not in da]}
    if alt:
        vorher = namen_in(alt, namen)
        aus["verschwunden_gegenueber_produktion"] = [n for n in namen if n in vorher and n not in da]
    aus["urteil"] = ("alle Namen vorhanden" if not aus["fehlend"] else
                     f"{len(aus['fehlend'])} Namen fehlen: Tempo mit und ohne Schalter neu messen, bevor das Release in Betrieb geht")
    print(json.dumps(aus, indent=1, ensure_ascii=False))
    sys.exit(1 if aus["fehlend"] else 0)


if __name__ == "__main__":
    main()
