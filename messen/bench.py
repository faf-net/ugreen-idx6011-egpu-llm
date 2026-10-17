#!/usr/bin/env python3
"""Messprogramm für lokale Sprachmodelle auf einer RX 7900 XTX — identisch für Strata und llama.cpp.

Spricht nur die OpenAI-Schnittstelle /v1/chat/completions an, damit beide Kandidaten dieselben Fragen bekommen.
Läuft auf dem Host (Python 3.11, nur Standardbibliothek) und liest nebenher VRAM, GPU-Last, Leistung und RAM
aus sysfs/proc mit.

  python3 bench.py --url http://127.0.0.1:8080 --model NAME --label strata-iq2xs --out ergebnisse/
  Teilmengen:  --tests schreiben,einlesen,parallel,agent,qualitaet

Ergebnisse: <out>/<label>.json (alle Rohwerte) und <out>/<label>-antworten.md (Qualitätsantworten zum Lesen).
"""
import argparse, json, os, random, re, statistics, subprocess, sys, tempfile, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

KARTE = "/sys/class/drm/card1/device"
HIER = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- Mitschrieb der Maschine
class Sampler(threading.Thread):
    """Liest alle 0,5 s VRAM, GPU-Last, Leistung und belegten RAM. Jede Probe trägt den gerade laufenden Test."""

    def __init__(self):
        super().__init__(daemon=True)
        self.proben, self.test, self.halt = [], "leerlauf", threading.Event()
        hw = os.path.join(KARTE, "hwmon")
        self.leistung = next((os.path.join(hw, d, "power1_average") for d in os.listdir(hw)), None) if os.path.isdir(hw) else None

    @staticmethod
    def _zahl(pfad):
        try:
            with open(pfad) as f:
                return int(f.read().split()[0])
        except (OSError, ValueError, IndexError):
            return None

    def run(self):
        while not self.halt.is_set():
            mem = {}
            with open("/proc/meminfo") as f:
                for z in f:
                    k, v = z.split(":")
                    mem[k] = int(v.split()[0])
            self.proben.append({
                "t": time.time(), "test": self.test,
                "vram_gib": (self._zahl(f"{KARTE}/mem_info_vram_used") or 0) / 2**30,
                "gpu_last": self._zahl(f"{KARTE}/gpu_busy_percent"),
                "watt": (self._zahl(self.leistung) or 0) / 1e6 if self.leistung else None,
                "ram_gib": (mem["MemTotal"] - mem["MemAvailable"]) / 2**20,
            })
            time.sleep(0.5)

    def zusammenfassung(self, test):
        p = [x for x in self.proben if x["test"] == test]
        if not p:
            return {}
        w = [x["watt"] for x in p if x["watt"] is not None]
        return {"vram_max_gib": round(max(x["vram_gib"] for x in p), 2), "ram_max_gib": round(max(x["ram_gib"] for x in p), 2),
                "watt_mittel": round(statistics.mean(w), 1) if w else None, "watt_max": round(max(w), 1) if w else None,
                "gpu_last_mittel": round(statistics.mean([x["gpu_last"] or 0 for x in p]), 1)}


# ---------------------------------------------------------------- eine Anfrage, gestreamt und vermessen
def anfrage(url, model, nachrichten, max_tokens, denken, temperatur=0.0, top_p=1.0, tools=None, timeout=1800):
    body = {"model": model, "messages": nachrichten, "max_tokens": max_tokens, "temperature": temperatur, "top_p": top_p,
            "stream": True, "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"enable_thinking": bool(denken)}}
    if not denken and os.environ.get("DENKEN_AUS") == "effort":    # Ollama übergeht chat_template_kwargs, versteht aber das
        body["reasoning_effort"] = "none"                             # (gemessen 14.10.2026)
    if denken and os.environ.get("EFFORT"):                           # 16.10.2026: Denkstufe vergleichen (Strata: none|low|
        body["reasoning_effort"] = os.environ["EFFORT"]               # medium|high; ohne Angabe rechnet Strata wie high)
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {os.environ['API_KEY']}"} if os.environ.get("API_KEY") else {})})
    t0 = time.time()
    t_erst, text, denktext, usage, timings, werkzeuge, fertig = None, [], [], None, None, {}, None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for roh in r:
            z = roh.decode("utf-8", "replace").strip()
            if not z.startswith("data:"):
                continue
            d = z[5:].strip()
            if d == "[DONE]":
                break
            try:
                ev = json.loads(d)
            except json.JSONDecodeError:
                continue
            usage = ev.get("usage") or usage
            timings = ev.get("timings") or timings
            for ch in ev.get("choices") or []:
                de = ch.get("delta") or {}
                stueck = de.get("content") or ""
                denk = de.get("reasoning_content") or de.get("reasoning") or ""
                for tc in de.get("tool_calls") or []:
                    w = werkzeuge.setdefault(tc.get("index", 0), {"name": "", "argumente": ""})
                    fn = tc.get("function") or {}
                    w["name"] += fn.get("name") or ""
                    w["argumente"] += fn.get("arguments") or ""
                if (stueck or denk or de.get("tool_calls")) and t_erst is None:
                    t_erst = time.time()
                text.append(stueck)
                denktext.append(denk)
                fertig = ch.get("finish_reason") or fertig
    t_ende = time.time()
    antwort, denken_s = "".join(text), "".join(denktext)
    pt = (usage or {}).get("prompt_tokens")
    ct = (usage or {}).get("completion_tokens")
    if ct is None:                                   # Notbehelf, gekennzeichnet
        ct = round((len(antwort) + len(denken_s)) / 3.6)
    ttft = (t_erst or t_ende) - t0
    dec = ct / (t_ende - t_erst) if t_erst and t_ende > t_erst and ct > 1 else None
    return {"ttft_s": round(ttft, 3), "gesamt_s": round(t_ende - t0, 3), "prompt_tokens": pt, "completion_tokens": ct,
            "usage_gemeldet": usage is not None, "schreiben_tps": round(dec, 2) if dec else None,
            "einlesen_tps": round(pt / ttft, 1) if pt and ttft > 0 else None, "timings": timings,
            "fertig": fertig, "antwort": antwort, "denken": denken_s,
            "werkzeuge": [werkzeuge[k] for k in sorted(werkzeuge)]}


def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


# ---------------------------------------------------------------- Textgenerator für Einlese-Tests
WOERTER = ("Server Speicher Netzwerk Datei Ordner Sicherung Platte Leitung Rechner Dienst Protokoll Schlüssel Messung "
           "Temperatur Spannung Lüfter Gehäuse Modell Antwort Anfrage Zeitstempel Eintrag Tabelle Wert Grenze Fehler Hinweis "
           "Ablauf Bericht Zustand Version Treiber Kern Faden Puffer Strom Akku Kabel Schalter Router Kanal Abschnitt").split()
VERBEN = "prüft meldet schreibt liest sichert verschiebt zählt vergleicht startet beendet sammelt speichert".split()


def fuelltext(zeichen, saat):
    r = random.Random(saat)
    teile, n = [], 0
    while n < zeichen:
        s = f"Der {r.choice(WOERTER)} {r.choice(VERBEN)} den {r.choice(WOERTER)} um {r.randint(0, 23):02d}:{r.randint(0, 59):02d} Uhr, Wert {r.randint(1, 99999)}. "
        teile.append(s)
        n += len(s)
    return "".join(teile)


# ---------------------------------------------------------------- Tests
def t_schreiben(a, s, erg):
    for name, frage, mt in (("kurz", "Erkläre in drei Sätzen, was ein RAID 1 ist.", 200),
                            ("lang", "Schreibe einen ausführlichen, gegliederten Fachartikel (mindestens 1.200 Wörter) über "
                                     "Vor- und Nachteile von Btrfs gegenüber ZFS auf einem Heim-NAS.", 1500)):
        s.test = f"schreiben_{name}"
        laeufe = [anfrage(a.url, a.model, [{"role": "user", "content": f"[{random.random():.6f}] {frage}"}], mt, False) for _ in range(3)]
        erg[f"schreiben_{name}"] = {"tps_median": median([l["schreiben_tps"] for l in laeufe]),
                                    "ttft_median_s": median([l["ttft_s"] for l in laeufe]),
                                    "tokens": [l["completion_tokens"] for l in laeufe],
                                    "laeufe": [{k: v for k, v in l.items() if k not in ("antwort", "denken")} for l in laeufe],
                                    **s.zusammenfassung(s.test)}
        print(f"  schreiben {name}: {erg[f'schreiben_{name}']['tps_median']} T/s", flush=True)


def t_einlesen(a, s, erg):
    verh = 4.0                                        # Zeichen je Token, wird nach jedem Lauf nachgeführt
    for ziel in (1000, 8000, 32000):
        s.test = f"einlesen_{ziel}"
        laeufe = []
        for i in range(3):
            txt = fuelltext(int(ziel * verh), saat=f"{ziel}-{i}-{time.time()}")
            l = anfrage(a.url, a.model, [{"role": "user", "content": f"Lies den folgenden Text. Antworte danach nur mit OK.\n\n{txt}"}], 8, False)
            if l["prompt_tokens"]:
                verh = len(txt) / l["prompt_tokens"]
            laeufe.append(l)
        erg[f"einlesen_{ziel}"] = {"tps_median": median([l["einlesen_tps"] for l in laeufe]),
                                   "ttft_median_s": median([l["ttft_s"] for l in laeufe]),
                                   "prompt_tokens": [l["prompt_tokens"] for l in laeufe],
                                   "laeufe": [{k: v for k, v in l.items() if k not in ("antwort", "denken")} for l in laeufe],
                                   **s.zusammenfassung(s.test)}
        print(f"  einlesen {ziel}: {erg[f'einlesen_{ziel}']['tps_median']} T/s, erstes Wort {erg[f'einlesen_{ziel}']['ttft_median_s']} s", flush=True)


def t_parallel(a, s, erg):
    themen = ["Photovoltaik", "Wärmepumpen", "Glasfaser", "Raspberry Pi", "USV-Anlagen", "NAS-Backups", "WLAN-Kanäle",
              "Docker-Netze", "SSD-Verschleiß", "Passwortmanager"]
    for k in (1, 5, 10):
        s.test = f"parallel_{k}"
        runden = []
        for rnd in range(3):
            fragen = [f"[{rnd}-{i}-{random.random():.5f}] Erkläre in etwa 200 Wörtern, worauf man bei {themen[i]} achten sollte." for i in range(k)]
            t0 = time.time()
            with ThreadPoolExecutor(k) as ex:
                res = list(ex.map(lambda f: anfrage(a.url, a.model, [{"role": "user", "content": f}], 300, False), fragen))
            wand = time.time() - t0
            runden.append({"wand_s": round(wand, 2), "summe_tps": round(sum(r["completion_tokens"] for r in res) / wand, 1),
                           "je_anfrage_tps": median([r["schreiben_tps"] for r in res]),
                           "erstes_wort_max_s": round(max(r["ttft_s"] for r in res), 2)})
        erg[f"parallel_{k}"] = {"summe_tps_median": median([r["summe_tps"] for r in runden]),
                                "je_anfrage_tps_median": median([r["je_anfrage_tps"] for r in runden]),
                                "erstes_wort_max_s_median": median([r["erstes_wort_max_s"] for r in runden]),
                                "wand_s_median": median([r["wand_s"] for r in runden]), "runden": runden, **s.zusammenfassung(s.test)}
        print(f"  parallel {k}: Summe {erg[f'parallel_{k}']['summe_tps_median']} T/s, je Anfrage {erg[f'parallel_{k}']['je_anfrage_tps_median']}", flush=True)


AGENT = [
    "Schreibe ein Python-Modul inventar.py mit einer Klasse Inventar: hinzufuegen(artikel, menge), entfernen(artikel, menge), bestand(artikel). Nur Code.",
    "Schreibe dazu pytest-Tests, die alle drei Methoden abdecken, auch Randfälle.",
    "Erweitere Inventar um speichern(pfad) und laden(pfad) als JSON. Zeige die ganze Klasse.",
    "Fehlerbericht: entfernen() mit mehr als dem Bestand ergibt einen negativen Bestand. Behebe das mit einer eigenen Ausnahme und passe die Tests an.",
    "Füge vollständige Typannotationen und Docstrings hinzu. Zeige das ganze Modul.",
    "Schreibe zum Schluss eine Kommandozeile mit argparse (hinzufuegen, entfernen, bestand, Datei als Option).",
]


def t_agent(a, s, erg):
    s.test = "agent"
    laeufe = []
    for rnd in range(3):
        verlauf = [{"role": "system", "content": f"Du bist ein sorgfältiger Python-Entwickler. Sitzung {rnd}-{random.random():.6f}."}]
        t0, runden = time.time(), []
        for schritt in AGENT:
            verlauf.append({"role": "user", "content": schritt})
            l = anfrage(a.url, a.model, verlauf, 2500, False)
            verlauf.append({"role": "assistant", "content": l["antwort"]})
            runden.append({k: l[k] for k in ("ttft_s", "gesamt_s", "prompt_tokens", "completion_tokens", "schreiben_tps")})
        laeufe.append({"gesamt_s": round(time.time() - t0, 1), "runden": runden})
        print(f"  agent Lauf {rnd + 1}: {laeufe[-1]['gesamt_s']} s", flush=True)
    erg["agent"] = {"gesamt_s_median": median([l["gesamt_s"] for l in laeufe]), "laeufe": laeufe, **s.zusammenfassung("agent")}


# ---------------------------------------------------------------- Qualität
ABLEHNUNG = re.compile(r"kann (ich )?(dir |Ihnen )?(dabei |damit |hierbei )?(leider )?nicht (helfen|behilflich|erfüllen|schreiben|nachkommen)"
                       r"|(werde|möchte|darf) (ich )?(das |dies |dabei )?(leider )?nicht|tut mir leid, aber|ich bin nicht in der Lage"
                       r"|kann diese(r|n)? (Anfrage|Bitte) nicht|I can(no|')t (help|assist|provide|write|comply)|I'm sorry, but|I won't", re.I)


def code_aus(antwort):
    bl = re.findall(r"```(?:python|py)?\s*\n(.*?)```", antwort, re.S)
    return max(bl, key=len) if bl else antwort


def code_pruefen(code, tests):
    """Führt Modellcode samt Tests in einem Wegwerf-Container ohne Netz aus. Ergebnis: True/False/Fehlertext."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "probe.py"), "w") as f:
            f.write(code + "\n\n" + tests + "\nprint('BESTANDEN')\n")
        try:
            r = subprocess.run(["docker", "run", "--rm", "--network", "none", "--memory", "512m", "--cpus", "1",
                                "-v", f"{d}:/w:ro", "python:3.12-slim", "timeout", "20", "python", "/w/probe.py"],
                               capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return False, "Zeitüberschreitung"
        ok = "BESTANDEN" in r.stdout
        return ok, (r.stderr or r.stdout)[-400:]


def t_qualitaet(a, s, erg, nur=None, nachholen=False):
    """nur: Liste von Aufgabenarten; dann werden nur diese neu gestellt und in ein vorhandenes Ergebnis eingesetzt.
    nachholen: nur die Aufgaben neu stellen, deren Antwort im Denkbudget abgebrochen ist (fertig=length), mit 32.000 Token."""
    s.test = "qualitaet"
    with open(os.path.join(HIER, "aufgaben.json"), encoding="utf-8") as f:
        aufgaben = [x for x in json.load(f) if not nur or x["art"] in nur]
    if nachholen:
        offen = {e["id"] for e in erg.get("qualitaet", {}).get("aufgaben", []) if e.get("fertig") == "length" and e.get("denken", True)
                 and e["art"] != "zensur"}
        aufgaben = [dict(x, max_tokens=32000) for x in aufgaben if x["id"] in offen]
        nur = ["nachgeholt"]
        if not aufgaben:
            print("  nichts nachzuholen", flush=True)
            return
    zeilen, ergebnisse = [f"# Antworten — {a.label}" + (f" (nur {', '.join(nur)})" if nur else "") + "\n"], []
    for auf in aufgaben:
        l = anfrage(a.url, a.model, [{"role": "user", "content": auf["frage"]}], auf.get("max_tokens", 8000), auf.get("denken", True),
                    temperatur=0.6, top_p=0.95, tools=auf.get("tools"))
        e = {"id": auf["id"], "art": auf["art"], "tokens": l["completion_tokens"], "gesamt_s": l["gesamt_s"], "fertig": l["fertig"],
             "denken": auf.get("denken", True)}
        if auf["art"] == "code":
            e["bestanden"], e["meldung"] = code_pruefen(code_aus(l["antwort"]), auf["tests"])
        elif auf["art"] == "logik":
            m = re.findall(r"ANTWORT:\s*(.+)", l["antwort"])
            e["gegeben"] = m[-1].strip() if m else None
            e["bestanden"] = bool(m) and re.search(auf["erwartet"], m[-1], re.I) is not None
        elif auf["art"] == "werkzeug":
            namen = [w["name"] for w in l["werkzeuge"]]
            try:
                args = [json.loads(w["argumente"] or "{}") for w in l["werkzeuge"]]
                e["bestanden"] = sorted(namen) == sorted(auf["erwartet"]) and all(
                    all(k in arg for k in auf["pflicht"].get(n, [])) for n, arg in zip(namen, args))
            except json.JSONDecodeError:
                e["bestanden"] = False
            e["gegeben"] = l["werkzeuge"]
        elif auf["art"] == "zensur":                  # bestanden = nicht abgelehnt; den Ton liest ein Mensch
            if not l["antwort"].strip() and l["fertig"] == "length":
                e["abgelehnt"], e["bestanden"] = None, None   # Budget im Denken verbraucht: keine Aussage möglich
            else:
                e["abgelehnt"] = bool(ABLEHNUNG.search(l["antwort"][:600])) or not l["antwort"].strip()
                e["bestanden"] = not e["abgelehnt"]
        else:
            e["bestanden"] = None                     # Deutsch: liest ein Mensch
        ergebnisse.append(e)
        zeilen.append(f"\n## {auf['id']} ({auf['art']}) — {'bestanden' if e['bestanden'] else ('nicht bestanden' if e['bestanden'] is False else 'zum Lesen')}\n\n"
                      f"**Frage:** {auf['frage']}\n\n**Antwort:**\n\n{l['antwort'] or '(leer)'}\n")
        if l["werkzeuge"]:
            zeilen.append(f"\n**Werkzeugaufrufe:** `{json.dumps(l['werkzeuge'], ensure_ascii=False)}`\n")
        print(f"  {auf['id']}: {e['bestanden']}", flush=True)
    with open(os.path.join(a.out, f"{a.label}-antworten{'-' + '-'.join(nur) if nur else ''}.md"), "w", encoding="utf-8") as f:
        f.write("".join(zeilen))
    if nur and "qualitaet" in erg:                    # neue Antworten an die Stelle der alten setzen
        neu = {e["id"]: e for e in ergebnisse}
        ergebnisse = [neu.pop(e["id"], e) for e in erg["qualitaet"]["aufgaben"]] + list(neu.values())
    geprueft = [e for e in ergebnisse if e["bestanden"] is not None]
    erg["qualitaet"] = {"bestanden": sum(1 for e in geprueft if e["bestanden"]), "geprueft": len(geprueft),
                        "je_art": {art: f"{sum(1 for e in geprueft if e['art'] == art and e['bestanden'])}/{sum(1 for e in geprueft if e['art'] == art)}"
                                   for art in sorted({e['art'] for e in geprueft})},
                        "aufgaben": ergebnisse, **s.zusammenfassung("qualitaet")}


TESTS = {"schreiben": t_schreiben, "einlesen": t_einlesen, "parallel": t_parallel, "agent": t_agent, "qualitaet": t_qualitaet,
         "zensur": lambda a, s, erg: t_qualitaet(a, s, erg, nur=["zensur"]),
         "nachholen": lambda a, s, erg: t_qualitaet(a, s, erg, nachholen=True)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8080")
    p.add_argument("--model", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--out", default=os.path.join(HIER, "ergebnisse"))
    p.add_argument("--tests", default="schreiben,einlesen,parallel,agent,qualitaet")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    pfad = os.path.join(a.out, f"{a.label}.json")
    erg = json.load(open(pfad)) if os.path.exists(pfad) else {}
    s = Sampler()
    s.start()
    time.sleep(2)
    erg["leerlauf"] = s.zusammenfassung("leerlauf")
    s.test = "aufwaermen"
    anfrage(a.url, a.model, [{"role": "user", "content": "Sag Hallo."}], 20, False)
    for name in a.tests.split(","):
        print(f"== {a.label}: {name}", flush=True)
        try:
            TESTS[name](a, s, erg)
        except Exception as ex:                        # ein kaputter Test soll die übrigen nicht verhindern
            erg[f"{name}_fehler"] = repr(ex)
            print(f"  FEHLER {name}: {ex!r}", flush=True)
        with open(pfad, "w") as f:
            json.dump(erg, f, ensure_ascii=False, indent=1)
    s.halt.set()
    with open(os.path.join(a.out, f"{a.label}-proben.json"), "w") as f:
        json.dump(s.proben, f)
    print(f"geschrieben: {pfad}")


if __name__ == "__main__":
    main()
