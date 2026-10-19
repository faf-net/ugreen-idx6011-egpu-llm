#!/usr/bin/env python3
"""Strata 0.2.0-beta (Engine-Paket 0.1.45.3 hip-rx7900, fertig gebaut) auf der RX 7900 XTX — 19.10.2026.

Laut Release-Notizen ist der RX-7000-Build nur kompiliert, auf keiner echten Karte gelaufen. Hier läuft er auf gfx1100,
mit denselben Gewichten, Packs und Einstellungen wie unser arbeit (0.1.44.1), damit die Zahlen vergleichbar sind.

  python3 t020.py --nur-konfig     Konfigurationen unter /volume1/docker/strata-020/run/ anlegen
  python3 t020.py                  ganzer Lauf (nur wenn llama-swap /running leer ist)

Schritte: strata doctor · a020 (wie arbeit) mit strata_bench --long, bench.py, needle_bench 32k/128k/250k ·
a020-auto (ohne --pool-workers: was plant 0.2.0 auf der Hybrid-CPU?) · Bildleser GPU gegen CPU (VRAM, Zeit, Antworten).
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request

LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")   # llama-swap
SWAP = "/volume1/docker/llama-swap/config.yaml"
BASIS = "/volume1/docker/strata-020"
RUN = f"{BASIS}/run"
PROD = "/volume1/docker/strata-test"
MESS = "/volume1/docker/ki-messung"
ZEIT = time.strftime("%Y%m%d-%H%M")
AUS = f"{MESS}/ergebnisse/t020-{ZEIT}"

DOCKER = ("docker run --rm {name} --network host --device /dev/kfd --device /dev/dri --group-add 44 --group-add 105 "
          "--security-opt seccomp=unconfined --ipc host --ulimit memlock=-1 --ulimit stack=67108864 "
          f"-v {BASIS}/control:/opt/strata -v {BASIS}/engine:/opt/engine -v {PROD}/data:/strata/data "
          f"-v {PROD}/vision:/strata/vision -v {PROD}/src/tools/hip:/strata/hip:ro -v {RUN}:/strata/run "
          "-e STRATA_ENGINE=/opt/engine/strata -w /opt/strata strata-hip:296b59d")
MAKRO = "  strata020: >-\n    " + DOCKER.format(name="--name ls-${MODEL_ID}") + \
        "\n    /opt/strata/python/bin/python3 serve/server.py --engine strata --port ${PORT} --config\n"
MODELLE = ["a020", "a020-auto", "a020-vcpu", "a020-vgpu"]


def konfig_anlegen():
    os.makedirs(RUN, exist_ok=True)
    basis = json.load(open(f"{PROD}/src/ls-arbeit.json"))
    a = basis["args"]
    a[a.index("--expert-profile") + 1] = "/opt/strata/data/expert-profile.bin"
    basis.update(exe="/opt/engine/strata", cwd="/opt/strata", lib_dirs=["/opt/engine"],
                 env={"STRATA_HIPBLASLT_TUNING": "/strata/hip/gfx1100-hipblaslt-100200.txt"}, open_browser=False)
    native = a[a.index("--native") + 1]
    for name in MODELLE:
        cfg = json.loads(json.dumps(basis))
        if name == "a020-auto":
            i = cfg["args"].index("--pool-workers")
            del cfg["args"][i:i + 2]
        if name.startswith("a020-v"):
            gpu = name == "a020-vgpu"
            cfg["args"].append("--vision")
            cfg["vision"] = {"exe": "/opt/engine/strata-vision-hip" if gpu else "/opt/engine/strata-vision",
                             "mmproj": "/strata/vision/mmproj-Qwen3.8-Flash-Next-BF16.gguf", "model": native,
                             "gpu": gpu, "max_tokens": 1024 if gpu else 300}
            if not gpu:
                cfg["vision"]["threads"] = 8
        cfg.update(model_name=name, log=f"/strata/run/{name}.log")
        json.dump(cfg, open(f"{RUN}/{name}.json", "w"), indent=1)
    print("Konfigurationen:", MODELLE, flush=True)


def eintraege():
    return "".join(f"""  {m}:
    name: "Test Strata 0.2.0 {m}"
    cmd: ${{strata020}} /strata/run/{m}.json
    cmdStop: docker stop -t 80 ls-${{MODEL_ID}}
    proxy: http://127.0.0.1:${{PORT}}
    checkEndpoint: /health
    ttl: 900

""" for m in MODELLE)


def swap_setzen(sicherung):
    shutil.copy2(SWAP, sicherung)
    t = open(SWAP).read().replace("macros:\n", "macros:\n" + MAKRO, 1).replace("\n  frei:\n", "\n" + eintraege() + "  frei:\n", 1)
    open(SWAP, "w").write(t)
    for _ in range(30):
        time.sleep(1)
        try:
            if set(MODELLE) <= {m["id"] for m in json.load(urllib.request.urlopen(LS + "/v1/models", timeout=10))["data"]}:
                return
        except Exception:
            pass
    sys.exit("Testeinträge erscheinen nicht in /v1/models")


def frage(modell, inhalt, max_tokens=8, timeout=1200):
    body = {"model": modell, "messages": [{"role": "user", "content": inhalt}], "max_tokens": max_tokens,
            "temperature": 0, "reasoning_effort": "none"}
    req = urllib.request.Request(LS + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d, round(time.time() - t0, 1)


def laden(modell):
    urllib.request.urlopen(LS + "/unload", timeout=180).read()
    time.sleep(3)
    d, s = frage(modell, "Sag OK.", 4)
    lauf = json.load(urllib.request.urlopen(LS + "/running", timeout=10)).get("running") or []
    proxy = next((r.get("proxy") for r in lauf if r.get("model") == modell), None)
    notiz(f"{modell} geladen in {s} s, Antwort {d['choices'][0]['message'].get('content')!r}, Backend {proxy}")
    return proxy


def notiz(text):
    print(f"{time.strftime('%H:%M:%S')} {text}", flush=True)
    with open(f"{AUS}/protokoll.txt", "a") as f:
        f.write(text + "\n")


def sh(befehl, datei, timeout=3600):
    notiz(f"$ {befehl}")
    with open(f"{AUS}/{datei}", "w") as f:
        r = subprocess.run(befehl, shell=True, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    notiz(f"  → Exit {r.returncode}, Ausgabe {datei}")


def logzeilen(modell, muster=r"pool|worker|VRAM free|hipblaslt|vision|image|encoder|error|warn|version|P-core|E-core|slots"):
    try:
        z = [l.rstrip() for l in open(f"{RUN}/{modell}.log", errors="replace") if re.search(muster, l, re.I)]
    except OSError as e:
        z = [repr(e)]
    open(f"{AUS}/log-{modell}.txt", "w").write("\n".join(z[:200]) + "\n")
    return z


def bilder(modell):
    sys.path.insert(0, f"{PROD}/vision")
    import visiontest as V
    erg = []
    for name, erzeuge, text, erwartet in V.BILDER:
        d, s = frage_bild(modell, text, erzeuge())
        antwort = d["choices"][0]["message"].get("content") or ""
        erg.append({"bild": name, "s": s, "antwort": antwort[:60], "richtig": all(w in antwort.lower() for w in erwartet),
                    "prompt_token": d["usage"]["prompt_tokens"]})
    return erg


def frage_bild(modell, text, png):
    import base64
    body = {"model": modell, "max_tokens": 40, "temperature": 0, "reasoning_effort": "none", "messages": [{"role": "user",
            "content": [{"type": "text", "text": text}, {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(png).decode()}}]}]}
    req = urllib.request.Request(LS + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r), round(time.time() - t0, 2)


def main():
    konfig_anlegen()
    if "--nur-konfig" in sys.argv:
        return
    if json.load(urllib.request.urlopen(LS + "/running", timeout=10)).get("running"):
        sys.exit("llama-swap hat ein Modell geladen, Abbruch")
    os.makedirs(AUS, exist_ok=True)
    sh(DOCKER.format(name="--name strata020-doctor") + " /opt/strata/bin/strata doctor", "doctor.txt", 300)
    sh(DOCKER.format(name="--name strata020-version") + " /opt/engine/strata --version", "engine-version.txt", 120)
    sicherung = f"{SWAP}.vor-t020-{ZEIT}"
    swap_setzen(sicherung)
    try:
        proxy = laden("a020")
        logzeilen("a020")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/strata_bench.py --url {proxy} --long --out {AUS}/strata-bench",
               "strata-bench.txt")
        sh(f"cd {MESS} && python3 bench.py --url {LS} --model a020 --label 020-a020 --out {AUS}/ "
           "--tests schreiben,einlesen,agent,qualitaet", "bench.txt")
        if proxy:
            for laengen in ("32k,128k", "250k"):
                sh(f"cd {PROD}/src && .venv/bin/python tools/needle_bench.py --url {proxy} --lengths {laengen} "
                   f"--depths 10,50,90 --out {AUS}/needles-{laengen.replace(',', '-')}.json", f"needles-{laengen.replace(',', '-')}.txt")
        logzeilen("a020")
        laden("a020-auto")
        sh(f"cd {MESS} && python3 bench.py --url {LS} --model a020-auto --label 020-auto --out {AUS}/ --tests schreiben",
           "bench-auto.txt")
        logzeilen("a020-auto")
        for m in ("a020-vcpu", "a020-vgpu"):
            try:
                laden(m)
                erg = bilder(m)
                notiz(f"{m} Bilder: {json.dumps(erg, ensure_ascii=False)}")
            except Exception as e:
                notiz(f"{m} FEHLER: {e!r}")
            z = logzeilen(m)
            notiz(f"{m} Log: " + " | ".join(l for l in z if re.search(r"VRAM free|vision|encoder", l, re.I))[:1500])
    finally:
        shutil.copy2(sicherung, SWAP)
        try:
            urllib.request.urlopen(LS + "/unload", timeout=180).read()
        except Exception as e:
            notiz(f"Entladen fehlgeschlagen: {e!r}")
        notiz(f"Ergebnis: {AUS} · config.yaml zurück aus {sicherung}")


if __name__ == "__main__":
    main()
