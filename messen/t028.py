#!/usr/bin/env python3
"""Strata 0.2.8 (Engine-Paket 0.1.54 hip-rx7900, Control 0.1.54) auf der RX 7900 XTX — 31.10.2026.

Für den Bericht an Strata (Nachtrag zu PR #2904). Vergleich gegen 0.2.3.1 (Engine 0.1.48, Control 0.1.48.1).
Beide Varianten laufen mit derselben Konfiguration wie faber (/volume1/docker/strata-prod/ls-faber.json),
nur Engine und Control sind getauscht. Unnötige Dienste der iDX sind vorher gestoppt (siehe HINTERGRUND).

  python3 t028.py --nur-konfig     Konfigurationen unter /volume1/docker/strata-028/run/ anlegen
  python3 t028.py                  ganzer Lauf (nur wenn llama-swap /running leer ist)

Schritte: strata doctor · b028 frisch geladen: strata bench run --suite standard-v1 (zuerst, Protokoll) ·
strata_bench --long, bench.py, needle_bench 32k/128k und 250k · Tool-Calls b028 und p0231 ·
Paare b028 gegen p0231 · acht frische Engines b028 · danach das Docker-Image 0.2.8-rocm-gfx110x (--track default).
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request

LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")
SWAP = "/volume1/docker/llama-swap/config.yaml"
BASIS = "/volume1/docker/strata-028"
RUN = f"{BASIS}/run"
PROD = "/volume1/docker/strata-test"
B028 = "/volume1/docker/strata-prod/0.2.8"
P0231 = "/volume1/docker/strata-prod/0.2.3.1"
MESS = "/volume1/docker/ki-messung"
ZEIT = time.strftime("%Y%m%d-%H%M")
AUS = f"{MESS}/ergebnisse/t028-{ZEIT}"
IMAGE = "ghcr.io/niko1221/strata:0.2.8-rocm-gfx110x"
DDATA = "/volume1/docker/strata-021/docker-data"
DKEY = "/volume1/docker/strata-021/docker-key"
HINTERGRUND = ["llama-swap proxy (idle, no other model loaded)",
               "NAS services stopped for the run: photo library, media server, agent, search, mail bridge, file sync",
               "still running: reverse tunnel, three small MCP servers, container agent (all idle)"]


def docker(ver, name):
    return (f"docker run --rm {name} --network host --device /dev/kfd --device /dev/dri --group-add 44 --group-add 105 "
            "--security-opt seccomp=unconfined --ipc host --ulimit memlock=-1 --ulimit stack=67108864 "
            f"-v {PROD}:/strata -v /volume1/docker/strata-prod:/strata-prod -v {ver}/engine:/opt/engine "
            f"-v {ver}/control:/opt/strata -v {RUN}:/t028 "
            "-e STRATA_ENGINE=/opt/engine/strata -w /opt/strata strata-hip:296b59d")


VARIANTEN = {"b028": ("strata028t", B028), "p0231": ("strata0231t", P0231)}
MAKROS = "".join(f"  {m}: >-\n    " + docker(v, "--name ls-${MODEL_ID}") +
                 "\n    /opt/strata/python/bin/python3 serve/server.py --engine strata --port ${PORT} --config\n"
                 for m, v in VARIANTEN.values())
MODELLE = list(VARIANTEN)

WERKZEUGE = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file from the project",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command and return its output",
     "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout_s": {"type": "integer"}},
                    "required": ["command"]}}},
    {"type": "function", "function": {"name": "search_web", "description": "Search the web",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}},
                    "required": ["query"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write a text file",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"]}}},
]
AUFGABEN = [
    ("read_file", "Open the file src/main.py and tell me what it does."),
    ("run_command", "Check how much disk space is free on this machine."),
    ("search_web", "Find the release date of Linux 6.18."),
    ("write_file", 'Create notes/todo.md containing the line "- buy milk" and a second line "- call Anna \\"tomorrow\\"".'),
    ("run_command", "List the running Docker containers, with a timeout of 30 seconds."),
    ("read_file", "Read the configuration in config/app.yaml."),
    ("search_web", "Look up three recent articles about RDNA3 matrix cores, at most three results."),
    ("write_file", 'Write a JSON file out/result.json with {"ok": true, "items": [1, 2, 3]}.'),
    ("run_command", "Show the last 20 lines of /var/log/syslog."),
    ("read_file", "What is in the README.md at the project root? Read it first."),
]


def konfig_anlegen():
    os.makedirs(RUN, exist_ok=True)
    basis = json.load(open("/volume1/docker/strata-prod/ls-faber.json"))
    for name in MODELLE:
        cfg = json.loads(json.dumps(basis))
        cfg.update(model_name=name, log=f"/t028/{name}.log")
        json.dump(cfg, open(f"{RUN}/{name}.json", "w"), indent=1)
    print("Konfigurationen:", MODELLE, flush=True)


def eintraege():
    return "".join(f"""  {m}:
    name: "Test Strata {m}"
    cmd: ${{{VARIANTEN[m][0]}}} /t028/{m}.json
    cmdStop: docker stop -t 80 ls-${{MODEL_ID}}
    proxy: http://127.0.0.1:${{PORT}}
    checkEndpoint: /health
    ttl: 7200

""" for m in MODELLE)


def swap_setzen(sicherung):
    shutil.copy2(SWAP, sicherung)
    t = open(SWAP).read()
    assert "macros:\n" in t and "\n  frei:\n" in t, "Einfügestellen fehlen"
    t = t.replace("macros:\n", "macros:\n" + MAKROS, 1).replace("\n  frei:\n", "\n" + eintraege() + "  frei:\n", 1)
    open(SWAP, "w").write(t)
    for _ in range(30):
        time.sleep(1)
        try:
            if set(MODELLE) <= {m["id"] for m in json.load(urllib.request.urlopen(LS + "/v1/models", timeout=10))["data"]}:
                return
        except Exception:
            pass
    sys.exit("Testeinträge erscheinen nicht in /v1/models")


def anfrage(body, timeout=1200):
    req = urllib.request.Request(LS + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d, round(time.time() - t0, 1)


def frage(modell, inhalt, max_tokens=8, timeout=1200):
    return anfrage({"model": modell, "messages": [{"role": "user", "content": inhalt}], "max_tokens": max_tokens,
                    "temperature": 0, "reasoning_effort": "none"}, timeout)


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


def logzeilen(modell, muster=r"pool|worker|VRAM free|hipblaslt|tuning|error|warn|version|NUMA|core|slots|MTP|draft|session is up|tool"):
    try:
        z = [l.rstrip() for l in open(f"{RUN}/{modell}.log", errors="replace") if re.search(muster, l, re.I)]
    except OSError as e:
        z = [repr(e)]
    open(f"{AUS}/log-{modell}.txt", "w").write("\n".join(z[-400:]) + "\n")
    return z


def standard_v1(proxy):
    port = proxy.rsplit(":", 1)[1]
    bg = " ".join(f"--background '{b}'" for b in HINTERGRUND)
    sh(docker(B028, "--name strata028-stdbench").replace(f"-v {RUN}:/t028", f"-v {RUN}:/t028 -v {AUS}:/aus")
       + f" /opt/strata/bin/strata bench run --url http://127.0.0.1:{port} --suite standard-v1 --out /aus/standard-v1"
       " --track custom --track-notes 'prebuilt hip-rx7900 0.1.54 + control 0.1.54; served by serve/server.py with a hand-written "
       "run config: default pool workers, --vram-reserve-mib 832 --spec 4 --kv int8 --max-context 262144 --kv-resident 32768, "
       "conversation cache 9216 MiB x4, hipBLASLt table gfx1100'"
       f" {bg} --output human", "standard-v1.txt", 7200)


def werkzeuge(modell, ausgabe):
    """Zehn Aufgaben mit vier deklarierten Werkzeugen, Denken an (Voreinstellung des Modells), je eine frische Unterhaltung."""
    laden(modell)
    for i, (soll, text) in enumerate(AUFGABEN, 1):
        z = {"test": "tool-call", "variante": modell, "nr": i, "soll": soll}
        try:
            d, s = anfrage({"model": modell, "tools": WERKZEUGE, "max_tokens": 3000, "temperature": 0,
                            "messages": [{"role": "system", "content": f"Run {time.time_ns()}. You are a coding agent. Use a tool."},
                                         {"role": "user", "content": text}]})
            m = d["choices"][0]["message"]
            calls = m.get("tool_calls") or []
            args_ok = []
            for c in calls:
                try:
                    json.loads(c["function"]["arguments"])
                    args_ok.append(True)
                except Exception:
                    args_ok.append(False)
            z.update(sekunden=s, finish=d["choices"][0].get("finish_reason"), aufrufe=[c["function"]["name"] for c in calls],
                     argumente=[c["function"]["arguments"] for c in calls], argumente_json=args_ok,
                     richtig=bool(calls) and calls[0]["function"]["name"] == soll and all(args_ok),
                     text=(m.get("content") or "")[:300], usage=d.get("usage"))
        except Exception as e:
            z.update(fehler=repr(e), richtig=False)
        with open(ausgabe, "a") as f:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
    logzeilen(modell)
    n = sum(json.loads(l)["richtig"] for l in open(ausgabe) if json.loads(l)["variante"] == modell)
    notiz(f"Tool-Calls {modell}: {n}/{len(AUFGABEN)} richtig")


def paare(ausgabe, n=3):
    """Wie t0231: je Engine Aufwärmen, dann zwei gemessene Antworten; b028 und p0231 verschränkt."""
    sys.path.insert(0, "/volume1/docker/strata-test/r3177")
    import folgetests as F
    F.LS = LS
    for paar in range(1, n + 1):
        for modell in ("b028", "p0231"):
            laden(modell)
            F.frage(modell, F.GESCHICHTE, 900)
            for i in (1, 2):
                F.schreiben(ausgabe, {"test": "version", "variante": modell, "paar": paar, "messung": i,
                                      **F.frage(modell, f"Lauf {time.time_ns()}. " + F.GESCHICHTE, 900)})
            logzeilen(modell)


def frisch(ausgabe, engines=8):
    sys.path.insert(0, "/volume1/docker/strata-test/r3177")
    import folgetests as F
    F.LS = LS
    _frage = F.frage
    F.frage = lambda modell, text, mt: _frage("b028", text, mt)
    try:
        F.frisch_test(ausgabe, engines)
    finally:
        F.frage = _frage


def image_test():
    """Docker-Image 0.2.8 mit MODEL=IQ3_XXS und API_KEY, Standardlauf --track default im Container."""
    name = "strata028-docker"
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
            bg = " ".join(f"--background '{b}'" for b in HINTERGRUND[1:])
            sh(f"docker exec -e STRATA_API_KEY=$(cat {DKEY}) {name} strata bench run --url http://127.0.0.1:8080 "
               "--suite standard-v1 --track default --track-notes 'unchanged image, MODEL=IQ3_XXS and API_KEY only' "
               f"{bg} --out /data/std028-default --output human", "image-standard-v1.txt", 7200)
    finally:
        subprocess.run(f"docker logs {name} > {AUS}/image-container.log 2>&1", shell=True)
        subprocess.run(f"docker exec {name} sh -c 'cat /data/state/strata/launch/docker.engine.log' > {AUS}/image-engine.log 2>&1",
                       shell=True)
        subprocess.run(f"docker stop -t 120 {name}; docker rm -f {name}", shell=True, capture_output=True)
        subprocess.run(f"sudo cp -a {DDATA}/std028-default {AUS}/ 2>/dev/null; cp -a {DDATA}/install/*.json {AUS}/ 2>/dev/null; "
                       f"sudo chown -R $(id -u) {AUS}", shell=True)


def main():
    konfig_anlegen()
    if "--nur-konfig" in sys.argv:
        return
    if json.load(urllib.request.urlopen(LS + "/running", timeout=10)).get("running"):
        sys.exit("llama-swap hat ein Modell geladen, Abbruch")
    os.makedirs(AUS, exist_ok=True)
    sh("docker ps --format '{{.Names}}\t{{.Status}}'; echo; free -m; echo; uptime", "hintergrund.txt", 60)
    sh(docker(B028, "--name strata028-doctor") + " /opt/strata/bin/strata doctor", "doctor.txt", 300)
    sh(docker(B028, "--name strata028-version") + " /opt/engine/strata --version", "engine-version.txt", 120)
    sicherung = f"{SWAP}.vor-t028-{ZEIT}"
    swap_setzen(sicherung)
    try:
        proxy = laden("b028")
        if proxy:
            standard_v1(proxy)
        logzeilen("b028")
        proxy = laden("b028")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/strata_bench.py --url {proxy} --long --out {AUS}/strata-bench",
               "strata-bench.txt")
        sh(f"cd {MESS} && python3 bench.py --url {LS} --model b028 --label 028-b028 --out {AUS}/ "
           "--tests schreiben,einlesen,agent,qualitaet", "bench.txt")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/needle_bench.py --url {proxy} --lengths 32k,128k "
               f"--depths 10,50,90 --out {AUS}/needles-32k-128k.json", "needles-32k-128k.txt")
        proxy = laden("b028")
        if proxy:
            sh(f"cd {PROD}/src && .venv/bin/python tools/needle_bench.py --url {proxy} --lengths 250k "
               f"--depths 10,50,90 --timeout 1800 --out {AUS}/needles-250k.json", "needles-250k.txt", 7200)
        logzeilen("b028")
        for schritt, f in (("werkzeuge-b028", lambda: werkzeuge("b028", f"{AUS}/tool-calls.jsonl")),
                           ("werkzeuge-p0231", lambda: werkzeuge("p0231", f"{AUS}/tool-calls.jsonl")),
                           ("paare", lambda: paare(f"{AUS}/version.jsonl")),
                           ("frisch", lambda: frisch(f"{AUS}/frisch.jsonl"))):
            try:
                f()
            except Exception as e:
                notiz(f"{schritt} FEHLER: {e!r}")
    finally:
        shutil.copy2(sicherung, SWAP)
        try:
            urllib.request.urlopen(LS + "/unload", timeout=180).read()
        except Exception as e:
            notiz(f"Entladen fehlgeschlagen: {e!r}")
        notiz(f"config.yaml zurück aus {sicherung}")
        subprocess.run(f"sudo chown -R $(id -u) {AUS}", shell=True)
    if "--ohne-image" not in sys.argv:
        time.sleep(10)
        try:
            image_test()
        except Exception as e:
            notiz(f"image FEHLER: {e!r}")
    notiz(f"Ergebnis: {AUS}")


if __name__ == "__main__":
    main()
