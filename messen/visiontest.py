#!/usr/bin/env python3
"""Test: Flash-Next (arbeit) liest Bilder selbst, mit Stratas Bildleser auf der CPU (--vision cpu).

Läuft auf der iDX:
  python3 visiontest.py --nur-konfig     legt /volume1/docker/strata-test/vision/ls-arbeit-vision.json an, sonst nichts
  python3 visiontest.py                  ganzer Test, nur wenn llama-swap /running leer ist (Hermes ruht)
  python3 visiontest.py --ohne-vergleich ohne die Gegenprobe mit arbeit und qwen27b

Ablauf: Eintrag arbeit-vision in llama-swap (Sicherung der config.yaml), drei Bilder + Text + Werkzeug an arbeit-vision,
dann dieselben Messungen an arbeit (VRAM, RAM, Tempo) und die Bilder an qwen27b, zuletzt config.yaml zurück und entladen.
Ergebnis: /volume1/docker/ki-messung/ergebnisse/vision-<zeit>.json
"""
import base64, glob, json, os, shutil, struct, sys, time, urllib.request, zlib

LS = os.environ.get("LS_URL", "http://127.0.0.1:8090")   # llama-swap
STRATA = "/volume1/docker/strata-test"
VISION = f"{STRATA}/vision"
KONFIG_ALT = f"{STRATA}/src/ls-arbeit.json"
KONFIG_NEU = f"{VISION}/ls-arbeit-vision.json"
LOG_NEU = f"{VISION}/ls-arbeit-vision.log"
SWAP = "/volume1/docker/llama-swap/config.yaml"
ERGEBNISSE = "/volume1/docker/ki-messung/ergebnisse"
EINTRAG = """  arbeit-vision:
    name: "Test — arbeit mit Bildleser auf der CPU"
    description: "Visiontest, wird nach dem Test wieder entfernt (visiontest.py)."
    cmd: ${strata} /strata/vision/ls-arbeit-vision.json
    cmdStop: docker stop -t 80 ls-${MODEL_ID}
    proxy: http://127.0.0.1:${PORT}
    checkEndpoint: /health
    ttl: 600

"""
WERKZEUG = [{"type": "function", "function": {"name": "wetter_abrufen", "description": "Wettervorhersage für einen Ort",
             "parameters": {"type": "object", "properties": {"ort": {"type": "string"}}, "required": ["ort"]}}}]


# ------------------------------------------------------------------------------------------------ Testbilder
def png(b, h, farbe):
    """PNG ohne Fremdbibliothek; farbe(x, y) liefert drei Bytes."""
    zeilen = b"".join(b"\x00" + b"".join(farbe(x, y) for x in range(b)) for y in range(h))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", b, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(zeilen)) + ch(b"IEND", b"")


WEISS, SCHWARZ = b"\xff\xff\xff", b"\x10\x10\x10"
ZIFFERN = {"4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
           "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
           "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
           "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"]}


def bild_quadrat():
    return png(64, 64, lambda x, y: b"\xc0\x30\x30" if 16 <= x < 48 and 16 <= y < 48 else WEISS)


def bild_zahl(text="4728", s=8):
    rand, b, h = 2 * s, (len(text) * 6 - 1) * s + 4 * s, 7 * s + 4 * s
    def farbe(x, y):
        x, y = x - rand, y - rand
        if x < 0 or y < 0 or y >= 7 * s:
            return WEISS
        i, sx = divmod(x // s, 6)
        if i >= len(text) or sx == 5:
            return WEISS
        return SCHWARZ if ZIFFERN[text[i]][y // s][sx] == "1" else WEISS
    return png(b, h, farbe)


def bild_drei():
    farben = [b"\xc0\x30\x30", b"\x30\xa0\x40", b"\x30\x50\xc0"]           # rot, grün, blau
    return png(192, 64, lambda x, y: farben[x // 64] if 12 <= x % 64 < 52 and 12 <= y < 52 else WEISS)


BILDER = [("quadrat", bild_quadrat, "Welche Farbe hat das Quadrat in der Mitte? Antworte mit einem Wort.", ["rot"]),
          ("zahl", bild_zahl, "Welche Zahl steht im Bild? Antworte nur mit der Zahl.", ["4728"]),
          ("drei", bild_drei, "Welche Farben haben die drei Quadrate, von links nach rechts? Nur die drei Farbwörter.",
           ["rot", "grün", "blau"]),
          # so groß wie ein Bildschirmfoto: der Bildleser stößt an max_tokens 300, das zeigt die echte Zeit je Bild
          ("zahl-gross", lambda: bild_zahl("8274", s=40), "Welche Zahl steht im Bild? Antworte nur mit der Zahl.", ["8274"])]


# ------------------------------------------------------------------------------------------------ Messen
def frage(modell, nachrichten, max_tokens=60, tools=None, timeout=900):
    body = {"model": modell, "messages": nachrichten, "max_tokens": max_tokens, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False}}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(f"{LS}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    m = d["choices"][0]["message"]
    return round(time.time() - t0, 2), (m.get("content") or "").strip(), m.get("tool_calls") or [], d.get("usage", {})


def bildnachricht(text, daten):
    url = "data:image/png;base64," + base64.b64encode(daten).decode()
    return {"role": "user", "content": [{"type": "text", "text": text}, {"type": "image_url", "image_url": {"url": url}}]}


def holen(pfad):
    with urllib.request.urlopen(LS + pfad, timeout=30) as r:
        return json.load(r)


def xtx():
    """Die Karte mit eigenem VRAM (AMD, 0x1002), nicht die Arc-iGPU."""
    for d in glob.glob("/sys/class/drm/card*/device"):
        try:
            if open(f"{d}/vendor").read().strip() == "0x1002" and os.path.exists(f"{d}/mem_info_vram_total"):
                return d
        except OSError:
            pass
    return None


def speicher():
    k = xtx()
    mib = lambda f: int(open(f"{k}/{f}").read()) // 2**20
    meminfo = {z.split(":")[0]: int(z.split()[1]) for z in open("/proc/meminfo")}
    return {"vram_frei_mib": mib("mem_info_vram_total") - mib("mem_info_vram_used") if k else None,
            "ram_verfuegbar_gib": round(meminfo["MemAvailable"] / 2**20, 1)}


def logzeilen(pfad, muster=("vram", "slot", "vision", "image", "encod", "mmproj", "warn", "error")):
    try:
        with open(pfad, errors="replace") as f:
            return [z.rstrip() for z in f if any(m in z.lower() for m in muster)][-40:]
    except OSError as e:
        return [f"(Log nicht lesbar: {e})"]


def textteil(modell):
    t_lade, antwort, _, _ = frage(modell, [{"role": "user", "content": "Erkläre in einem Satz auf Deutsch, was ein NAS ist."}])
    time.sleep(3)
    sp = speicher()
    t2, _, _, u2 = frage(modell, [{"role": "user", "content": "Nenne drei Vorteile von RAID 1, als kurze Liste."}], max_tokens=300)
    tw, _, calls, _ = frage(modell, [{"role": "user", "content": "Wie wird das Wetter morgen in Detmold?"}], tools=WERKZEUG)
    werkzeug = calls[0]["function"]["name"] + " " + calls[0]["function"]["arguments"] if calls else "KEIN AUFRUF"
    tps = round((u2.get("completion_tokens") or 0) / t2, 1) if t2 else 0
    return {"laden_und_erste_antwort_s": t_lade, "antwort": antwort[:200], **sp, "raid_s": t2, "raid_ts_gesamt": tps,
            "werkzeug": werkzeug}


def bildteil(modell):
    ergebnisse = []
    for name, erzeuge, text, erwartet in BILDER:
        try:
            t, antwort, _, u = frage(modell, [bildnachricht(text, erzeuge())])
            treffer = all(w in antwort.lower() for w in erwartet)
            ergebnisse.append({"bild": name, "s": t, "antwort": antwort[:80], "richtig": treffer,
                               "prompt_tokens": u.get("prompt_tokens")})
        except Exception as e:
            ergebnisse.append({"bild": name, "fehler": repr(e)})
        print(f"  {modell:14} {name:8} {ergebnisse[-1]}", flush=True)
    try:                                       # zweites Bild in derselben Unterhaltung, nach einer Textantwort
        verlauf = [bildnachricht(BILDER[0][2], bild_quadrat()), {"role": "assistant", "content": "Rot."},
                   bildnachricht(BILDER[1][2], bild_zahl())]
        t, antwort, _, _ = frage(modell, verlauf)
        ergebnisse.append({"bild": "verlauf", "s": t, "antwort": antwort[:80], "richtig": "4728" in antwort})
    except Exception as e:
        ergebnisse.append({"bild": "verlauf", "fehler": repr(e)})
    print(f"  {modell:14} verlauf  {ergebnisse[-1]}", flush=True)
    return ergebnisse


# ------------------------------------------------------------------------------------------------ Konfiguration
def konfig_anlegen():
    cfg = json.load(open(KONFIG_ALT))
    if "--vision" not in cfg["args"]:
        cfg["args"].append("--vision")
    native = cfg["args"][cfg["args"].index("--native") + 1]       # das Textmodell, nur das Vokabular wird geöffnet
    cfg["vision"] = {"exe": "/strata/vision/bin/strata-vision", "mmproj": "/strata/vision/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
                     "model": native, "gpu": False, "max_tokens": 300, "threads": 8}
    cfg["model_name"] = "arbeit-vision"
    cfg["log"] = "/strata/vision/ls-arbeit-vision.log"
    with open(KONFIG_NEU, "w") as f:
        json.dump(cfg, f, indent=1, ensure_ascii=False)
    print(f"angelegt: {KONFIG_NEU}")


def eintrag_setzen(sicherung):
    shutil.copy2(SWAP, sicherung)
    text = open(SWAP).read()
    if "\n  arbeit-vision:" in text:
        return
    marke = "\n  frei:\n"
    if marke not in text:
        sys.exit("Eintrag frei: in config.yaml nicht gefunden, nichts geändert")
    with open(SWAP, "w") as f:
        f.write(text.replace(marke, "\n" + EINTRAG.rstrip("\n") + "\n" + marke, 1))
    for _ in range(30):                        # llama-swap lädt die Konfiguration selbst neu
        time.sleep(1)
        try:
            if any(m["id"] == "arbeit-vision" for m in holen("/v1/models")["data"]):
                return
        except Exception:
            pass
    sys.exit("arbeit-vision taucht in /v1/models nicht auf")


def main():
    if not (os.path.exists(f"{VISION}/bin/strata-vision") and os.path.exists(f"{VISION}/mmproj-Qwen3.8-Flash-Next-BF16.gguf")):
        sys.exit("strata-vision oder die mmproj-Datei fehlt unter " + VISION)
    konfig_anlegen()
    if "--nur-konfig" in sys.argv:
        return
    laeuft = holen("/running").get("running") or []
    if laeuft and "--trotzdem" not in sys.argv:
        sys.exit(f"llama-swap hat ein Modell geladen ({laeuft}), vermutlich nutzt Frank Hermes. Abbruch (--trotzdem übergeht das).")
    zeit = time.strftime("%Y%m%d-%H%M")
    sicherung = f"{SWAP}.vor-visiontest-{zeit}"
    erg = {"zeit": zeit, "konfig": json.load(open(KONFIG_NEU)), "vorher": speicher()}
    eintrag_setzen(sicherung)
    try:
        print("arbeit-vision: Text und Werkzeug", flush=True)
        erg["arbeit_vision"] = textteil("arbeit-vision")
        print(" ", erg["arbeit_vision"], flush=True)
        erg["arbeit_vision"]["bilder"] = bildteil("arbeit-vision")
        erg["arbeit_vision"]["nach_bildern"] = speicher()
        erg["arbeit_vision"]["log"] = logzeilen(LOG_NEU)
        if "--ohne-vergleich" not in sys.argv:
            print("arbeit (Gegenprobe ohne Bildleser)", flush=True)
            erg["arbeit"] = textteil("arbeit")
            erg["arbeit"]["log"] = logzeilen(f"{STRATA}/src/ls-arbeit.log")[-15:]
            print(" ", {k: v for k, v in erg["arbeit"].items() if k != "log"}, flush=True)
            print("qwen27b (heutiger Bildweg)", flush=True)
            erg["qwen27b_bilder"] = bildteil("qwen27b")
    finally:
        shutil.copy2(sicherung, SWAP)          # Eintrag wieder heraus, auch bei Abbruch
        try:
            urllib.request.urlopen(LS + "/unload", timeout=120).read()
        except Exception as e:
            print("Entladen fehlgeschlagen:", repr(e))
        os.makedirs(ERGEBNISSE, exist_ok=True)
        ziel = f"{ERGEBNISSE}/vision-{zeit}.json"
        with open(ziel, "w") as f:
            json.dump(erg, f, indent=1, ensure_ascii=False)
        print(f"Ergebnis: {ziel} · config.yaml zurückgesetzt aus {sicherung}")


if __name__ == "__main__":
    main()
