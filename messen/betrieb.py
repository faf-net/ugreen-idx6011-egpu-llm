#!/usr/bin/env python3
"""Betriebsmessungen am laufenden NAS: Strom an der USV, Kaltstart, Tempo unter Nebenlast.

  python3 betrieb.py strom     --model faber --aus strom.json      Leerlauf, geladen, Schreiben, Einlesen
  python3 betrieb.py kaltstart --model faber --aus kaltstart.json  Entladen -> erste Antwort, 1x kalte Platte, n-mal warm
  python3 betrieb.py last      --model faber --sekunden 120        nur Schreiblast erzeugen und das Tempo ausgeben

Läuft auf dem NAS selbst. Spricht mit llama-swap (URL), liest die USV über NUT (upsc, Variable USV) und die
Kartenleistung aus sysfs (Variable KARTE = PCI-Adresse). Die USV meldet ihre Werte nur alle 30 s neu, deshalb zählen
von jeder Phase erst die Messpunkte ab der 45. Sekunde. Nur Standardbibliothek.
"""
import argparse, glob, json, os, statistics, subprocess, threading, time, urllib.request, uuid

URL = os.environ.get("URL", "http://localhost:8090")
USV = os.environ.get("USV", "ups0@localhost")
KARTE = os.environ.get("KARTE", "0000:03:00.0")
VORLAUF = 45  # Sekunden, bis die USV-Werte zur Phase gehören


def usv_watt():
    try:
        return float(subprocess.run(["upsc", USV, "ups.realpower"], capture_output=True, text=True, timeout=5).stdout.strip())
    except Exception:
        return None


def karte_watt():
    for p in glob.glob(f"/sys/bus/pci/devices/{KARTE}/hwmon/hwmon*/power1_average"):
        try:
            return int(open(p).read()) / 1e6
        except Exception:
            pass
    return None


class Messer(threading.Thread):
    """Liest alle 2 s USV- und Kartenleistung und merkt sie sich mit der gerade laufenden Phase."""
    def __init__(self):
        super().__init__(daemon=True)
        self.phase, self.t0, self.punkte, self.an = None, 0, [], True

    def run(self):
        while self.an:
            if self.phase:
                self.punkte.append({"phase": self.phase, "t": round(time.time() - self.t0, 1), "usv_w": usv_watt(), "karte_w": karte_watt()})
            time.sleep(2)

    def beginne(self, phase):
        self.phase, self.t0 = phase, time.time()

    def werte(self, phase):
        ps = [p for p in self.punkte if p["phase"] == phase and p["t"] >= VORLAUF]
        aus = {"messpunkte": len(ps)}
        for feld in ("usv_w", "karte_w"):
            v = [p[feld] for p in ps if p[feld] is not None]
            if v:
                aus[feld] = {"mittel": round(statistics.mean(v), 1), "min": round(min(v), 1), "max": round(max(v), 1)}
        return aus


def anfrage(model, text, max_tokens, timeout=1800, nachrichten=None):
    body = {"model": model, "messages": nachrichten or [{"role": "user", "content": text}], "max_tokens": max_tokens, "temperature": 0.7,
            "stream": True, "stream_options": {"include_usage": True}, "reasoning_effort": "none"}
    req = urllib.request.Request(URL + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0, t_erst, usage, teile = time.time(), None, {}, []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for zeile in r:
            zeile = zeile.decode("utf-8", "replace").strip()
            if not zeile.startswith("data:") or zeile.endswith("[DONE]"):
                continue
            ev = json.loads(zeile[5:])
            usage = ev.get("usage") or usage
            for c in ev.get("choices") or []:
                d = c.get("delta") or {}
                if t_erst is None and (d.get("content") or d.get("reasoning_content") or d.get("reasoning")):
                    t_erst = time.time()
                teile.append(d.get("content") or "")
    t1 = time.time()
    t_erst = t_erst or t1
    return {"erste_antwort_s": round(t_erst - t0, 2), "gesamt_s": round(t1 - t0, 2), "prompt_token": usage.get("prompt_tokens"),
            "neu_token": usage.get("completion_tokens"), "schreib_s": round(t1 - t_erst, 2), "text": "".join(teile)}


def geladen():
    try:
        return [m.get("model") for m in json.load(urllib.request.urlopen(URL + "/running", timeout=10)).get("running", [])]
    except Exception:
        return None


def entladen():
    urllib.request.urlopen(URL + "/unload", timeout=120).read()
    while geladen():
        time.sleep(2)


SCHREIB = "Write a detailed, factual essay of about 1,500 words on the history of lighthouses in Europe. Run {}."


def langprompt(zeilen=2600):
    lauf = uuid.uuid4().hex
    text = "\n".join(f"Record {i} of batch {lauf[:8]}: station {uuid.uuid4().hex[:6]} reported value {i * 37 % 1000}." for i in range(zeilen))
    return text + "\n\nReply with the single word OK."


def schreiben(model, sekunden):
    """Lange Antworten hintereinander, bis die Zeit um ist. Gibt Token und reine Schreibzeit zurück."""
    ende, laeufe, n = time.time() + sekunden, [], 0
    while time.time() < ende:
        n += 1
        laeufe.append(anfrage(model, SCHREIB.format(n), 1500))
    tok, zeit = sum(l["neu_token"] or 0 for l in laeufe), sum(l["schreib_s"] for l in laeufe)
    return {"anfragen": len(laeufe), "neu_token": tok, "schreib_s": round(zeit, 1), "tps": round(tok / zeit, 1) if zeit else None,
            "tps_je_anfrage": [round(l["neu_token"] / l["schreib_s"], 1) for l in laeufe if l["neu_token"] and l["schreib_s"]]}


def lesen(model, sekunden):
    ende, laeufe = time.time() + sekunden, []
    while time.time() < ende:
        laeufe.append(anfrage(model, langprompt(), 4))
    tok, zeit = sum(l["prompt_token"] or 0 for l in laeufe), sum(l["erste_antwort_s"] for l in laeufe)
    return {"anfragen": len(laeufe), "prompt_token": tok, "lese_s": round(zeit, 1), "tps": round(tok / zeit, 1) if zeit else None}


def wh_je_1000(watt, tps):
    return round(watt * 1000 / tps / 3600, 3) if watt and tps else None


def strom(a):
    m = Messer(); m.start()
    aus = {"model": a.model, "beginn": time.strftime("%Y-%m-%dT%H:%M:%S"), "vorlauf_s": VORLAUF, "phasen": {}}
    entladen()
    m.beginne("leer"); time.sleep(VORLAUF + a.ruhe)
    aus["phasen"]["leer"] = m.werte("leer")
    anfrage(a.model, "Reply with the single word OK.", 4)
    m.beginne("geladen"); time.sleep(VORLAUF + a.ruhe)
    aus["phasen"]["geladen"] = m.werte("geladen")
    m.beginne("schreiben"); s = schreiben(a.model, VORLAUF + a.last)
    aus["phasen"]["schreiben"] = dict(m.werte("schreiben"), **s)
    m.beginne("lesen"); l = lesen(a.model, VORLAUF + a.last)
    aus["phasen"]["lesen"] = dict(m.werte("lesen"), **l)
    m.an = False
    leer = aus["phasen"]["leer"].get("usv_w", {}).get("mittel")
    for name in ("schreiben", "lesen"):
        p = aus["phasen"][name]
        w = p.get("usv_w", {}).get("mittel")
        p["wh_je_1000_token_gesamt"] = wh_je_1000(w, p.get("tps"))
        p["wh_je_1000_token_ueber_leerlauf"] = wh_je_1000(w - leer, p.get("tps")) if w and leer else None
    aus["messpunkte"] = m.punkte
    json.dump(aus, open(a.aus, "w"), indent=1)
    print(json.dumps({k: v for k, v in aus.items() if k != "messpunkte"}, indent=1))


def kaltstart(a):
    aus = {"model": a.model, "beginn": time.strftime("%Y-%m-%dT%H:%M:%S"), "laeufe": []}
    for i in range(a.n + 1):
        entladen(); time.sleep(10)
        kalt = i == 0
        if kalt:  # Seitencache leeren: das Modell kommt dann wirklich von der Platte
            subprocess.run(["sudo", "-n", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"], check=True)
            time.sleep(5)
        r = anfrage(a.model, "Reply with the single word OK.", 4)
        aus["laeufe"].append({"platte_kalt": kalt, "erste_antwort_s": r["erste_antwort_s"]})
        print(aus["laeufe"][-1], flush=True)
        json.dump(aus, open(a.aus, "w"), indent=1)
        time.sleep(20)


def last(a):
    print(json.dumps(schreiben(a.model, a.sekunden)))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    u = p.add_subparsers(dest="was", required=True)
    for name, f in (("strom", strom), ("kaltstart", kaltstart), ("last", last)):
        q = u.add_parser(name); q.set_defaults(f=f)
        q.add_argument("--model", default="faber"); q.add_argument("--aus", default=name + ".json")
        q.add_argument("--ruhe", type=int, default=120); q.add_argument("--last", type=int, default=180)
        q.add_argument("--n", type=int, default=4); q.add_argument("--sekunden", type=int, default=120)
    a = p.parse_args()
    a.f(a)
