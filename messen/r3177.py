#!/usr/bin/env python3
"""Nachstellen von Strata-Issue #3177 (19.10.2026): MTP-Verify-Timeout bei einer Agentenanfrage mit ~54K Token auf einer
einzelnen RX 7900 XTX. Konfiguration wie beim Melder: IQ3_S, --spec 2, --prefill auto:32768, 262K, int8-KV.

Läuft auf der iDX:  python3 r3177.py            (nur, wenn llama-swap /running leer ist)
                    python3 r3177.py --nur-konfig

Varianten: c045-mtp (Image strata-hip:v0.1.45, MTP an) · c045-ohne (MTP-Kopf weg, --spec 2 bleibt) · c044-mtp (unser
Baum 296b59d, Engine 0.1.44.1). Die Einträge stehen nur während des Laufs in llama-swap, config.yaml wird danach
zurückgesetzt. Ergebnis: /volume1/docker/ki-messung/ergebnisse/r3177-<zeit>.jsonl
"""
import json, os, re, shutil, sys, time, urllib.error, urllib.request

LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")   # llama-swap
TEST = "/volume1/docker/strata-test"
HIER = f"{TEST}/r3177"
SWAP = "/volume1/docker/llama-swap/config.yaml"
ERGEBNISSE = "/volume1/docker/ki-messung/ergebnisse"
QUELLE = f"{TEST}/src/serve/server.py"          # Strata-Quelltext als Inhalt der Werkzeug-Antworten
ZIEL_ZEICHEN = 212_000                          # ~54K Token Code (gemessen: 43.450 Token bei 168.000 Zeichen)
LAEUFE = [("c045-mtp", 3), ("c045-ohne", 1), ("c044-mtp", 2)]

MAKRO = """  strata045: >-
    docker run --rm --name ls-${MODEL_ID} --network host
    --device /dev/kfd --device /dev/dri --group-add 44 --group-add 105
    --security-opt seccomp=unconfined --ipc host --ulimit memlock=-1 --ulimit stack=67108864
    -v /volume1/docker/strata-test/data:/strata/data -v /volume1/docker/strata-test/r3177:/strata/r3177
    -w /strata/src strata-hip:v0.1.45
    /strata/src/.venv/bin/python serve/server.py --engine strata --port ${PORT} --config
"""


def eintrag(name, makro):
    return f"""  {name}:
    name: "Test #3177 {name}"
    cmd: ${{{makro}}} /strata/r3177/{name}.json
    cmdStop: docker stop -t 80 ls-${{MODEL_ID}}
    proxy: http://127.0.0.1:${{PORT}}
    checkEndpoint: /health
    ttl: 600
"""


def konfig_anlegen():
    basis = json.load(open(f"{TEST}/src/strata-iq3_s.json"))
    a = basis["args"]
    a[a.index("--spec") + 1] = "2"
    a[a.index("--prefill") + 1] = "auto:32768"
    a[a.index("--max-context") + 1] = "262144"
    a += ["--pool-workers", "9"]                 # auf dieser CPU sonst 27 % langsamer; berührt den Verify-Pfad nicht
    for name in ("c045-mtp", "c045-ohne", "c044-mtp"):
        cfg = json.loads(json.dumps(basis))
        if name == "c045-ohne":
            i = cfg["args"].index("--mtp")
            del cfg["args"][i:i + 2]
        cfg.pop("port", None)
        cfg.update(model_name=name, log=f"/strata/r3177/{name}.log", open_browser=False)
        with open(f"{HIER}/{name}.json", "w") as f:
            json.dump(cfg, f, indent=1)
    print("Konfigurationen:", sorted(os.listdir(HIER)))


def swap_setzen(sicherung):
    shutil.copy2(SWAP, sicherung)
    t = open(SWAP).read()
    t = t.replace("macros:\n", "macros:\n" + MAKRO, 1)
    neu = eintrag("c045-mtp", "strata045") + eintrag("c045-ohne", "strata045") + eintrag("c044-mtp", "strata")
    t = t.replace("\n  frei:\n", "\n" + neu + "\n  frei:\n", 1)
    open(SWAP, "w").write(t)
    for _ in range(30):
        time.sleep(1)
        try:
            ids = {m["id"] for m in json.load(urllib.request.urlopen(LS + "/v1/models", timeout=10))["data"]}
            if {"c045-mtp", "c045-ohne", "c044-mtp"} <= ids:
                return
        except Exception:
            pass
    sys.exit("Testeinträge erscheinen nicht in /v1/models")


WERKZEUGE = [{"type": "function", "function": {"name": n, "description": d, "parameters": {
    "type": "object", "properties": {k: {"type": "string"} for k in p}, "required": p}}}
    for n, d, p in [("read_file", "Read a file of the repository", ["path"]),
                    ("search", "Search the repository with a regular expression", ["pattern"]),
                    ("run_shell", "Run a shell command in the repository", ["command"]),
                    ("write_file", "Write a file", ["path", "content"]),
                    ("list_dir", "List a directory", ["path"])]]


def agentenanfrage(kennung):
    text = open(QUELLE, errors="replace").read()
    stuecke = [text[i:i + 12_000] for i in range(0, min(len(text), ZIEL_ZEICHEN), 12_000)]
    msgs = [{"role": "system", "content": f"Session {kennung}. You are a careful coding agent working in the Strata "
             "repository. Use the tools to inspect code before answering."},
            {"role": "user", "content": "Review serve/server.py. Read it in parts, then tell me the three riskiest "
             "places for a hang on long requests."}]
    for i, s in enumerate(stuecke):
        cid = f"call_{i}"
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"id": cid, "type": "function", "function": {
            "name": "read_file", "arguments": json.dumps({"path": f"serve/server.py#part{i + 1}"})}}]})
        msgs.append({"role": "tool", "tool_call_id": cid, "content": s})
    msgs.append({"role": "user", "content": "You have read enough. Write the review now: for each of the three places "
                 "quote the code, explain the hang scenario step by step and propose a concrete patch."})
    return msgs


def lauf(modell, nr, ausgabe):
    body = {"model": modell, "messages": agentenanfrage(time.time_ns()), "tools": WERKZEUGE,
            "max_tokens": 2500, "temperature": 0.6,
            "tool_choice": "none"}      # sonst ruft das Modell nach ~200 Token ein Werkzeug auf (gemessen)
    z = {"variante": modell, "lauf": nr, "start": time.strftime("%H:%M:%S")}
    t0 = time.time()
    try:
        req = urllib.request.Request(LS + "/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1200) as r:
            d = json.load(r)
        t = d.get("timings", {})
        z.update(status=200, prompt_token=d["usage"]["prompt_tokens"], neu_token=d["usage"]["completion_tokens"],
                 ende=d["choices"][0].get("finish_reason"), prompt_tps=t.get("prompt_per_second"),
                 decode_tps=t.get("predicted_per_second"), draft_n=t.get("draft_n"), draft_ok=t.get("draft_n_accepted"))
    except urllib.error.HTTPError as e:
        z.update(status=e.code, fehler=e.read()[:400].decode(errors="replace"))
    except Exception as e:
        z.update(status=None, fehler=repr(e)[:400])
    z["sekunden"] = round(time.time() - t0, 1)
    try:
        log = open(f"{HIER}/{modell}.log", errors="replace").read()
        z["log_verify_timeout"] = len(re.findall(r"timed out at layer|Unrecoverable native verification", log))
        z["log_engine_exit"] = len(re.findall(r"engine (?:exited|stopped)|exit code", log, re.I))
    except OSError:
        pass
    print(json.dumps(z, ensure_ascii=False), flush=True)
    with open(ausgabe, "a") as f:
        f.write(json.dumps(z, ensure_ascii=False) + "\n")


def main():
    os.makedirs(HIER, exist_ok=True)
    konfig_anlegen()
    if "--nur-konfig" in sys.argv:
        return
    laeuft = json.load(urllib.request.urlopen(LS + "/running", timeout=10)).get("running") or []
    if laeuft:
        sys.exit(f"llama-swap hat ein Modell geladen ({laeuft}), Abbruch")
    zeit = time.strftime("%Y%m%d-%H%M")
    sicherung = f"{SWAP}.vor-r3177-{zeit}"
    ausgabe = f"{ERGEBNISSE}/r3177-{zeit}.jsonl"
    swap_setzen(sicherung)
    try:
        for modell, n in LAEUFE:
            for i in range(n):
                lauf(modell, i + 1, ausgabe)
    finally:
        shutil.copy2(sicherung, SWAP)
        try:
            urllib.request.urlopen(LS + "/unload", timeout=180).read()
        except Exception as e:
            print("Entladen fehlgeschlagen:", repr(e))
        print(f"Ergebnis: {ausgabe} · config.yaml zurück aus {sicherung}", flush=True)


if __name__ == "__main__":
    main()
