#!/usr/bin/env python3
"""Strata 0.2.1 (Engine-Paket 0.1.46 hip-rx7900, Control 0.1.46.2) auf der RX 7900 XTX — 21.10.2026.

Anlass: #3262. 0.2.1 zählt die LP-E-Kerne (cpu_lowpower) als E-Kerne und soll auf der 255H 10 statt 15 Worker planen.
Der Maintainer bittet um Startlog und tok/s. Gleiche Gewichte, Packs und Einstellungen wie arbeit (0.1.44.1) und t020.

  python3 t021.py --nur-konfig     Konfigurationen unter /volume1/docker/strata-021/run/ anlegen
  python3 t021.py                  ganzer Lauf (nur wenn llama-swap /running leer ist)

Schritte: strata doctor · b021 (wie arbeit, 9 Worker) mit strata_bench --long, bench.py, needle_bench 32k/128k ·
Worker-Paare b021-auto (Plan von 0.2.1) gegen b021 · acht frische Engines · strata bench run --suite standard-v1.
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request

LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")
SWAP = "/volume1/docker/llama-swap/config.yaml"
BASIS = "/volume1/docker/strata-021"
RUN = f"{BASIS}/run"
PROD = "/volume1/docker/strata-test"
MESS = "/volume1/docker/ki-messung"
ZEIT = time.strftime("%Y%m%d-%H%M")
AUS = f"{MESS}/ergebnisse/t021-{ZEIT}"

DOCKER = ("docker run --rm {name} --network host --device /dev/kfd --device /dev/dri --group-add 44 --group-add 105 "
          "--security-opt seccomp=unconfined --ipc host --ulimit memlock=-1 --ulimit stack=67108864 "
          f"-v {BASIS}/control:/opt/strata -v {BASIS}/engine:/opt/engine -v {PROD}/data:/strata/data "
          f"-v {PROD}/vision:/strata/vision -v {PROD}/src/tools/hip:/strata/hip:ro -v {RUN}:/strata/run "
          "-e STRATA_ENGINE=/opt/engine/strata -w /opt/strata strata-hip:296b59d")
MAKRO = "  strata021: >-\n    " + DOCKER.format(name="--name ls-${MODEL_ID}") + \
        "\n    /opt/strata/python/bin/python3 serve/server.py --engine strata --port ${PORT} --config\n"
MODELLE = ["b021", "b021-auto"]


def konfig_anlegen():
    os.makedirs(RUN, exist_ok=True)
    basis = json.load(open(f"{PROD}/src/ls-arbeit.json"))
    a = basis["args"]
    a[a.index("--expert-profile") + 1] = "/opt/strata/data/expert-profile.bin"
    basis.update(exe="/opt/engine/strata", cwd="/opt/strata", lib_dirs=["/opt/engine"],
                 env={"STRATA_HIPBLASLT_TUNING": "/strata/hip/gfx1100-hipblaslt-100200.txt"}, open_browser=False)
    for name in MODELLE:
        cfg = json.loads(json.dumps(basis))
        if name == "b021-auto":
            i = cfg["args"].index("--pool-workers")
            del cfg["args"][i:i + 2]
        cfg.update(model_name=name, log=f"/strata/run/{name}.log")
        json.dump(cfg, open(f"{RUN}/{name}.json", "w"), indent=1)
    print("Konfigurationen:", MODELLE, flush=True)


def eintraege():
    return "".join(f"""  {m}:
    name: "Test Strata 0.2.1 {m}"
    cmd: ${{strata021}} /strata/run/{m}.json
    cmdStop: docker stop -t 80 ls-${{MODEL_ID}}
    proxy: http://127.0.0.1:${{PORT}}
    checkEndpoint: /health
    ttl: 7200

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


def logzeilen(modell, muster=r"pool|worker|VRAM free|hipblaslt|tuning|error|warn|version|P-core|E-core|efficien|lowpower|hybrid|core|slots|MTP|draft"):
    try:
        z = [l.rstrip() for l in open(f"{RUN}/{modell}.log", errors="replace") if re.search(muster, l, re.I)]
    except OSError as e:
        z = [repr(e)]
    open(f"{AUS}/log-{modell}.txt", "w").write("\n".join(z[:200]) + "\n")
    return z


def paare(ausgabe, n=3):
    """Wie folgetests.cpu_test: je Engine Aufwärmen, dann zwei gemessene Antworten; b021-auto und b021 verschränkt."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import folgetests as F
    F.LS = LS
    for paar in range(1, n + 1):
        for modell in ("b021-auto", "b021"):
            laden(modell)
            F.frage(modell, F.GESCHICHTE, 900)
            for i in (1, 2):
                F.schreiben(ausgabe, {"test": "worker", "variante": modell, "paar": paar, "messung": i,
                                      **F.frage(modell, f"Lauf {time.time_ns()}. " + F.GESCHICHTE, 900)})
            z = logzeilen(modell, r"pool|worker|core|efficien|lowpower|hybrid")
            notiz(f"{modell} Plan: " + " | ".join(z[-6:])[:800])


def frisch(ausgabe, engines=8):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import folgetests as F
    F.LS = LS
    _frage = F.frage
    F.frage = lambda modell, text, mt: _frage("b021", text, mt)
    try:
        F.frisch_test(ausgabe, engines)
    finally:
        F.frage = _frage


def main():
    konfig_anlegen()
    if "--nur-konfig" in sys.argv:
        return
    if json.load(urllib.request.urlopen(LS + "/running", timeout=10)).get("running"):
        sys.exit("llama-swap hat ein Modell geladen, Abbruch")
    os.makedirs(AUS, exist_ok=True)
    sh(DOCKER.format(name="--name strata021-doctor") + " /opt/strata/bin/strata doctor", "doctor.txt", 300)
    sh(DOCKER.format(name="--name strata021-version") + " /opt/engine/strata --version", "engine-version.txt", 120)
    sicherung = f"{SWAP}.vor-t021-{ZEIT}"
    swap_setzen(sicherung)
    try:
        proxy = laden("b021")
        logzeilen("b021")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/strata_bench.py --url {proxy} --long --out {AUS}/strata-bench",
               "strata-bench.txt")
        sh(f"cd {MESS} && python3 bench.py --url {LS} --model b021 --label 021-b021 --out {AUS}/ "
           "--tests schreiben,einlesen,agent,qualitaet", "bench.txt")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/needle_bench.py --url {proxy} --lengths 32k,128k "
               f"--depths 10,50,90 --out {AUS}/needles-32k-128k.json", "needles-32k-128k.txt")
        logzeilen("b021")
        for schritt, f in (("paare", lambda: paare(f"{AUS}/worker.jsonl")), ("frisch", lambda: frisch(f"{AUS}/frisch.jsonl"))):
            try:
                f()
            except Exception as e:
                notiz(f"{schritt} FEHLER: {e!r}")
        proxy = laden("b021")
        if proxy:
            port = proxy.rsplit(":", 1)[1]
            sh(DOCKER.format(name="--name strata021-stdbench").replace(f"-v {RUN}:/strata/run", f"-v {RUN}:/strata/run -v {AUS}:/aus")
               + f" /opt/strata/bin/strata bench run --url http://127.0.0.1:{port} --suite standard-v1 --out /aus/standard-v1"
               " --track custom --track-notes 'prebuilt hip-rx7900 0.1.46 + control 0.1.46.2; served by serve/server.py with a hand-written "
               "run config: --pool-workers 9 --vram-reserve-mib 832 --spec 4 --kv int8 --max-context 262144, hipBLASLt table gfx1100'"
               " --background 'llama-swap proxy (idle)' --output human", "standard-v1.txt", 7200)
    finally:
        shutil.copy2(sicherung, SWAP)
        try:
            urllib.request.urlopen(LS + "/unload", timeout=180).read()
        except Exception as e:
            notiz(f"Entladen fehlgeschlagen: {e!r}")
        notiz(f"Ergebnis: {AUS} · config.yaml zurück aus {sicherung}")


if __name__ == "__main__":
    main()
