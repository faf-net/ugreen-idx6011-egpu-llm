#!/usr/bin/env python3
"""Zwei Messungen für Strata-Rückmeldungen (19.10.2026), beide mit dem Produktionsmodell arbeit (0.1.44.1, IQ3_XXS, MTP):

  cpu     LP-E-Kerne: Strata zählt die zwei LP-E-Kerne der Core Ultra 7 255H (cpu_lowpower, CPU 14/15) als P-Kerne und
          belegt sie mit Pool-Workern. A = wie im Betrieb, B = Container auf CPU 0-13 begrenzt (--cpuset-cpus), sonst
          gleich. Drei verschränkte Paare, je Engine ein Aufwärmen und zwei gemessene Antworten.
  frisch  Einlesen bei frischen Engines mit MTP (Release 0.2.0, bekannte Grenze auf der R9700: etwa jede zweite frische
          Engine liest 10-23 % langsamer). Acht frische Engines, je ein 4K-Prompt nach dem Aufwärmen und ein zweiter.

Läuft auf der iDX:  python3 folgetests.py [cpu] [frisch]     (ohne Angabe: beide; nur wenn /running leer ist)
Ergebnis: /volume1/docker/ki-messung/ergebnisse/folgetests-<zeit>.jsonl
"""
import os, json, random, shutil, sys, time, urllib.request

LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")   # llama-swap
SWAP = "/volume1/docker/llama-swap/config.yaml"
ERGEBNISSE = "/volume1/docker/ki-messung/ergebnisse"
WOERTER = ("Haus Garten Fluss Rechner Netz Strom Licht Wolke Brücke Straße Fenster Lampe Buch Seite Karte Zug Hafen "
           "Markt Feld Wald Berg Tal Stadt Dorf Kabel Platte Speicher Schalter Turm Mauer Brunnen Weg Stein Glas").split()
GESCHICHTE = "Erzähle eine ruhige Geschichte über einen Leuchtturmwärter, etwa 600 Wörter, ohne Überschrift."


def frage(modell, text, max_tokens):
    body = {"model": modell, "messages": [{"role": "user", "content": text}], "max_tokens": max_tokens,
            "temperature": 0, "reasoning_effort": "none"}
    req = urllib.request.Request(LS + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.load(r)
    t = d.get("timings", {})
    return {"prompt_token": d["usage"]["prompt_tokens"], "neu_token": d["usage"]["completion_tokens"],
            "prompt_tps": t.get("prompt_per_second"), "decode_tps": t.get("predicted_per_second"),
            "draft_n": t.get("draft_n"), "draft_ok": t.get("draft_n_accepted"), "sekunden": round(time.time() - t0, 1)}


def entladen():
    urllib.request.urlopen(LS + "/unload", timeout=180).read()
    time.sleep(3)


def schreiben(ausgabe, z):
    print(json.dumps(z, ensure_ascii=False), flush=True)
    with open(ausgabe, "a") as f:
        f.write(json.dumps(z, ensure_ascii=False) + "\n")


def cpu_test(ausgabe):
    sicherung = SWAP + ".vor-folgetest-cpu-" + time.strftime("%Y%m%d-%H%M")
    shutil.copy2(SWAP, sicherung)
    t = open(SWAP).read()
    makro = t.split("  strata: >-\n", 1)[1].split("\n  llama:", 1)[0]
    t = t.replace("macros:\n", "macros:\n  strata_ohne_lpe: >-\n" + makro.replace("--network host", "--network host --cpuset-cpus 0-13", 1) + "\n", 1)
    t = t.replace("\n  frei:\n", """
  arbeit-ohne-lpe:
    name: "Test: arbeit ohne LP-E-Kerne (CPU 0-13)"
    cmd: ${strata_ohne_lpe} /strata/src/ls-arbeit.json
    cmdStop: docker stop -t 80 ls-${MODEL_ID}
    proxy: http://127.0.0.1:${PORT}
    checkEndpoint: /health
    ttl: 600

  frei:
""", 1)
    open(SWAP, "w").write(t)
    try:
        for _ in range(30):
            time.sleep(1)
            if any(m["id"] == "arbeit-ohne-lpe" for m in json.load(urllib.request.urlopen(LS + "/v1/models"))["data"]):
                break
        for paar in (1, 2, 3):
            for modell in ("arbeit", "arbeit-ohne-lpe"):
                entladen()
                frage(modell, "Sag OK.", 4)
                frage(modell, GESCHICHTE, 900)                     # Expertencache anwärmen
                for i in (1, 2):
                    schreiben(ausgabe, {"test": "cpu", "variante": modell, "paar": paar, "messung": i,
                                        **frage(modell, f"Lauf {time.time_ns()}. " + GESCHICHTE, 900)})
    finally:
        shutil.copy2(sicherung, SWAP)
        entladen()


def frisch_test(ausgabe, engines=8):
    rng = random.Random(19102026)
    for n in range(1, engines + 1):
        entladen()
        frage("arbeit", "Sag OK.", 4)
        for i in (1, 2):
            text = f"Lauf {time.time_ns()}.\n" + " ".join(rng.choice(WOERTER) for _ in range(3000)) + \
                   "\n\nIgnoriere die Wortliste. Antworte nur mit OK."
            schreiben(ausgabe, {"test": "frisch", "engine": n, "prompt": i, **frage("arbeit", text, 8)})
    entladen()


def main():
    if json.load(urllib.request.urlopen(LS + "/running", timeout=10)).get("running"):
        sys.exit("llama-swap hat ein Modell geladen, Abbruch")
    teile = sys.argv[1:] or ["cpu", "frisch"]
    ausgabe = f"{ERGEBNISSE}/folgetests-{time.strftime('%Y%m%d-%H%M')}.jsonl"
    if "cpu" in teile:
        cpu_test(ausgabe)
    if "frisch" in teile:
        frisch_test(ausgabe)
    print("Ergebnis:", ausgabe, flush=True)


if __name__ == "__main__":
    main()
