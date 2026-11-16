#!/usr/bin/env python3
"""Does the NAS keep working while the model writes? Fixed schedule from START (HH:MM, NAS time), so that a client can
start its downloads at known times:

  +0:00  stop the agent (optional), unload, serve exactly one large file over HTTP
  +1:00  transcode 3x, no model loaded (messen/transkodieren.sh)
  +2:00  drop the page cache; +2:30 the client downloads the file (download 1, no model loaded)
  +4:30  load the model and write long answers (1,500 tokens) until +12:30
  +9:00  transcode 3x while the client downloads the file again (download 2), the model keeps writing

Every request is logged with start and end, so its overlap with the side load can be assigned afterwards. The client
measures the downloads itself (e.g. curl -s -o /dev/null -w '%{speed_download}'); this script only serves the file.

  URL=http://<nas>:8090 BIND=<nas address> python3 nebenlast.py 13:30 --datei /path/to/17GB.gguf --aus nebenlast.json

Needs betrieb.py next to it (anfrage, entladen, SCHREIB) and sudo for drop_caches. Standard library only.
"""
import argparse, datetime, json, os, re, subprocess, threading, time

from betrieb import anfrage, entladen, SCHREIB

p = argparse.ArgumentParser()
p.add_argument("start"); p.add_argument("--model", default="faber"); p.add_argument("--datei", required=True)
p.add_argument("--aus", default="nebenlast.json"); p.add_argument("--port", type=int, default=8000)
p.add_argument("--www", default="nebenlast-http"); p.add_argument("--agent", default="", help="docker container to stop meanwhile")
a = p.parse_args()

TRANSK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transkodieren.sh")
h, m = map(int, a.start.split(":"))
heute = datetime.date.today()
T0 = datetime.datetime(heute.year, heute.month, heute.day, h, m).timestamp()
aus = {"gemessen": str(heute), "modell": a.model, "start": a.start, "transkodieren": {"ohne_modell": [], "waehrend_schreiben": []}, "anfragen": []}


def bis(sek):
    while time.time() < T0 + sek:
        time.sleep(0.5)


def speichern():
    json.dump(aus, open(a.aus, "w"), ensure_ascii=False, indent=1)


def transkodieren(wohin):
    for _ in range(3):
        t0 = time.time()
        r = subprocess.run(["sh", TRANSK], capture_output=True, text=True, timeout=600).stdout
        fps = re.findall(r"fps=\s*([\d.]+)", r)
        aus["transkodieren"][wohin].append({"start": round(t0 - T0, 1), "ende": round(time.time() - T0, 1), "bilder_s": float(fps[-1]) if fps else None})
        print(wohin, fps[-1] if fps else "?", flush=True)


bis(0)
srv = None
try:
    if a.agent:
        subprocess.run(["docker", "stop", "-t", "60", a.agent], capture_output=True)
    entladen()
    os.makedirs(a.www, exist_ok=True)
    link = os.path.join(a.www, os.path.basename(a.datei))
    if not os.path.exists(link):
        os.symlink(a.datei, link)
    srv = subprocess.Popen(["python3", "-m", "http.server", str(a.port), "--bind", os.environ.get("BIND", "0.0.0.0"), "--directory", a.www],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bis(60); transkodieren("ohne_modell"); speichern()
    bis(120); subprocess.run(["sudo", "-n", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"], check=True)
    bis(270)
    th = threading.Thread(target=lambda: (bis(540), transkodieren("waehrend_schreiben"), speichern()))
    th.start()
    n = 0
    while time.time() < T0 + 750:
        n += 1
        t0 = time.time()
        r = anfrage(a.model, SCHREIB.format(n), 1500)
        r.pop("text", None)
        r.update({"start": round(t0 - T0, 1), "ende": round(time.time() - T0, 1)})
        r["tps"] = round(r["neu_token"] / r["schreib_s"], 1) if r["neu_token"] and r["schreib_s"] else None
        aus["anfragen"].append(r)
        print(n, r["tps"], flush=True)
        speichern()
    th.join()
finally:
    if srv:
        srv.terminate()
    entladen()
    if a.agent:
        subprocess.run(["docker", "start", a.agent], capture_output=True)
    speichern()
