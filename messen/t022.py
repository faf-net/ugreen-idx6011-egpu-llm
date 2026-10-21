#!/usr/bin/env python3
"""Strata 0.2.2 (Engine-Paket 0.1.47 hip-rx7900, Control 0.1.47) auf der RX 7900 XTX — 21.10.2026.

Vergleich gegen die Produktion seit heute früh (0.2.1, Engine 0.1.46, Control 0.1.46.2). Beide Varianten laufen mit
derselben Konfiguration wie arbeit (/volume1/docker/strata-prod/ls-arbeit.json), nur Engine und Control sind getauscht.

  python3 t022.py --nur-konfig     Konfigurationen unter /volume1/docker/strata-022/run/ anlegen
  python3 t022.py                  ganzer Lauf (nur wenn llama-swap /running leer ist)

Schritte: strata doctor · b022 mit strata_bench --long, bench.py, needle_bench 32k/128k · Paare b022 gegen p021 ·
acht frische Engines b022 · strata bench run --suite standard-v1 aus dem Paket (0.2.2 hat COMMIT) ·
danach das Docker-Image 0.2.2-rocm-gfx110x mit Voreinstellungen (--track default).
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request

LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")
SWAP = "/volume1/docker/llama-swap/config.yaml"
BASIS = "/volume1/docker/strata-022"
RUN = f"{BASIS}/run"
PROD = "/volume1/docker/strata-test"
P021 = "/volume1/docker/strata-prod/0.2.1"
MESS = "/volume1/docker/ki-messung"
ZEIT = time.strftime("%Y%m%d-%H%M")
AUS = f"{MESS}/ergebnisse/t022-{ZEIT}"
IMAGE = "ghcr.io/niko1221/strata:0.2.2-rocm-gfx110x"
DDATA = "/volume1/docker/strata-021/docker-data"
DKEY = "/volume1/docker/strata-021/docker-key"


def docker(ver, name):
    return (f"docker run --rm {name} --network host --device /dev/kfd --device /dev/dri --group-add 44 --group-add 105 "
            "--security-opt seccomp=unconfined --ipc host --ulimit memlock=-1 --ulimit stack=67108864 "
            f"-v {PROD}:/strata -v {ver}/engine:/opt/engine -v {ver}/control:/opt/strata -v {RUN}:/t022 "
            "-e STRATA_ENGINE=/opt/engine/strata -w /opt/strata strata-hip:296b59d")


VARIANTEN = {"b022": ("strata022", BASIS), "p021": ("strata021t", P021)}
MAKROS = "".join(f"  {m}: >-\n    " + docker(v, "--name ls-${MODEL_ID}") +
                 "\n    /opt/strata/python/bin/python3 serve/server.py --engine strata --port ${PORT} --config\n"
                 for m, v in VARIANTEN.values())
MODELLE = list(VARIANTEN)


def konfig_anlegen():
    os.makedirs(RUN, exist_ok=True)
    basis = json.load(open("/volume1/docker/strata-prod/ls-arbeit.json"))
    for name in MODELLE:
        cfg = json.loads(json.dumps(basis))
        cfg.update(model_name=name, log=f"/t022/{name}.log")
        json.dump(cfg, open(f"{RUN}/{name}.json", "w"), indent=1)
    print("Konfigurationen:", MODELLE, flush=True)


def eintraege():
    return "".join(f"""  {m}:
    name: "Test Strata {m}"
    cmd: ${{{VARIANTEN[m][0]}}} /t022/{m}.json
    cmdStop: docker stop -t 80 ls-${{MODEL_ID}}
    proxy: http://127.0.0.1:${{PORT}}
    checkEndpoint: /health
    ttl: 7200

""" for m in MODELLE)


def swap_setzen(sicherung):
    shutil.copy2(SWAP, sicherung)
    t = open(SWAP).read().replace("macros:\n", "macros:\n" + MAKROS, 1).replace("\n  frei:\n", "\n" + eintraege() + "  frei:\n", 1)
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


def logzeilen(modell, muster=r"pool|worker|VRAM free|hipblaslt|tuning|error|warn|version|NUMA|core|slots|MTP|draft|session is up"):
    try:
        z = [l.rstrip() for l in open(f"{RUN}/{modell}.log", errors="replace") if re.search(muster, l, re.I)]
    except OSError as e:
        z = [repr(e)]
    open(f"{AUS}/log-{modell}.txt", "w").write("\n".join(z[:250]) + "\n")
    return z


def paare(ausgabe, n=3):
    """Wie t021: je Engine Aufwärmen, dann zwei gemessene Antworten; b022 und p021 verschränkt."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import folgetests as F
    F.LS = LS
    for paar in range(1, n + 1):
        for modell in ("b022", "p021"):
            laden(modell)
            F.frage(modell, F.GESCHICHTE, 900)
            for i in (1, 2):
                F.schreiben(ausgabe, {"test": "version", "variante": modell, "paar": paar, "messung": i,
                                      **F.frage(modell, f"Lauf {time.time_ns()}. " + F.GESCHICHTE, 900)})
            logzeilen(modell)


def frisch(ausgabe, engines=8):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import folgetests as F
    F.LS = LS
    _frage = F.frage
    F.frage = lambda modell, text, mt: _frage("b022", text, mt)
    try:
        F.frisch_test(ausgabe, engines)
    finally:
        F.frage = _frage


def image_test():
    """Docker-Image 0.2.2 mit MODEL=IQ3_XXS und API_KEY, Standardlauf --track default im Container."""
    name = "strata022-docker"
    sh(f"docker pull -q {IMAGE}", "image-pull.txt", 1800)
    sh(f"docker run -d --name {name} --device /dev/kfd --device /dev/dri --group-add 44 --group-add 105 "
       f"-p 127.0.0.1:18180:8080 --ulimit memlock=-1:-1 --shm-size 2g --stop-timeout 120 -v {DDATA}:/data "
       f"-e MODEL=IQ3_XXS -e API_KEY=$(cat {DKEY}) {IMAGE}", "image-start.txt", 300)
    try:
        bereit = False
        for _ in range(120):
            time.sleep(10)
            log = subprocess.run(f"docker logs {name} 2>&1", shell=True, capture_output=True, text=True).stdout
            if "Strata is serving" in log:
                bereit = True
                break
            if "stopped with code" in log or subprocess.run(f"docker inspect {name}", shell=True, capture_output=True).returncode:
                break
        notiz(f"Image bereit: {bereit}")
        if bereit:
            sh(f"docker exec -e STRATA_API_KEY=$(cat {DKEY}) {name} strata bench run --url http://127.0.0.1:8080 "
               "--suite standard-v1 --track default --track-notes 'unchanged image, MODEL=IQ3_XXS and API_KEY only' "
               "--out /data/std022-default --output human", "image-standard-v1.txt", 7200)
    finally:
        subprocess.run(f"docker logs {name} > {AUS}/image-container.log 2>&1", shell=True)
        subprocess.run(f"docker exec {name} sh -c 'cat /data/state/strata/launch/docker.engine.log' > {AUS}/image-engine.log 2>&1",
                       shell=True)
        subprocess.run(f"docker stop -t 120 {name}; docker rm -f {name}", shell=True, capture_output=True)
        subprocess.run(f"cp -a {DDATA}/std022-default {AUS}/ 2>/dev/null; cp -a {DDATA}/install/*.json {AUS}/ 2>/dev/null", shell=True)


def main():
    konfig_anlegen()
    if "--nur-konfig" in sys.argv:
        return
    if json.load(urllib.request.urlopen(LS + "/running", timeout=10)).get("running"):
        sys.exit("llama-swap hat ein Modell geladen, Abbruch")
    os.makedirs(AUS, exist_ok=True)
    sh(docker(BASIS, "--name strata022-doctor") + " /opt/strata/bin/strata doctor", "doctor.txt", 300)
    sh(docker(BASIS, "--name strata022-version") + " /opt/engine/strata --version", "engine-version.txt", 120)
    sicherung = f"{SWAP}.vor-t022-{ZEIT}"
    swap_setzen(sicherung)
    try:
        proxy = laden("b022")
        logzeilen("b022")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/strata_bench.py --url {proxy} --long --out {AUS}/strata-bench",
               "strata-bench.txt")
        sh(f"cd {MESS} && python3 bench.py --url {LS} --model b022 --label 022-b022 --out {AUS}/ "
           "--tests schreiben,einlesen,agent,qualitaet", "bench.txt")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/needle_bench.py --url {proxy} --lengths 32k,128k "
               f"--depths 10,50,90 --out {AUS}/needles-32k-128k.json", "needles-32k-128k.txt")
        logzeilen("b022")
        for schritt, f in (("paare", lambda: paare(f"{AUS}/version.jsonl")), ("frisch", lambda: frisch(f"{AUS}/frisch.jsonl"))):
            try:
                f()
            except Exception as e:
                notiz(f"{schritt} FEHLER: {e!r}")
        proxy = laden("b022")
        if proxy:
            port = proxy.rsplit(":", 1)[1]
            sh(docker(BASIS, "--name strata022-stdbench").replace(f"-v {RUN}:/t022", f"-v {RUN}:/t022 -v {AUS}:/aus")
               + f" /opt/strata/bin/strata bench run --url http://127.0.0.1:{port} --suite standard-v1 --out /aus/standard-v1"
               " --track custom --track-notes 'prebuilt hip-rx7900 0.1.47 + control 0.1.47; served by serve/server.py with a hand-written "
               "run config: default pool workers, --vram-reserve-mib 832 --spec 4 --kv int8 --max-context 262144, hipBLASLt table gfx1100'"
               " --background 'llama-swap proxy (idle)' --output human", "standard-v1.txt", 7200)
        logzeilen("b022")
    finally:
        shutil.copy2(sicherung, SWAP)
        try:
            urllib.request.urlopen(LS + "/unload", timeout=180).read()
        except Exception as e:
            notiz(f"Entladen fehlgeschlagen: {e!r}")
        notiz(f"config.yaml zurück aus {sicherung}")
    if "--ohne-image" not in sys.argv:
        time.sleep(10)
        try:
            image_test()
        except Exception as e:
            notiz(f"image FEHLER: {e!r}")
    notiz(f"Ergebnis: {AUS}")


if __name__ == "__main__":
    main()
