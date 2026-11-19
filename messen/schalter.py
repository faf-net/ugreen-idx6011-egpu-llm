#!/usr/bin/env python3
"""Die 28 Schalter für das Einlesen in eine Laufkonfiguration eintragen, prüfen und wieder herausnehmen.

Die Schalter sind Umgebungsvariablen der unveränderten Strata-Engine (Abschnitt "env" der Laufkonfiguration).
Die Liste steht in konfig/strata-0.2.14/prompt-schalter.json; dieses Skript trägt sie ein oder nimmt sie heraus.
Hintergrund, Messwerte und Grenzen: docs/schalter.de.md.

  python3 schalter.py stand              welche Modelle die Schalter tragen, Abweichungen von der Liste
  python3 schalter.py ein liber          Sicherung, Schalter eintragen, Modell entladen
  python3 schalter.py zurueck liber      PLAN B: Schalter herausnehmen (alles andere bleibt), Modell entladen
  python3 schalter.py pruefen liber      Kurzantwort, Tool-Call, 16K-Prompt, Fehlerzeilen im Engine-Log

"zurueck" entfernt genau die Schlüssel aus der Liste und fasst sonst nichts an; es braucht die Sicherungsdatei nicht.
llama-swap wird nicht neu gestartet: Die Engine liest ihre Laufkonfiguration bei jedem Laden neu.

Umgebung: STRATA_KONFIG (Ordner mit <modell>.json und <modell>.log, Vorgabe /strata/konfig),
SCHALTER_LISTE (Vorgabe: die Datei aus diesem Repo), LS_URL (llama-swap, Vorgabe http://localhost:8090).
"""
import json, os, shutil, sys, time, urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
PROD = os.environ.get("STRATA_KONFIG", "/strata/konfig")
LISTE = os.environ.get("SCHALTER_LISTE", os.path.join(os.path.dirname(HIER), "konfig", "strata-0.2.14", "prompt-schalter.json"))
PROTOKOLL = f"{PROD}/prompt-schalter.log"
LS = os.environ.get("LS_URL", "http://localhost:8090")
MODELLE = ("faber", "liber", "velox")
WOERTER = ("Haus Garten Fluss Rechner Netz Strom Licht Wolke Brücke Straße Fenster Lampe Buch Seite Karte Zug Hafen "
           "Berg Tal Wiese Wald Stein Sand Meer Insel Turm Glocke Uhr Tisch Stuhl").split()


def liste():
    return json.load(open(LISTE, encoding="utf-8"))["schalter"]


def konf(m):
    return f"{PROD}/{m}.json"


def lies(m):
    return json.load(open(konf(m), encoding="utf-8"))


def schreib(m, k):
    text = json.dumps(k, ensure_ascii=False, indent=1) + "\n"
    with open(konf(m), "r+", encoding="utf-8") as f:      # in place, wie bei config.yaml
        f.seek(0); f.write(text); f.truncate()


def notiz(text):
    zeile = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}"
    with open(PROTOKOLL, "a", encoding="utf-8") as f:
        f.write(zeile + "\n")
    print(zeile)


def laeuft():
    try:
        d = json.load(urllib.request.urlopen(LS + "/running", timeout=10))
        return [x.get("model") for x in d.get("running", [])]
    except Exception as e:
        return [f"?{e}"]


def entladen(m):
    if m in laeuft():
        urllib.request.urlopen(LS + "/unload", timeout=120).read()
        notiz(f"{m} entladen; lädt beim nächsten Aufruf mit der neuen Konfiguration")
    else:
        print(f"{m} ist nicht geladen, nichts zu entladen (geladen: {laeuft()})")


def stand():
    s = liste()
    for m in MODELLE:
        env = lies(m).get("env", {})
        da = {k: env[k] for k in s if k in env}
        anders = {k: (env[k], s[k]) for k in da if env[k] != s[k]}
        wort = "AUS" if not da else ("AN" if len(da) == len(s) and not anders else "TEILWEISE")
        print(f"{m:6} {wort:9} {len(da)}/{len(s)} Schalter" + (f" · abweichend: {anders}" if anders else "")
              + (f" · fehlen: {sorted(set(s) - set(da))}" if da and len(da) < len(s) else ""))
    print("geladen:", laeuft())


def ein(m):
    s, k = liste(), lies(m)
    sich = konf(m) + ".vor-schalter-" + time.strftime("%Y%m%d")
    if not os.path.exists(sich):
        shutil.copy2(konf(m), sich)
    env = k.setdefault("env", {})
    doppelt = {x: env[x] for x in s if x in env and env[x] != s[x]}
    assert not doppelt, f"schon mit anderem Wert gesetzt: {doppelt}"
    env.update(s)
    schreib(m, k)
    assert all(lies(m)["env"].get(x) == w for x, w in s.items())
    notiz(f"{m}: {len(s)} Schalter eingetragen; Sicherung {os.path.basename(sich)}; Rückweg: schalter.py zurueck {m}")
    entladen(m)


def zurueck(m):
    s, k = liste(), lies(m)
    env = k.get("env", {})
    raus = [x for x in s if x in env]
    for x in raus:
        del env[x]
    schreib(m, k)
    assert not any(x in lies(m).get("env", {}) for x in s)
    notiz(f"{m}: {len(raus)} Schalter herausgenommen (Plan B); übrige Konfiguration unverändert")
    entladen(m)


def post(body, timeout=900):
    req = urllib.request.Request(LS + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=timeout))
    return d["choices"][0]["message"], d.get("timings", {}), d.get("usage", {}), round(time.time() - t0, 1)


def pruefen(m):
    ok = True
    msg, t, u, s = post({"model": m, "messages": [{"role": "user", "content": "Antworte mit genau einem Wort: Wie heißt die Hauptstadt von Frankreich?"}], "max_tokens": 2000})
    kurz = (msg.get("content") or "").strip()
    print(f"Kurzantwort {s} s: {kurz[:60]!r}"); ok &= "Paris" in kurz
    werkzeug = [{"type": "function", "function": {"name": "wetter", "description": "Wetter für einen Ort", "parameters": {"type": "object", "properties": {"ort": {"type": "string"}}, "required": ["ort"]}}}]
    msg, t, u, s = post({"model": m, "messages": [{"role": "user", "content": "Wie ist das Wetter in Hamburg? Nutze das Werkzeug."}], "tools": werkzeug, "max_tokens": 2000})
    rufe = msg.get("tool_calls") or []
    print(f"Tool-Call {s} s: {[r['function']['name'] + ' ' + r['function']['arguments'] for r in rufe]}"); ok &= bool(rufe) and rufe[0]["function"]["name"] == "wetter"
    text = " ".join(WOERTER[(i * 7) % len(WOERTER)] for i in range(11000))
    frage = text[:len(text) // 2] + " Die Inventarnummer der Lampe im Flur lautet 48213. " + text[len(text) // 2:] + "\n\nWie lautet die Inventarnummer der Lampe im Flur? Nur die Zahl."
    msg, t, u, s = post({"model": m, "messages": [{"role": "user", "content": frage}], "max_tokens": 2000})
    tps = t.get("prompt_per_second") or 0
    print(f"Langer Prompt {u.get('prompt_tokens')} Token in {s} s, Einlesen {tps:.0f} T/s, Antwort {(msg.get('content') or '').strip()[:40]!r}")
    ok &= "48213" in (msg.get("content") or "")
    an = all(x in lies(m).get("env", {}) for x in liste())
    if an and tps < 1700:
        print("WARNUNG: Schalter eingetragen, aber Einlesen unter 1.700 T/s – wirken sie noch?"); ok = False
    log = f"{PROD}/{m}.log"
    schlecht = [z.strip() for z in open(log, encoding="utf-8", errors="replace").read().splitlines()[-600:]
                if any(w in z.lower() for w in ("non-finite", "nan ", "device lost", "hip error", "traceback", "out of memory"))]
    print(f"Engine-Log, letzte 600 Zeilen: {len(schlecht)} Fehlerzeilen" + ("".join("\n  " + z[:160] for z in schlecht[:5])))
    ok &= not schlecht
    notiz(f"{m}: Prüfung {'bestanden' if ok else 'NICHT bestanden'} (Schalter {'an' if an else 'aus'}, Einlesen {tps:.0f} T/s)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    was = sys.argv[1] if len(sys.argv) > 1 else "stand"
    if was == "stand":
        stand()
    else:
        m = sys.argv[2]
        assert m in MODELLE, m
        {"ein": ein, "zurueck": zurueck, "pruefen": pruefen}[was](m)
