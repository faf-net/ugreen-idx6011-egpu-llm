#!/usr/bin/env python3
"""Ein dichtes Modell, das nicht ganz in den VRAM passt, mit llama.cpp (Vulkan) vermessen.

Startet den Server je Stufe neu mit einer anderen Zahl von Schichten auf der Karte (-ngl), misst Schreiben und
Einlesen aus den Zeitangaben des Servers und liest dabei USV- und Kartenleistung mit.

  python3 dicht70.py --gguf Llama-3.3-70B-Instruct-Q4_K_M.gguf --ngl 42 40 38 0 --aus dicht70.json

MODELLE = Ordner mit der GGUF-Datei, KARTE = PCI-Adresse der Karte, USV = NUT-Name. Nur Standardbibliothek und docker.
"""
import argparse, json, os, statistics, subprocess, threading, time, urllib.request

import betrieb

MODELLE = os.environ.get("MODELLE", "/models")
PORT = int(os.environ.get("PORT", "8199"))
IMAGE = "ghcr.io/ggml-org/llama.cpp:server-vulkan"
NAME = "dicht70"
FRAGE = "Write a detailed, factual essay of about 400 words on the history of lighthouses in Europe."


def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)


def starten(gguf, ngl, faeden, kontext):
    sh("docker", "rm", "-f", NAME)
    pfad = f"/dev/dri/by-path/pci-{betrieb.KARTE}"
    geraete = [os.path.realpath(pfad + "-card"), os.path.realpath(pfad + "-render")]
    r = sh("docker", "run", "-d", "--name", NAME, "--device", geraete[0], "--device", geraete[1], "--group-add", "44", "--group-add", "105",
           "-p", f"127.0.0.1:{PORT}:8080", "-v", f"{MODELLE}:/models:ro", IMAGE,
           "-m", f"/models/{gguf}", "-ngl", str(ngl), "-c", str(kontext), "-np", "1", "-t", str(faeden),
           "--host", "0.0.0.0", "--port", "8080", "--jinja")
    if r.returncode:
        return r.stderr.strip()
    t0 = time.time()
    while time.time() - t0 < 1500:
        if sh("docker", "inspect", "-f", "{{.State.Running}}", NAME).stdout.strip() != "true":
            return "Server beendet: " + sh("docker", "logs", "--tail", "8", NAME).stderr[-600:]
        try:
            if json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5)).get("status") == "ok":
                return round(time.time() - t0, 1)
        except Exception:
            pass
        time.sleep(3)
    return "Zeitüberschreitung beim Laden"


def frage(text, max_tokens):
    body = {"messages": [{"role": "user", "content": text}], "max_tokens": max_tokens, "temperature": 0.7, "cache_prompt": False}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(req, timeout=3600)).get("timings", {})
    return {"prompt_token": t.get("prompt_n"), "einlesen_tps": round(t.get("prompt_per_second") or 0, 1),
            "neu_token": t.get("predicted_n"), "schreiben_tps": round(t.get("predicted_per_second") or 0, 2)}


def vram_mib():
    try:
        return round(int(open(f"/sys/bus/pci/devices/{betrieb.KARTE}/mem_info_vram_used").read()) / 2**20)
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gguf", required=True); p.add_argument("--ngl", type=int, nargs="+", required=True)
    p.add_argument("--faeden", type=int, default=6); p.add_argument("--kontext", type=int, default=8192)
    p.add_argument("--token", type=int, default=300); p.add_argument("--aus", default="dicht70.json")
    a = p.parse_args()
    aus = {"gguf": a.gguf, "faeden": a.faeden, "kontext": a.kontext, "beginn": time.strftime("%Y-%m-%dT%H:%M:%S"), "stufen": []}
    for ngl in a.ngl:
        stufe = {"ngl": ngl}
        lade = starten(a.gguf, ngl, a.faeden, a.kontext)
        if isinstance(lade, str):
            stufe["fehler"] = lade
        else:
            stufe.update(laden_s=lade, vram_mib=vram_mib())
            frage("Reply with the single word OK.", 4)  # warm
            m = betrieb.Messer(); m.start(); m.beginne("schreiben")
            laeufe = [frage(FRAGE, a.token) for _ in range(2)]
            while time.time() - m.t0 < betrieb.VORLAUF + 45:  # schnelle Modelle: genug USV-Messpunkte sammeln
                laeufe.append(frage(FRAGE, a.token))
            m.an = False
            stufe["schreiben_tps"] = [l["schreiben_tps"] for l in laeufe]
            stufe["schreiben_tps_median"] = round(statistics.median(stufe["schreiben_tps"]), 2)
            stufe.update(m.werte("schreiben"))
            lang = frage(betrieb.langprompt(120), 4)
            stufe["einlesen"] = {"prompt_token": lang["prompt_token"], "tps": lang["einlesen_tps"]}
            w = stufe.get("usv_w", {}).get("mittel")
            stufe["wh_je_1000_token_gesamt"] = betrieb.wh_je_1000(w, stufe["schreiben_tps_median"])
        sh("docker", "rm", "-f", NAME)
        aus["stufen"].append(stufe)
        print(json.dumps(stufe), flush=True)
        json.dump(aus, open(a.aus, "w"), indent=1)
        time.sleep(15)


if __name__ == "__main__":
    main()
