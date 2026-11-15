#!/usr/bin/env python3
"""Ein Modell, das ganz in den VRAM passt, auf vier Wegen: nur CPU, eingebaute Arc-iGPU, Dock-Karte.

Gedacht für das Modell, das UGREENs KI-Konsole selbst herunterlädt (GGUF unter /volume1/@aiconsole/models/).
Stufen:
  ugreen-werk  der Server, den UGOS selbst gestartet hat (SYCL auf der Arc-iGPU), angesprochen über seinen Unix-Socket (SOCKET)
  cpu          llama.cpp (Vulkan-Image), keine Schicht auf einer Grafikkarte
  arc-sycl     UGREENs eigener llama-server (SYCL) aus der KI-Konsole, alle Schichten auf der Arc-iGPU
  arc-vulkan   llama.cpp (Vulkan-Image), alle Schichten auf der Arc-iGPU
  xtx-vulkan   llama.cpp (Vulkan-Image), alle Schichten auf der Karte im Dock

  sudo python3 werksmodell.py --ordner /volume1/@aiconsole/models/<name> --gguf <erste-datei.gguf> \
       --stufen cpu arc-sycl xtx-vulkan --aus werksmodell.json

KARTE / ARC = PCI-Adressen der beiden Grafikkarten, SYCL = Ordner mit UGREENs llama-server. Braucht root, weil die
Dateien der KI-Konsole root gehören. Nur Standardbibliothek und docker.
"""
import argparse, glob, http.client, json, os, socket, statistics, subprocess, time, urllib.request

import betrieb, dicht70

ARC = os.environ.get("ARC", "0000:00:02.0")
SYCL = os.environ.get("SYCL", "/volume1/@aiconsole/llamacppSycl/llama-sycl/llama-sycl")
SOCKET = os.environ.get("SOCKET") or next(iter(glob.glob("/run/ugreen/llama-gw-socks/*.sock")), None)
PORT = dicht70.PORT
NAME = "werksmodell"
prozess = None


def geraete(pci):
    pfad = f"/dev/dri/by-path/pci-{pci}"
    return ["--device", os.path.realpath(pfad + "-card"), "--device", os.path.realpath(pfad + "-render")]


def stoppen():
    global prozess
    dicht70.sh("docker", "rm", "-f", NAME)
    if prozess:
        prozess.terminate()
        try:
            prozess.wait(30)
        except Exception:
            prozess.kill()
        prozess = None


def starten(stufe, ordner, gguf, faeden, kontext):
    global prozess
    stoppen()
    gemeinsam = ["-c", str(kontext), "-np", "1", "-t", str(faeden), "--port", "8080" if stufe != "arc-sycl" else str(PORT), "--jinja"]
    if stufe == "arc-sycl":
        umgebung = dict(os.environ, LD_LIBRARY_PATH=SYCL, ZES_ENABLE_SYSMAN="1")
        prozess = subprocess.Popen([os.path.join(SYCL, "llama-server"), "-m", os.path.join(ordner, gguf), "-ngl", "99", "--host", "127.0.0.1"] + gemeinsam,
                                   cwd=SYCL, env=umgebung, stdout=open("werksmodell-sycl.log", "w"), stderr=subprocess.STDOUT)
    else:
        ngl, dev = {"cpu": ("0", []), "arc-vulkan": ("99", geraete(ARC)), "xtx-vulkan": ("99", geraete(betrieb.KARTE))}[stufe]
        r = dicht70.sh("docker", "run", "-d", "--name", NAME, *dev, "--group-add", "44", "--group-add", "105", "-p", f"127.0.0.1:{PORT}:8080",
                       "-v", f"{ordner}:/models:ro", dicht70.IMAGE, "-m", f"/models/{gguf}", "-ngl", ngl, "--host", "0.0.0.0", *gemeinsam)
        if r.returncode:
            return r.stderr.strip()
    t0 = time.time()
    while time.time() - t0 < 1200:
        if prozess and prozess.poll() is not None:
            return "Server beendet: " + open("werksmodell-sycl.log").read()[-600:]
        if not prozess and dicht70.sh("docker", "inspect", "-f", "{{.State.Running}}", NAME).stdout.strip() != "true":
            return "Server beendet: " + dicht70.sh("docker", "logs", "--tail", "8", NAME).stderr[-600:]
        try:
            if json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5)).get("status") == "ok":
                return round(time.time() - t0, 1)
        except Exception:
            pass
        time.sleep(3)
    return "Zeitüberschreitung beim Laden"


class UnixVerbindung(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3600)
        self.sock.connect(SOCKET)


def frage_socket(text, max_tokens):
    """Wie dicht70.frage, aber über den Unix-Socket des von UGOS gestarteten Servers."""
    v = UnixVerbindung("localhost")
    body = json.dumps({"messages": [{"role": "user", "content": text}], "max_tokens": max_tokens, "temperature": 0.7, "cache_prompt": False})
    v.request("POST", "/v1/chat/completions", body, {"Content-Type": "application/json"})
    t = json.loads(v.getresponse().read()).get("timings", {})
    v.close()
    return {"prompt_token": t.get("prompt_n"), "einlesen_tps": round(t.get("prompt_per_second") or 0, 1),
            "neu_token": t.get("predicted_n"), "schreiben_tps": round(t.get("predicted_per_second") or 0, 2)}


def ram_frei_gib():
    for z in open("/proc/meminfo"):
        if z.startswith("MemAvailable"):
            return round(int(z.split()[1]) / 2**20, 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ordner", required=True); p.add_argument("--gguf", required=True)
    p.add_argument("--stufen", nargs="+", default=["cpu", "arc-sycl", "xtx-vulkan"])
    p.add_argument("--faeden", type=int, default=6); p.add_argument("--kontext", type=int, default=8192)
    p.add_argument("--token", type=int, default=300); p.add_argument("--aus", default="werksmodell.json")
    a = p.parse_args()
    aus = {"gguf": a.gguf, "faeden": a.faeden, "kontext": a.kontext, "beginn": time.strftime("%Y-%m-%dT%H:%M:%S"), "stufen": []}
    for name in a.stufen:
        stufe = {"stufe": name, "ram_frei_vorher_gib": ram_frei_gib()}
        werk = name == "ugreen-werk"
        frage = frage_socket if werk else dicht70.frage
        lade = 0.0 if werk else starten(name, a.ordner, a.gguf, a.faeden, a.kontext)
        if isinstance(lade, str):
            stufe["fehler"] = lade
        else:
            try:
                frage("Reply with the single word OK.", 16)  # warm
                stufe.update(laden_s=lade, vram_xtx_mib=dicht70.vram_mib(), ram_frei_geladen_gib=ram_frei_gib())
                m = betrieb.Messer(); m.start(); m.beginne("schreiben")
                laeufe = [frage(dicht70.FRAGE, a.token) for _ in range(3)]
                while time.time() - m.t0 < betrieb.VORLAUF + 45:  # schnelle Stufen: genug USV-Messpunkte sammeln
                    laeufe.append(frage(dicht70.FRAGE, a.token))
                m.an = False
                stufe["schreiben_tps"] = [l["schreiben_tps"] for l in laeufe]
                stufe["schreiben_tps_median"] = round(statistics.median(stufe["schreiben_tps"]), 2)
                stufe.update(m.werte("schreiben"))
                lang = frage(betrieb.langprompt(120), 16)
                stufe["einlesen"] = {"prompt_token": lang["prompt_token"], "tps": lang["einlesen_tps"]}
                stufe["wh_je_1000_token_gesamt"] = betrieb.wh_je_1000(stufe.get("usv_w", {}).get("mittel"), stufe["schreiben_tps_median"])
            except Exception as e:
                stufe["fehler"] = f"{type(e).__name__}: {e}"
        if not werk:
            stoppen()
        aus["stufen"].append(stufe)
        print(json.dumps(stufe), flush=True)
        json.dump(aus, open(a.aus, "w"), indent=1)
        time.sleep(20)


if __name__ == "__main__":
    main()
