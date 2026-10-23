#!/usr/bin/env python3
"""128K-Gegentest (23.10.2026): erster 128K-Prompt auf frischer Engine, 0.2.3.1 (faber) gegen 0.2.2 (p022t),
gleiche Laufkonfiguration ls-faber.json, im Wechsel, je 2 Mal. Anlass: t0231 brauchte 217 s statt ~108 s."""
import json, os, shutil, subprocess, time, urllib.request
LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")
SWAP = "/volume1/docker/llama-swap/config.yaml"
PROD = "/volume1/docker/strata-prod"
AUS = "/volume1/docker/ki-messung/ergebnisse/t128-20261023"
os.makedirs(AUS, exist_ok=True)
cfg = json.load(open(f"{PROD}/ls-faber.json")); cfg.update(model_name="p022t", log="/strata-prod/ls-p022t.log")
json.dump(cfg, open(f"{PROD}/ls-p022t.json", "w"), indent=1)
sich = SWAP + ".vor-t128-20261023"
shutil.copy2(SWAP, sich)
eintrag = """  p022t:
    name: "Test 0.2.2 mit faber-Konfiguration"
    cmd: ${strata022} /strata-prod/ls-p022t.json
    cmdStop: docker stop -t 80 ls-${MODEL_ID}
    proxy: http://127.0.0.1:${PORT}
    checkEndpoint: /health
    ttl: 3600
    unlisted: true

"""
t = open(SWAP).read(); open(SWAP, "w").write(t.replace("\n  frei:\n", "\n" + eintrag + "  frei:\n", 1))
time.sleep(5)
def laden(m):
    urllib.request.urlopen(LS + "/unload", timeout=180).read(); time.sleep(3)
    b = json.dumps({"model": m, "messages": [{"role": "user", "content": "OK"}], "max_tokens": 4, "reasoning_effort": "none"}).encode()
    urllib.request.urlopen(urllib.request.Request(LS + "/v1/chat/completions", b, {"Content-Type": "application/json"}), timeout=600).read()
    return next(r["proxy"] for r in json.load(urllib.request.urlopen(LS + "/running"))["running"] if r["model"] == m)
try:
    for runde in (1, 2):
        for m in ("faber", "p022t"):
            proxy = laden(m)
            out = f"{AUS}/{m}-{runde}.json"
            subprocess.run(f"cd /volume1/docker/strata-test/src && .venv/bin/python tools/needle_bench.py --url {proxy} --lengths 128k --depths 10 --out {out}",
                           shell=True, stdout=open(out + ".txt", "w"), stderr=subprocess.STDOUT, timeout=1800)
            r = json.load(open(out))[0]
            print(f"{time.strftime('%H:%M:%S')} {m} Runde {runde}: {r['seconds']} s, gefunden {r['found']}", flush=True)
finally:
    shutil.copy2(sich, SWAP)
    try: urllib.request.urlopen(LS + "/unload", timeout=180).read()
    except Exception: pass
    os.remove(f"{PROD}/ls-p022t.json")
    print("config.yaml zurück", flush=True)
