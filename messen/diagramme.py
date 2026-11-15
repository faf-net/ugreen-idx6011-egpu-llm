#!/usr/bin/env python3
"""Alle Diagramme des Repos aus einer Hand: HTML mit eingebettetem SVG im hellen Workbench-Design.

Ein Rahmen für alle Bilder:
Dachzeile (Mono, Versalien), Titel (Instrument Serif), je Feld eine Zeile "was und in welcher Einheit" und eine
Lesehilfe, höchstens eine kursive Anmerkung, unten Legende und Quelle. Bernstein ist die Hauptreihe, Stahl die
Vergleichsreihe; Flächen mit 18 % Deckkraft und voller Kante. Zustände (gut, Grenzfall, schlecht) tragen immer
auch ein Wort.

  python diagramme.py messen/daten bilder/html          # schreibt <name>-<sprache>.html
  uv run --with playwright python diagramme.py messen/daten bilder/html --png bilder   # dazu die PNG

Nur Standardbibliothek; für --png zusätzlich playwright mit Chromium. Die Schriften kommen von Google Fonts.
"""
import html, json, math, os, statistics, sys
from collections import defaultdict

W, L, R = 960, 72, 928
PAPER, INK, MUTED, TITLE, BASE = "#efeae1", "#2a2724", "#6a6258", "#171512", "#8b8377"
ACC, STAHL, PETROL, GOLD = "#975b34", "#456579", "#4e716a", "#7e6820"
# Zustandstöne: Fläche, Kante, Wort
TON = {"salbei": ("#c3c5b1", "#5e7040", "#485530"), "gold": ("#cdc3a7", "#7e6820", "#5f4e18"),
       "rose": ("#d6bbb1", "#9c4d40", "#7a3c32"), "neutral": ("#e4ded3", "#8b8377", "#6a6258")}
FONT = {"sans": "'Atkinson Hyperlegible Next', 'Segoe UI', sans-serif", "mono": "'JetBrains Mono', Consolas, monospace",
        "serif": "'Instrument Serif', Georgia, serif"}
GITTER = 'stroke="#2a2724" stroke-opacity="0.08" stroke-width="0.8"'
ACHSE = 'stroke="#2a2724" stroke-opacity="0.3" stroke-width="1"'


def z(x, sp, nk=None):
    """Zahl in der Schreibweise der Sprache; ohne nk: ab 100 ganzzahlig, darunter eine Nachkommastelle."""
    if nk is None:
        nk = 0 if abs(x) >= 100 else 1
    s = f"{x:,.{nk}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") if sp == "de" else s


class Svg:
    def __init__(self):
        self.e = []

    def text(self, x, y, t, size=9, fill=MUTED, font="mono", anchor="start", weight=None, kursiv=False, sperr=None):
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        w = f' font-weight="{weight}"' if weight else ""
        k = ' font-style="italic"' if kursiv else ""
        s = f' letter-spacing="{sperr}"' if sperr else ""
        self.e.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-family="{FONT[font]}"{a}{w}{k}{s}>{html.escape(str(t))}</text>')

    def line(self, x1, y1, x2, y2, stil=GITTER):
        self.e.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {stil}/>')

    def rect(self, x, y, w, h, farbe, deck=0.18, kante=None, sw=1, rx=0, strich=None):
        k = f' stroke="{kante or farbe}" stroke-width="{sw}"' if kante is not False else ""
        d = f' stroke-dasharray="{strich}"' if strich else ""
        r = f' rx="{rx}"' if rx else ""
        self.e.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" fill="{farbe}" fill-opacity="{deck}"{k}{d}{r}/>')

    def punkt(self, x, y, farbe, hohl=False, r=4):
        f = PAPER if hohl else farbe
        self.e.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{f}" stroke="{farbe}" stroke-width="1.6"/>')

    def zug(self, pts, farbe, sw=2):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.e.append(f'<polyline points="{p}" fill="none" stroke="{farbe}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>')

    def roh(self, s):
        self.e.append(s)


def kopf(s, dach, titel):
    s.text(L, 36, dach.upper(), 8.5, MUTED, "mono", weight=500, sperr="0.16em")
    s.text(L, 68, titel, 25, TITLE, "serif")


def feld(s, x, y, was, hilfe=None, anmerkung=None, x_rechts=None):
    """Kopfzeile eines Feldes: was gemessen wird (Mono), Lesehilfe (Sans), optional Anmerkung rechtsbündig."""
    s.text(x, y, was.upper(), 8.5, MUTED, "mono", weight=500, sperr="0.14em")
    if hilfe:
        s.text(x, y + 16, hilfe, 10, MUTED, "sans")
    if anmerkung:
        s.text(x_rechts, y + 16, anmerkung, 15, INK, "serif", anchor="end", kursiv=True)


def umbruch(text, breite=150):
    zeilen, akt = [], ""
    for teil in text.split(" · "):
        if akt and len(akt) + len(teil) + 3 > breite:
            zeilen.append(akt); akt = teil
        else:
            akt = f"{akt} · {teil}" if akt else teil
    return zeilen + [akt]


def fuss(s, y, legende, quelle):
    """Trennlinie, Legendenzeile, Quelle. Gibt die Gesamthöhe zurück."""
    s.line(40, y, W - 40, y, 'stroke="#2a2724" stroke-opacity="0.14" stroke-width="0.8"')
    y += 26
    if legende:
        x = L
        for art, farbe, name in legende:
            if art == "balken":
                s.rect(x, y - 9, 16, 10, farbe, rx=2)
            elif art == "leer":
                s.rect(x, y - 9, 16, 10, farbe, deck=0.06, rx=2, strich="3,2")
            elif art == "ton":
                s.rect(x, y - 9, 16, 10, TON[farbe][0], deck=1, kante=TON[farbe][1], rx=2)
            elif art == "linie":
                s.zug([(x, y - 4), (x + 16, y - 4)], farbe); s.punkt(x + 8, y - 4, farbe, r=3)
            elif art == "linie-hohl":
                s.zug([(x, y - 4), (x + 16, y - 4)], farbe); s.punkt(x + 8, y - 4, farbe, hohl=True, r=3)
            elif art == "punkt":
                s.punkt(x + 8, y - 4, farbe)
            elif art == "punkt-hohl":
                s.punkt(x + 8, y - 4, farbe, hohl=True)
            elif art == "marke":
                s.roh(f'<path d="M{x + 3},{y - 9} h10 l-5,8 z" fill="{INK}"/>')
            s.text(x + 24, y, name, 10, INK, "sans")
            x += 24 + len(name) * 5.5 + 28
        y += 22
    for zeile in umbruch(quelle):
        s.text(L, y, zeile, 8.5, MUTED, "mono")
        y += 14
    return int(math.ceil((y + 8) / 4) * 4)


class Hoch:
    """Feld mit senkrechter Werteachse."""
    def __init__(self, s, x0, x1, y0, y1, vmax, vmin=0):
        self.s, self.x0, self.x1, self.y0, self.y1, self.vmin, self.vmax = s, x0, x1, y0, y1, vmin, vmax

    def Y(self, v):
        return self.y1 - (v - self.vmin) / (self.vmax - self.vmin) * (self.y1 - self.y0)

    def achse(self, schritt, sp, fett=None):
        v = self.vmin
        while v <= self.vmax + 1e-9:
            y = self.Y(v)
            if v > self.vmin:
                self.s.line(self.x0, y, self.x1, y)
            b = fett is not None and abs(v - fett) < 1e-9
            self.s.text(self.x0 - 8, y + 3, z(v, sp, 0), 9, INK if b else MUTED, "mono", "end", 600 if b else None)
            v += schritt
        self.s.line(self.x0, self.y0, self.x0, self.y1, ACHSE)
        self.s.line(self.x0, self.y1, self.x1, self.y1, ACHSE)

    def balken(self, mitte, breite, v, farbe, text=None, fokus=False, stark=False):
        y = self.Y(v)
        self.s.rect(mitte - breite / 2, y, breite, self.y1 - y, farbe, sw=2 if stark else 1)
        if text:
            self.s.text(mitte, y - 7, text, 9, farbe if fokus else MUTED, "mono", "middle", 600 if fokus else None)


def endmarken(s, x, marken, abstand=26):
    """Reihenname und Wert rechts neben dem letzten Punkt; nahe Marken auseinanderschieben."""
    marken = sorted(marken, key=lambda m: m[0])
    ys = [m[0] for m in marken]
    for k in range(1, len(ys)):
        fehl = abstand - (ys[k] - ys[k - 1])
        if fehl > 0:
            ys[k - 1] -= fehl / 2; ys[k] += fehl / 2
    for (_, farbe, name, wert), y in zip(marken, ys):
        if wert is None:
            s.text(x, y + 3.5, name, 10, farbe, "sans", weight=600)
        else:
            s.text(x, y - 1, name, 10, farbe, "sans", weight=600)
            s.text(x, y + 10, wert, 9, farbe, "mono")


def seite(slug, sp, titel, desc, s, hoehe):
    return f'''<!DOCTYPE html>
<html lang="{sp}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(titel)}</title>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: {PAPER}; color: {INK}; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem 16px; }}
    .frame {{ max-width: 1100px; width: 100%; min-width: 0; }}
    .scroll {{ width: 100%; overflow-x: auto; }}
    svg {{ width: 100%; min-width: {W}px; display: block; font-variant-numeric: tabular-nums; }}
    @media print {{ .scroll {{ overflow: visible; }} svg {{ min-width: 0; }} }}
  </style>
</head>
<body>
  <div class="frame"><div class="scroll">
    <svg viewBox="0 0 {W} {hoehe}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">
      <title id="{slug}-title">{html.escape(titel[:60])}</title>
      <desc id="{slug}-desc">{html.escape(desc)}</desc>
      <rect width="{W}" height="{hoehe}" fill="{PAPER}"/>
      {chr(10).join("      " + e for e in s.e).strip()}
    </svg>
  </div></div>
</body>
</html>
'''


# ───────────────────────── Daten laden ─────────────────────────

def med(werte):
    werte = [w for w in werte if w is not None]
    return statistics.median(werte) if werte else None


def strata_bench(pfad):
    r = json.load(open(pfad, encoding="utf-8"))["results"]
    ok = lambda rs: [x for x in rs if x.get("ok")]
    out = {"chat": med([x["decode_tps"] for x in ok(r["chat"]["requests"])]),
           "agent": med([x["decode_tps"] for sitz in r["agent"]["sessions"] for x in ok(sitz)])}
    for k in ("4K", "16K", "32K"):
        reqs = ok(r["prompts"][k]["requests"])
        out[k] = med([x["prompt_tps"] for x in reqs])
        out["ttft_" + k] = med([x["ttft_s"] for x in reqs])
    return out


def standard(pfad):
    su = json.load(open(pfad, encoding="utf-8"))["summaries"]
    return {(x["case_id"], x["metric"]): x["median"] for x in su if x.get("concurrency") == 1}


def tiefe_daten(d):
    werte = defaultdict(lambda: defaultdict(list))
    for zeile in open(os.path.join(d, "tiefe-20261017.jsonl"), encoding="utf-8"):
        r = json.loads(zeile)
        werte[r["label"]][r["ziel"]].append(r)
    return werte


# ───────────────────────── die Diagramme ─────────────────────────

def logx(x0, x1):
    return lambda v: x0 + 16 + (math.log2(v) - 10) / 8 * (x1 - x0 - 16)

TIEFEN = [(1024, "1K"), (4096, "4K"), (16384, "16K"), (65536, "64K"), (131072, "128K"), (262144, "256K")]


def tiefe(d, sp):
    en = sp == "en"
    w = tiefe_daten(d)
    s = Svg()
    titel = "Throughput barely drops from 1K to 248K tokens of context" if en else "Das Tempo fällt von 1K bis 248K Token Kontext kaum"
    kopf(s, "Strata 0.1.44.1 · Flash-Next 125B IQ3_XXS · RX 7900 XTX over OCuLink x4" if en else
         "Strata 0.1.44.1 · Flash-Next 125B IQ3_XXS · RX 7900 XTX über OCuLink x4", titel)
    reihen = (("mit-mtp", ACC, False, "with MTP" if en else "mit MTP"), ("ohne-mtp", STAHL, True, "without MTP" if en else "ohne MTP"))
    felder = ((L, 456, "decode_tps", 80, 20, "A · Decode · tokens/s" if en else "A · Schreiben · Token/s",
               "256 new tokens after a fresh prompt · higher is faster" if en else "256 neue Token nach frischem Prompt · höher ist schneller",
               "MTP adds 21–29 % at every depth." if en else "MTP bringt 21–29 % in jeder Tiefe.", 55),
              (544, R, "prompt_tps", 1400, 200, "B · Prefill · tokens/s" if en else "B · Einlesen · Token/s",
               "reading the fresh prompt · higher is faster" if en else "Einlesen des frischen Prompts · höher ist schneller",
               "From 16K on, reading stays above 1,000 tokens/s." if en else "Ab 16K bleibt das Einlesen über 1.000 Token/s.", 520))
    for x0, x1, wert, vmax, schritt, was, hilfe, anm, anm_v in felder:
        feld(s, x0, 104, was, hilfe)
        p = Hoch(s, x0, x1, 144, 384, vmax)
        p.achse(schritt, sp)
        X = logx(x0, x1 - 76)
        for v, name in TIEFEN:
            s.line(X(v), 384, X(v), 388, ACHSE)
            s.text(X(v), 400, name, 9, MUTED, "mono", "middle")
        s.text((x0 + x1 - 76) / 2, 420, ("context depth (tokens)" if en else "Kontexttiefe (Token)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
        marken = []
        for label, farbe, hohl, name in reihen:
            pts = []
            for ziel in sorted(w[label]):
                rs = w[label][ziel]
                pts.append((X(statistics.median([r["prompt_token"] for r in rs])), p.Y(med([r[wert] for r in rs])), med([r[wert] for r in rs])))
            s.zug([(x, y) for x, y, _ in pts], farbe)
            for x, y, _ in pts:
                s.punkt(x, y, farbe, hohl)
            marken.append((pts[-1][1], farbe, name, z(pts[-1][2], sp)))
        endmarken(s, pts[-1][0] + 12, marken)
        if wert == "decode_tps":
            s.text(x0 + 24, p.Y(anm_v), anm, 15, INK, "serif", kursiv=True)
        else:
            s.text(x1, p.Y(anm_v), anm, 15, INK, "serif", "end", kursiv=True)
    h = fuss(s, 444, None, "UGREEN iDX6011 Pro, 64 GB · one fresh prompt per run, then 256 new tokens · engine timings, median of 2–3 runs · messen/tiefe.py · data: messen/daten/tiefe-20261017.jsonl" if en else
             "UGREEN iDX6011 Pro, 64 GB · je Lauf ein frischer Prompt, dann 256 neue Token · Zeiten der Engine, Median aus 2–3 Läufen · messen/tiefe.py · Daten: messen/daten/tiefe-20261017.jsonl")
    return "tiefe", titel, ("Decode and prefill throughput with and without the MTP draft head at six context depths from 1K to 248K tokens." if en else
                            "Schreib- und Einlesetempo mit und ohne MTP-Kopf in sechs Kontexttiefen von 1K bis 248K Token."), s, h


def mtp_annahme(d, sp):
    en = sp == "en"
    w = tiefe_daten(d)["mit-mtp"]
    s = Svg()
    titel = "About half of the MTP drafts are accepted, at every depth" if en else "Rund die Hälfte der MTP-Vorschläge wird angenommen, in jeder Tiefe"
    kopf(s, "Strata 0.1.44.1 · Flash-Next 125B IQ3_XXS · RX 7900 XTX", titel)
    feld(s, L, 104, "Accepted draft tokens · %" if en else "Angenommene Vorschlagstoken · %",
         "share of the MTP head's draft tokens the model kept" if en else "Anteil der Vorschlagstoken des MTP-Kopfs, die das Modell übernommen hat")
    p = Hoch(s, L, R, 144, 344, 100)
    p.achse(20, sp)
    X = logx(L, R - 24)
    pts = []
    for ziel in sorted(w):
        rs = w[ziel]
        n = sum(r["draft_n"] or 0 for r in rs); ok = sum(r["draft_ok"] or 0 for r in rs)
        if n:
            pts.append((X(statistics.median([r["prompt_token"] for r in rs])), 100 * ok / n))
    for v, name in TIEFEN:
        s.line(X(v), 344, X(v), 348, ACHSE)
        s.text(X(v), 360, name, 9, MUTED, "mono", "middle")
    s.text((L + R) / 2, 380, ("context depth (tokens)" if en else "Kontexttiefe (Token)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
    s.zug([(x, p.Y(v)) for x, v in pts], ACC)
    for x, v in pts:
        s.punkt(x, p.Y(v), ACC)
        s.text(x, p.Y(v) - 10, f"{v:.0f} %", 9, ACC, "mono", "middle", 600)
    h = fuss(s, 404, None, "median of 2–3 fresh prompts per depth, 256 new tokens each · messen/tiefe.py · data: messen/daten/tiefe-20261017.jsonl" if en else
             "Median aus 2–3 frischen Prompts je Tiefe, je 256 neue Token · messen/tiefe.py · Daten: messen/daten/tiefe-20261017.jsonl")
    return "mtp-annahme", titel, ("MTP draft acceptance between 48 and 57 percent at six context depths from 1K to 248K tokens." if en else
                                  "MTP-Annahmequote zwischen 48 und 57 Prozent in sechs Kontexttiefen von 1K bis 248K Token."), s, h


def pool_workers(d, sp):
    en = sp == "en"
    s = Svg()
    titel = "On a hybrid CPU, nine pool workers beat the automatic choice" if en else "Auf der Hybrid-CPU schlagen neun Pool-Worker die Automatik"
    kopf(s, "Strata 0.1.44.1 · Flash-Next 125B IQ2_XS · 6 P + 8 E + 2 LP-E cores" if en else "Strata 0.1.44.1 · Flash-Next 125B IQ2_XS · 6 P- + 8 E- + 2 LP-E-Kerne", titel)
    feld(s, L, 104, "Decode, long answer · tokens/s" if en else "Schreiben, lange Antwort · Token/s", "higher is faster" if en else "höher ist schneller")
    p = Hoch(s, L, R, 144, 384, 100)
    p.achse(20, sp)
    # gemessen 14.10.2026, lange Antwort, Median aus 3 Läufen
    for i, (name, v) in enumerate(((("automatic" if en else "Automatik"), 56.1), ("5", 76.6), ("9", 76.8), ("13", 74.0))):
        mitte = L + (i + 0.5) * (R - L) / 4
        fokus = name == "9"
        p.balken(mitte, 72, v, ACC if fokus else STAHL, z(v, sp), fokus, fokus)
        s.text(mitte, 404, name, 12, ACC if fokus else INK, "sans", "middle", 600)
    s.text((L + R) / 2, 424, "--pool-workers", 9, MUTED, "mono", "middle")
    s.text(L + 24, 172, "Up to 0.2.0 the automatic choice cost 27 %." if en else "Bis 0.2.0 kostete die Automatik 27 %.", 15, INK, "serif", kursiv=True)
    h = fuss(s, 448, None, "median of 3 runs, measured 14 Oct 2026 · from Strata 0.2.1 the default plans 10 workers and keeps them off the LP-E cores: leave --pool-workers out" if en else
             "Median aus 3 Läufen, gemessen am 14.10.2026 · ab Strata 0.2.1 plant die Voreinstellung 10 Worker und hält sie von den LP-E-Kernen fern: --pool-workers weglassen")
    return "pool-workers", titel, ("Decode speed for the automatic worker count and for 5, 9 and 13 pool workers; 9 is fastest at 76.8 tokens per second, automatic reaches 56.1." if en else
                                   "Schreibtempo mit automatischer Worker-Zahl und mit 5, 9 und 13 Pool-Workern; 9 ist mit 76,8 Token je Sekunde am schnellsten, die Automatik erreicht 56,1."), s, h


VERSIONEN = [("0.2.0β", "2026-10-19/strata-0.2.0-beta/strata-bench-results.json"),
             ("0.2.1", "2026-10-21/strata-bench/2026-10-21-community-unknown-b021/results.json"),
             ("0.2.2", "2026-10-21-v0.2.2/strata-bench/2026-10-21-community-unknown-b022/results.json"),
             ("0.2.3.1", "2026-10-23-v0.2.3.1/strata-bench/2026-10-23-community-unknown-b023/results.json"),
             ("0.2.8", "2026-10-31-v0.2.8/strata-bench/2026-10-31-community-unknown-b028/results.json"),
             ("0.2.11", "2026-11-05-v0.2.11/strata-bench/2026-11-05-community-unknown-t-neu/results.json"),
             ("0.2.12", "2026-11-08-v0.2.12/strata-bench/2026-11-08-community-unknown-t-neu/results.json"),
             ("0.2.13", "2026-11-09-v0.2.13/strata-bench/2026-11-09-community-unknown-t-neu/results.json")]


def versionen(d, sp):
    en = sp == "en"
    werte = [strata_bench(os.path.join(d, p)) for _, p in VERSIONEN]
    n = len(werte)
    s = Svg()
    zahlwort = {8: ("Eight", "Acht"), 9: ("Nine", "Neun"), 10: ("Ten", "Zehn")}.get(n, (str(n), str(n)))
    titel = f"{zahlwort[0]} Strata releases on the same card: nothing got slower" if en else f"{zahlwort[1]} Strata-Versionen auf derselben Karte: nichts wurde langsamer"
    kopf(s, "Flash-Next 125B IQ3_XXS · RX 7900 XTX · tools/strata_bench.py --long", titel)
    felder = ((L, 456, (("agent", STAHL, True, "agent" if en else "Agent"), ("chat", ACC, False, "chat" if en else "Chat")), 100, 20,
               "A · Decode · tokens/s" if en else "A · Schreiben · Token/s", "median per release · higher is faster" if en else "Median je Version · höher ist schneller", True),
              (544, R, (("32K", PETROL, True, "32K"), ("16K", STAHL, True, "16K"), ("4K", ACC, False, "4K")), 1400, 200,
               "B · Prompt reading · tokens/s" if en else "B · Prompt einlesen · Token/s", "by prompt length · higher is faster" if en else "nach Prompt-Länge · höher ist schneller", False))
    for x0, x1, reihen, vmax, schritt, was, hilfe, jeder in felder:
        feld(s, x0, 104, was, hilfe)
        p = Hoch(s, x0, x1, 144, 384, vmax)
        p.achse(schritt, sp)
        X = lambda i: x0 + 24 + i * (x1 - x0 - 24 - 56) / (n - 1)
        for i, (name, _) in enumerate(VERSIONEN):
            s.line(X(i), 384, X(i), 388, ACHSE)
            s.text(X(i), 400, name, 8, MUTED, "mono", "middle")
        marken = []
        for k, (schl, farbe, hohl, name) in enumerate(reihen):
            ys = [w[schl] for w in werte]
            s.zug([(X(i), p.Y(v)) for i, v in enumerate(ys)], farbe)
            for i, v in enumerate(ys):
                s.punkt(X(i), p.Y(v), farbe, hohl, r=3.5)
                if jeder:
                    s.text(X(i), p.Y(v) + (-9 if k == 0 else 17), z(v, sp), 8.5, farbe, "mono", "middle")
            marken.append((p.Y(ys[-1]), farbe, name, None if jeder else z(ys[-1], sp)))
        endmarken(s, X(n - 1) + 12, marken)
    s.text(L + 24, 344, "0.2.1's worker plan for hybrid CPUs lifted decode." if en else "Der Worker-Plan von 0.2.1 hob das Schreibtempo.", 15, INK, "serif", kursiv=True)
    h = fuss(s, 424, None, "median per run · from 0.2.3.1: --kv-resident 32768 and 9 GiB conversation cache · 0.2.8 measured with the NAS services stopped, 0.2.11–0.2.13 with them running · data: messen/daten/<date>-v<release>/strata-bench/" if en else
             "Median je Lauf · ab 0.2.3.1: --kv-resident 32768 und 9 GiB Gesprächs-Cache · 0.2.8 mit gestoppten NAS-Diensten gemessen, 0.2.11–0.2.13 mit laufenden · Daten: messen/daten/<Datum>-v<Version>/strata-bench/")
    return "versionen", titel, ("Chat and agent decode speed and prompt reading speed at 4K, 16K and 32K for Strata releases 0.2.0-beta to 0.2.13 on one RX 7900 XTX; all series stay level or rise slightly." if en else
                                "Schreibtempo für Chat und Agent und Einlesetempo bei 4K, 16K und 32K für die Strata-Versionen 0.2.0-beta bis 0.2.13 auf einer RX 7900 XTX; alle Reihen bleiben gleich oder steigen leicht."), s, h


def docker_image(d, sp):
    en = sp == "en"
    reihen = [("0.2.1", "2026-10-21/standard-v1/docker-default/results.json", MUTED),
              ("0.2.2", "2026-10-21-v0.2.2/standard-v1/docker-image-0.2.2-default/results.json", MUTED),
              ("0.2.3", "2026-10-23-v0.2.3.1/standard-v1/docker-image-0.2.3-default/results.json", STAHL),
              ("tuned" if en else "abgestimmt", "2026-10-23-v0.2.3.1/standard-v1/package-0.2.3.1/results.json", ACC)]
    werte = [standard(os.path.join(d, p)) for _, p, _ in reihen]
    s = Svg()
    titel = "With 0.2.3 the unchanged Docker image caught up with the tuned config" if en else "Mit 0.2.3 holt das unveränderte Docker-Image die abgestimmte Konfiguration ein"
    kopf(s, "Strata rocm-gfx110x image · RX 7900 XTX (gfx1100) · standard-v1" if en else "Strata-Image rocm-gfx110x · RX 7900 XTX (gfx1100) · standard-v1", titel)
    feld(s, L, 104, "Prompt reading · tokens/s" if en else "Prompt einlesen · Token/s", "median of 3 · higher is faster" if en else "Median aus 3 · höher ist schneller")
    p = Hoch(s, L, R, 144, 384, 1400)
    p.achse(200, sp)
    for g, (fall, name) in enumerate((("prompt-4k", "4K prompt" if en else "4K-Prompt"), ("prompt-16k", "16K prompt" if en else "16K-Prompt"))):
        gm = L + (g + 0.5) * (R - L) / 2
        for i, ((kurz, _, farbe), w) in enumerate(zip(reihen, werte)):
            mitte = gm + (i - 1.5) * 80
            v = w[(fall, "prompt_tps")]
            p.balken(mitte, 64, v, farbe, z(v, sp), farbe == ACC, farbe == ACC)
            s.text(mitte, 400, kurz, 9, ACC if farbe == ACC else MUTED, "mono", "middle")
        s.text(gm, 422, name, 12, INK, "sans", "middle", 600)
    s.text(L + 24, 172, "From 0.2.3 the engine finds its gfx1100 table by itself." if en else "Ab 0.2.3 findet die Engine ihre gfx1100-Tabelle selbst.", 15, INK, "serif", kursiv=True)
    h = fuss(s, 444, (("balken", MUTED, "unchanged image 0.2.1, 0.2.2" if en else "unverändertes Image 0.2.1, 0.2.2"), ("balken", STAHL, "unchanged image 0.2.3" if en else "unverändertes Image 0.2.3"),
                      ("balken", ACC, "release packages 0.2.3.1 with the tuned run config" if en else "Release-Pakete 0.2.3.1 mit abgestimmter Konfiguration")),
             "strata bench run --suite standard-v1 · the 0.2.13 Linux image switches the table off again, see the 9 Nov follow-up (STRATA_HIPBLASLT_TABLE=on) · data: messen/daten/2026-10-21*/ and 2026-10-23-v0.2.3.1/standard-v1/" if en else
             "strata bench run --suite standard-v1 · das Linux-Image 0.2.13 schaltet die Tabelle wieder ab, siehe Nachtrag vom 9.11. (STRATA_HIPBLASLT_TABLE=on) · Daten: messen/daten/2026-10-21*/ und 2026-10-23-v0.2.3.1/standard-v1/")
    return "docker-image", titel, ("Prompt reading speed at 4K and 16K for the unchanged Docker images 0.2.1, 0.2.2 and 0.2.3 against the tuned run config; at 16K the 0.2.3 image reaches the tuned config's 1,200 tokens per second." if en else
                                   "Einlesetempo bei 4K und 16K für die unveränderten Docker-Images 0.2.1, 0.2.2 und 0.2.3 gegen die abgestimmte Konfiguration; bei 16K erreicht das Image 0.2.3 deren 1.200 Token je Sekunde."), s, h


def kontext(d, sp):
    en = sp == "en"
    w = strata_bench(os.path.join(d, VERSIONEN[2][1]))
    n128 = next(r for r in json.load(open(os.path.join(d, "2026-10-21-v0.2.2/needles-32k-128k.json"))) if r["length"] == "128k" and r["depth"] == 10)
    n250 = next(r for r in json.load(open(os.path.join(d, "needles-250k.json"))) if r["depth"] == 10)
    pts = [(4019, w["ttft_4K"], "4K"), (16000, w["ttft_16K"], "16K"), (32049, w["ttft_32K"], "32K"),
           (n128["prompt_tokens"], n128["seconds"], "128K"), (n250["prompt_tokens"], n250["seconds"], "250K")]
    s = Svg()
    titel = "Waiting for the first word as the prompt grows" if en else "Wartezeit bis zum ersten Wort bei wachsendem Prompt"
    kopf(s, "Flash-Next 125B IQ3_XXS · RX 7900 XTX · fresh prompts, nothing reused" if en else "Flash-Next 125B IQ3_XXS · RX 7900 XTX · frische Prompts, nichts wiederverwendet", titel)
    feld(s, L, 104, "Time to first token · seconds" if en else "Zeit bis zum ersten Token · Sekunden", "lower is faster · the needle was found every time" if en else "niedriger ist schneller · die Nadel wurde jedes Mal gefunden")
    p = Hoch(s, L, R, 144, 384, 250)
    p.achse(50, sp)
    X = lambda v: L + 8 + v / 262144 * (R - L - 40)
    s.zug([(X(x), p.Y(y)) for x, y, _ in pts], ACC)
    for x, y, name in pts:
        s.line(X(x), 384, X(x), 388, ACHSE)
        s.text(X(x), 400, name, 9, MUTED, "mono", "middle")
        s.punkt(X(x), p.Y(y), ACC)
        s.text(X(x), p.Y(y) - 10, f"{z(y, sp)} s" if y < 90 else f"{z(y / 60, sp)} min", 9, ACC, "mono", "middle", 600)
    s.text((L + R) / 2, 420, ("prompt length (tokens)" if en else "Prompt-Länge (Token)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
    s.text(X(140000), p.Y(40), "Almost linear: about 0.85 s per 1,000 tokens." if en else "Fast linear: rund 0,85 s je 1.000 Token.", 15, INK, "serif", kursiv=True)
    h = fuss(s, 444, None, "4K–32K: strata_bench.py (Strata 0.2.2) · 128K and 250K: needle_bench.py (0.2.2, 0.1.44.1) · the conversation cache keeps an agent session from paying this again on every turn" if en else
             "4K–32K: strata_bench.py (Strata 0.2.2) · 128K und 250K: needle_bench.py (0.2.2, 0.1.44.1) · der Gesprächs-Cache erspart einer Agentensitzung, das in jeder Runde neu zu zahlen")
    return "kontext", titel, ("Time to first token for fresh prompts: 5.5 seconds at 4K, 26 seconds at 32K, 1.8 minutes at 128K and 3.6 minutes at 250K tokens." if en else
                              "Zeit bis zum ersten Token bei frischen Prompts: 5,5 Sekunden bei 4K, 26 Sekunden bei 32K, 1,8 Minuten bei 128K und 3,6 Minuten bei 250K Token."), s, h


def speicher(d, sp):
    en = sp == "en"
    m = json.load(open(os.path.join(d, "2026-10-23-v0.2.3.1/memory.json"), encoding="utf-8"))
    ram = [("Strata engine" if en else "Strata-Engine", m["strata_rss_gib"], ACC), ("NAS services, kernel" if en else "NAS-Dienste, Kernel", m["ram_total_gib"] - m["strata_rss_gib"] - m["ram_available_gib"], STAHL),
           ("available" if en else "verfügbar", m["ram_available_gib"], None)]
    vram = [("expert cache" if en else "Experten-Cache", m["expert_cache_gib"], ACC), ("MTP draft" if en else "MTP-Entwurf", m["mtp_gib"], GOLD),
            ("dense, KV, work" if en else "dicht, KV, Arbeit", m["vram_used_gib"] - m["expert_cache_gib"] - m["mtp_gib"], PETROL),
            ("free" if en else "frei", m["vram_total_gib"] - m["vram_used_gib"], None)]
    s = Svg()
    titel = "Where the memory goes with the 125B model loaded" if en else "Wohin der Speicher geht, wenn das 125B-Modell geladen ist"
    kopf(s, "Flash-Next 125B IQ3_XXS loaded and idle · Strata 0.2.3.1 · 256K context" if en else "Flash-Next 125B IQ3_XXS geladen und ruhend · Strata 0.2.3.1 · 256K Kontext", titel)
    X = lambda v: L + v / 64 * (R - L)
    for v in range(0, 61, 10):
        s.line(X(v), 132, X(v), 324, GITTER if v else ACHSE)
        s.text(X(v), 340, str(v), 9, MUTED, "mono", "middle")
    s.text((L + R) / 2, 360, "GIB", 8, MUTED, "mono", "middle", sperr="0.14em")
    for y, was, teile, innen in ((132, f"RAM · {z(m['ram_total_gib'], sp)} GiB", ram, True), (236, f"VRAM · {z(m['vram_total_gib'], sp)} GiB", vram, False)):
        s.text(L + 8, y + 9, was.upper(), 8.5, MUTED, "mono", weight=500, sperr="0.14em")
        links, yb = 0, y + 24
        for i, (name, wert, farbe) in enumerate(teile):
            if farbe:
                s.rect(X(links), yb, X(wert) - L, 56, farbe)
            else:
                s.rect(X(links), yb, X(wert) - L, 56, MUTED, deck=0.06, strich="3,2")
            if innen or i == 0:
                mx = X(links + wert / 2)
                s.text(mx, yb + 26, name, 11, INK, "sans", "middle", 600)
                s.text(mx, yb + 42, z(wert, sp), 9, farbe or MUTED, "mono", "middle", 600 if farbe == ACC else None)
            links += wert
        if not innen:  # schmale Teile rechts neben dem Balken benennen
            x = X(links) + 24
            for j, (name, wert, farbe) in enumerate(teile[1:]):
                yy = yb + 14 + j * 16
                if farbe:
                    s.rect(x, yy - 9, 16, 10, farbe, rx=2)
                else:
                    s.rect(x, yy - 9, 16, 10, MUTED, deck=0.06, rx=2, strich="3,2")
                s.text(x + 24, yy, name, 10, INK, "sans")
                s.text(x + 150, yy, z(wert, sp), 9, MUTED, "mono", "end")
            s.text(R, yb + 34, "With 64 GB of RAM this is about the limit." if en else "Mit 64 GB RAM ist das etwa die Grenze.", 15, INK, "serif", "end", kursiv=True)
    h = fuss(s, 384, None, "measured 23 Oct 2026 · /proc, amdgpu mem_info_vram_used, engine log · dense/KV/work = used − expert cache − draft · data: messen/daten/2026-10-23-v0.2.3.1/memory.json" if en else
             "gemessen am 23.10.2026 · /proc, amdgpu mem_info_vram_used, Engine-Log · dicht/KV/Arbeit = belegt − Experten-Cache − Entwurf · Daten: messen/daten/2026-10-23-v0.2.3.1/memory.json")
    return "speicher", titel, ("Of 62.3 GiB RAM the Strata engine holds 44.6, NAS services and kernel 10.2, and 7.5 stay available; of 24 GiB VRAM the expert cache takes 17.3, the MTP draft 1.0, everything else 5.3, and 0.4 stay free." if en else
                               "Von 62,3 GiB RAM hält die Strata-Engine 44,6, NAS-Dienste und Kernel 10,2, verfügbar bleiben 7,5; von 24 GiB VRAM nimmt der Experten-Cache 17,3, der MTP-Entwurf 1,0, alles Übrige 5,3, frei bleiben 0,4."), s, h


NAMEN = {"faber": "faber (MoE)", "velox": "velox (MoE)", "qwen27": ("Qwen3.8-27B (dense)", "Qwen3.8-27B (dicht)"), "gemma31": ("Gemma 4 31B (dense)", "Gemma 4 31B (dicht)")}


def modellname(m, sp):
    n = NAMEN[m]
    return n if isinstance(n, str) else n[0 if sp == "en" else 1]


def dicht_moe(d, sp):
    en = sp == "en"
    daten = json.load(open(os.path.join(d, "2026-11-14-erfinden/nacht.json"), encoding="utf-8"))["modelle"]
    s = Svg()
    titel = "Dense models on the same card: half the speed, no better results" if en else "Dichte Modelle auf derselben Karte: halb so schnell, nicht besser"
    kopf(s, "RX 7900 XTX · all dense weights in VRAM · night run 13/14 Nov 2026" if en else "RX 7900 XTX · dichte Gewichte ganz im VRAM · Nachtlauf 13./14.11.2026", titel)
    feld(s, L, 104, "Graded tasks passed (of 102) against decode speed" if en else "Bestandene Aufgaben (von 102) gegen Schreibtempo",
         "further right is faster, further up is better · the task axis starts at 88" if en else "weiter rechts ist schneller, weiter oben ist besser · die Aufgabenachse beginnt bei 88")
    p = Hoch(s, L, R, 144, 384, 100, 88)
    p.achse(2, sp)
    X = lambda v: L + (v - 20) / 70 * (R - L)
    for v in range(30, 91, 10):
        s.line(X(v), 144, X(v), 384)
        s.text(X(v), 400, str(v), 9, MUTED, "mono", "middle")
    s.text(X(20), 400, "20", 9, MUTED, "mono", "middle")
    s.text((L + R) / 2, 420, ("decode, long answer (tokens/s, quiet card profile)" if en else "Schreiben, lange Antwort (Token/s, Kartenprofil leise)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
    for m, w in daten.items():
        moe = m in ("faber", "velox")
        x, y = X(w["schreiben_leise"]), p.Y(w["punkte"]["gesamt"])
        s.punkt(x, y, ACC if moe else STAHL, not moe, r=6)
        oben = m in ("gemma31", "velox")
        s.text(x + 14, y + (-14 if oben else 2), modellname(m, sp), 11, ACC if moe else INK, "sans", weight=600)
        s.text(x + 14, y + (-1 if oben else 15), f"{z(w['schreiben_leise'], sp)} tok/s · {w['punkte']['gesamt']}/102", 9, MUTED, "mono")
    h = fuss(s, 444, (("punkt", ACC, "MoE, experts split between VRAM and RAM (Strata 0.2.12)" if en else "MoE, Experten auf VRAM und RAM verteilt (Strata 0.2.12)"),
                      ("punkt-hohl", STAHL, "dense, Q4 (llama.cpp Vulkan)" if en else "dicht, Q4 (llama.cpp Vulkan)")),
             "102 auto-graded tasks, bench.py medians · German and judgement scores are in the table below the chart · data: messen/daten/2026-11-14-erfinden/nacht.json" if en else
             "102 automatisch bewertete Aufgaben, Mediane aus bench.py · Deutsch und Urteil stehen in der Tabelle unter dem Diagramm · Daten: messen/daten/2026-11-14-erfinden/nacht.json")
    return "dicht-moe", titel, ("Four models on one card: the two MoE models write at 64 and 74 tokens per second and pass 96 and 97 of 102 tasks, the two dense models write at 35 and 36 and pass 97 and 92." if en else
                                "Vier Modelle auf einer Karte: die beiden MoE-Modelle schreiben mit 64 und 74 Token je Sekunde und bestehen 96 und 97 von 102 Aufgaben, die beiden dichten schreiben mit 35 und 36 und bestehen 97 und 92."), s, h


def erfinden(d, sp):
    en = sp == "en"
    daten = json.load(open(os.path.join(d, "2026-11-14-erfinden/probe.json"), encoding="utf-8"))["modelle"]
    bereiche = [("ort", "town → state", "Gemeinde → Land"), ("befehl", "command option", "Befehlsoption"), ("begriff", "theorem, law", "Satz, Gesetz"),
                ("werk", "book → author", "Buch → Autor"), ("werkzeug", "agent tool, parameter", "Agentenwerkzeug")]
    summe = lambda x, f: sum(v[f] for v in x.values())
    s = Svg()
    titel = "Four rules in the system prompt make the models say “I don't know”" if en else "Vier Regeln im Systemprompt bringen die Modelle zu „weiß ich nicht“"
    kopf(s, "RX 7900 XTX · 5 areas × 8 made-up things × 3 rounds · temperature 0.7" if en else "RX 7900 XTX · 5 Bereiche × 8 erfundene Dinge × 3 Runden · Temperatur 0,7", titel)
    for i, m in enumerate(("faber", "velox", "qwen27", "gemma31")):
        x0, y0 = (L, 544)[i % 2], (104, 320)[i // 2]
        o, mi = daten[m]["ohne_regeln"], daten[m]["mit_regeln"]
        pz = lambda x: round(100 * summe(x, "erfunden_erkannt") / summe(x, "erfunden_n"))
        s.text(x0, y0, modellname(m, sp), 12, INK, "sans", weight=600)
        s.text(x0 + 384, y0, f"{pz(o)} % → {pz(mi)} %", 11, ACC, "mono", "end", 600)
        s.text(x0, y0 + 15, f"{'real things answered correctly' if en else 'Echtes richtig beantwortet'}: {summe(o, 'echt_richtig')}/{summe(o, 'echt_n')} → {summe(mi, 'echt_richtig')}/{summe(mi, 'echt_n')}", 8.5, MUTED, "mono")
        X = lambda v: x0 + 136 + v * 9.5
        yu = y0 + 36 + 5 * 24
        for v in (0, 6, 12, 18, 24):
            s.line(X(v), y0 + 28, X(v), yu, GITTER)
            s.text(X(v), yu + 14, str(v), 9, MUTED, "mono", "middle")
        s.line(X(0) - 8, yu, X(24) + 8, yu, ACHSE)
        for j, (b, b_en, b_de) in enumerate(bereiche):
            y = y0 + 44 + j * 24
            a, e = o[b]["erfunden_erkannt"], mi[b]["erfunden_erkannt"]
            s.text(x0 + 120, y + 3.5, b_en if en else b_de, 10, INK, "sans", "end")
            s.line(X(a), y, X(e), y, f'stroke="{MUTED}" stroke-opacity="0.5" stroke-width="1.5"')
            s.punkt(X(a), y, MUTED, True, r=4.5)
            s.punkt(X(e), y, ACC, r=4.5)
            lo, hi = sorted(((a, MUTED), (e, ACC)))
            if hi[0] - lo[0] >= 3:
                s.text(X(lo[0]) - 10, y + 3, str(lo[0]), 8.5, lo[1], "mono", "end")
            s.text(X(hi[0]) + 10, y + 3, str(hi[0]), 8.5, hi[1], "mono", weight=600 if hi[1] == ACC else None)
    s.text(W / 2, 524, ("made-up questions answered with “I don't know” (of 24 per area)" if en else "erfundene Fragen mit „weiß ich nicht“ beantwortet (von 24 je Bereich)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
    h = fuss(s, 544, (("punkt-hohl", MUTED, "without rules" if en else "ohne Regeln"), ("punkt", ACC, "with the four rules" if en else "mit den vier Regeln")),
             "messen/halluzination.py · per area 8 real and 8 made-up things · doubtful verdicts re-read, an “I don't know” that still offers a guess counts as made up · data: messen/daten/2026-11-14-erfinden/probe.json" if en else
             "messen/halluzination.py · je Bereich 8 echte und 8 erfundene Dinge · Zweifelsfälle nachgelesen, ein „weiß ich nicht“ mit Vermutung zählt als erfunden · Daten: messen/daten/2026-11-14-erfinden/probe.json")
    return "erfinden", titel, ("For four models and five areas, how many of 24 made-up questions were answered with I don't know, without and with four rules in the system prompt; overall recognition rises from 29–60 percent to 88–99 percent." if en else
                               "Für vier Modelle und fünf Bereiche, wie viele von 24 erfundenen Fragen mit weiß ich nicht beantwortet wurden, ohne und mit vier Regeln im Systemprompt; insgesamt steigt die Erkennung von 29–60 auf 88–99 Prozent."), s, h


def urteil(d, sp):
    en = sp == "en"
    daten = json.load(open(os.path.join(d, "2026-11-14-erfinden/urteil.json"), encoding="utf-8"))["lagen"]
    lagen = {"zahl_weicht_ab": (("number deviates,", "order says stop"), ("Zahl weicht ab,", "Auftrag sagt Stopp")),
             "werkzeug_fehlt": (("announced tool", "is missing"), ("angekündigtes", "Werkzeug fehlt")),
             "lauf_bricht_ab": (("job aborts,", "nobody awake"), ("Lauf bricht ab,", "niemand wach"))}
    worte = {"gut": ("salbei", "good", "gut"), "grenzfall": ("gold", "borderline", "Grenzfall"), "schlecht": ("rose", "bad", "schlecht")}
    s = Svg()
    titel = "faber as an operations agent: ten rounds show what three rounds hide" if en else "faber als Betriebsagent: zehn Runden zeigen, was drei verbergen"
    kopf(s, "Flash-Next 125B IQ3_XXS · Strata 0.2.12 · temperature 0.7 · every answer read" if en else "Flash-Next 125B IQ3_XXS · Strata 0.2.12 · Temperatur 0,7 · jede Antwort gelesen", titel)
    feld(s, L, 104, "Answers per situation (of 10)" if en else "Antworten je Lage (von 10)", "the same situation ten times" if en else "dieselbe Lage zehnmal",
         "A hard instruction holds; weighing things up does not." if en else "Eine harte Anweisung hält, das Abwägen nicht.", R)
    X = lambda v: 216 + v * (R - 216) / 10
    for v in range(0, 11, 2):
        s.line(X(v), 144, X(v), 368, GITTER if v else ACHSE)
        s.text(X(v), 384, str(v), 9, MUTED, "mono", "middle")
    for i, (l, w) in enumerate(daten.items()):
        y = 164 + i * 68
        for k, zeile in enumerate(lagen[l][0 if en else 1]):
            s.text(200, y + 21 + k * 14, zeile, 11, INK, "sans", "end", 600 if k == 0 else None)
        links = 0
        for f in ("gut", "grenzfall", "schlecht"):
            n = w[f]
            if n:
                ton, w_en, w_de = worte[f]
                s.rect(X(links) + 1, y, X(n) - 216 - 2, 44, TON[ton][0], deck=1, kante=TON[ton][1])
                s.text(X(links + n / 2), y + 27, f"{n} {w_en if en else w_de}", 11, TON[ton][2], "sans", "middle", 600)
            links += n
        xm = X(w["nacht_3_gut"] / 3 * 10)
        s.roh(f'<path d="M{xm - 6:.1f},{y - 13} h12 l-6,10 z" fill="{INK}"/>')
    h = fuss(s, 408, (("ton", "salbei", "good" if en else "gut"), ("ton", "gold", "borderline" if en else "Grenzfall"),
                      ("ton", "rose", "bad: invents capabilities or changes its own configuration" if en else "schlecht: erfindet Fähigkeiten oder ändert die eigene Konfiguration"),
                      ("marke", INK, "share “good” in the night run with 3 rounds" if en else "Anteil „gut“ im Nachtlauf mit 3 Runden")),
             "messen/agent_de.py · data: messen/daten/2026-11-14-erfinden/urteil.json" if en else "messen/agent_de.py · Daten: messen/daten/2026-11-14-erfinden/urteil.json")
    return "urteil", titel, ("Ten answers each for three operating situations: a hard stop instruction is followed 10 of 10 times; with a missing tool 3 are good, 6 borderline, 1 bad; when a job aborts at night 1 is good, 3 borderline, 6 bad." if en else
                             "Je zehn Antworten zu drei Betriebslagen: eine harte Stopp-Anweisung wird 10 von 10 Mal befolgt; bei fehlendem Werkzeug sind 3 gut, 6 Grenzfall, 1 schlecht; bricht ein Lauf nachts ab, ist 1 gut, 3 Grenzfall, 6 schlecht."), s, h


def schichten(d, sp):
    en = sp == "en"
    spalten = ((("rules in the", "system prompt"), ("Regeln im", "Systemprompt")), (("tool returns a ready sentence", "and the allowed steps"), ("Werkzeug liefert fertigen Satz", "und erlaubte Schritte")),
               (("rule-based checker", "(plugin, no language model)"), ("Prüfer aus Regeln", "(Plugin, kein Sprachmodell)")))
    zeilen = ((("made-up facts in words", "(“lies in Bavaria”)"), ("erfundene Fakten in Worten", "(„liegt in Bayern“)")), (("made-up numbers",), ("erfundene Zahlen",)),
              (("announced steps", "without a tool"), ("angekündigte Schritte", "ohne Werkzeug")), (("unknown tool names",), ("unbekannte Werkzeugnamen",)))
    # g = fängt ab, gemessen · u = hilft, nicht gemessen · b = blind · n = nicht zuständig
    art = {"g": ("salbei", "catches it", "fängt es ab"), "u": ("gold", "helps · not measured", "hilft · nicht gemessen"), "b": ("rose", "blind", "blind"), "n": ("neutral", "not its job", "nicht zuständig")}
    zellen = [[("g", "29–60 % → 88–99 %, four models", "29–60 % → 88–99 %, vier Modelle"), ("n", "", ""), ("b", "0 of 269 caught", "0 von 269 erkannt")],
              [("u", "“never invent numbers”", "„nie Zahlen erfinden“"), ("u", "numbers come from code", "Zahlen kommen aus dem Code"), ("g", "", "")],
              [("n", "", ""), ("u", "only allowed steps offered", "nur erlaubte Schritte angeboten"), ("g", "6 of 6 (faber)", "6 von 6 (faber)")],
              [("g", "10–20 → 23–24 of 24", "10–20 → 23–24 von 24"), ("n", "", ""), ("g", "", "")]]
    s = Svg()
    titel = "Three layers against made-up answers, and what each one catches" if en else "Drei Schichten gegen Erfinden, und was jede abfängt"
    kopf(s, "Hermes Agent on Flash-Next 125B · prompt rules, tool answers, rule-based checker" if en else "Hermes Agent auf Flash-Next 125B · Prompt-Regeln, Werkzeugantworten, Prüfer aus Regeln", titel)
    for j, sp_ in enumerate(spalten):
        for k, zeile in enumerate(sp_[0 if en else 1]):
            s.text(304 + j * 212 + 100, 108 + k * 15, zeile, 11, INK, "sans", "middle", 600)
    for i, zl in enumerate(zeilen):
        y = 140 + i * 72
        txt = zl[0 if en else 1]
        for k, zeile in enumerate(txt):
            s.text(L, y + (36 if len(txt) == 1 else 28) + k * 15, zeile, 11, INK if k == 0 else MUTED, "sans", weight=600 if k == 0 else None)
        for j, (a, t_en, t_de) in enumerate(zellen[i]):
            ton, w_en, w_de = art[a]
            x = 304 + j * 212
            s.rect(x, y, 200, 64, TON[ton][0], deck=1 if a != "n" else 0.5, kante=False, rx=3)
            s.rect(x, y, 3, 64, TON[ton][1], deck=1, kante=False)
            detail = t_en if en else t_de
            s.text(x + 16, y + (28 if detail else 36), (w_en if en else w_de).upper(), 9, TON[ton][2], "sans", weight=700, sperr="0.08em")
            if detail:
                s.text(x + 16, y + 45, detail, 8.5, INK, "mono")
    h = fuss(s, 444, None, "numbers in a cell are measured · the tool layer is in use but not measured as a whole · the checker raised 0 false alarms on the other tasks · konfig/hermes-pruefer/ · data: messen/daten/2026-11-14-erfinden/" if en else
             "Zahlen in einer Zelle sind gemessen · die Werkzeugschicht ist im Einsatz, als Ganzes nicht gemessen · der Prüfer meldete in den übrigen Aufgaben 0 Fehlalarme · konfig/hermes-pruefer/ · Daten: messen/daten/2026-11-14-erfinden/")
    return "schichten", titel, ("A matrix of four kinds of made-up content against three layers: prompt rules catch made-up facts and unknown tool names, tool answers help with numbers and steps, and the rule-based checker catches numbers, announced steps and tool names but is blind to made-up facts in words." if en else
                                "Eine Matrix aus vier Arten von Erfundenem gegen drei Schichten: Prompt-Regeln fangen erfundene Fakten und unbekannte Werkzeugnamen ab, Werkzeugantworten helfen bei Zahlen und Schritten, der Prüfer aus Regeln fängt Zahlen, angekündigte Schritte und Werkzeugnamen ab, ist aber blind für erfundene Fakten in Worten."), s, h


def bildmodelle(d, sp):
    en = sp == "en"
    namen = {"z-image-turbo": "Z-Image Turbo", "qwen-image-turbo": "Qwen-Image 2.1 Turbo", "qwen-image": "Qwen-Image 2.1", "chroma": "Chroma1-HD (bf16)"}
    zeilen = [json.loads(x) for x in open(os.path.join(d, "2026-10-23-bilder/bilder.jsonl"), encoding="utf-8")]
    sek = lambda m, kalt: med([x["ergebnis"]["seconds"] for x in zeilen if x["model"] == m and x["kalt"] == kalt and x["ergebnis"].get("success")])
    s = Svg()
    titel = "Picture models on the same card: 8 to 66 seconds per picture" if en else "Bildmodelle auf derselben Karte: 8 bis 66 Sekunden je Bild"
    kopf(s, "ComfyUI 0.42.1 through llama-swap · ROCm 7.2 · RX 7900 XTX · 1344×768 or 1664×928" if en else "ComfyUI 0.42.1 über llama-swap · ROCm 7.2 · RX 7900 XTX · 1344×768 bzw. 1664×928", titel)
    feld(s, L, 104, "Seconds per picture" if en else "Sekunden je Bild", "lower is faster" if en else "niedriger ist schneller",
         "Swapping out the chat model costs 21–27 s, once." if en else "Der Wechsel vom Sprachmodell kostet einmal 21–27 s.", R)
    X = lambda v: 216 + v * (R - 216) / 100
    for v in range(0, 101, 20):
        s.line(X(v), 144, X(v), 368, GITTER if v else ACHSE)
        s.text(X(v), 384, str(v), 9, MUTED, "mono", "middle")
    for i, (m, name) in enumerate(namen.items()):
        y = 160 + i * 52
        warm, kalt = sek(m, False), sek(m, True)
        s.text(200, y + 22, name, 11, INK, "sans", "end", 600)
        s.rect(X(0), y, X(kalt) - 216, 36, MUTED, deck=0.06, strich="3,2")
        s.rect(X(0), y, X(warm) - 216, 36, ACC)
        s.text(X(warm) - 8, y + 21.5, f"{z(warm, sp)} s", 9, ACC, "mono", "end", 600)
        s.text(X(kalt) + 8, y + 21.5, f"{z(kalt, sp)} s", 9, MUTED, "mono")
    h = fuss(s, 408, (("balken", ACC, "warm" if en else "warm"), ("leer", MUTED, "first picture after the chat model" if en else "erstes Bild nach dem Sprachmodell")),
             "llama-swap unloads Strata before it starts ComfyUI · median of 2 warm runs · data: messen/daten/2026-10-23-bilder/" if en else
             "llama-swap entlädt Strata, bevor es ComfyUI startet · Median aus 2 warmen Läufen · Daten: messen/daten/2026-10-23-bilder/")
    return "bildmodelle", titel, ("Seconds per picture for four models, warm and for the first picture after the chat model: Z-Image Turbo 8 and 32, Qwen-Image 2.1 Turbo 12 and 33, Qwen-Image 2.1 34 and 55, Chroma1-HD 66 and 93." if en else
                                  "Sekunden je Bild für vier Modelle, warm und für das erste Bild nach dem Sprachmodell: Z-Image Turbo 8 und 32, Qwen-Image 2.1 Turbo 12 und 33, Qwen-Image 2.1 34 und 55, Chroma1-HD 66 und 93."), s, h


def dflash2(d, sp):
    en = sp == "en"
    s = Svg()
    titel = "DFlash2 looks faster at fixed length, but is slower end to end" if en else "DFlash2 wirkt bei fester Länge schneller, ist am Ende aber langsamer"
    kopf(s, "Strata 0.2.12 · RX 7900 XTX (HIP) · faber · MTP vs DFlash2" if en else "Strata 0.2.12 · RX 7900 XTX (HIP) · faber · MTP gegen DFlash2", titel)
    # gemessen 08.11.2026, messen/daten/2026-11-08-v0.2.12/
    feld(s, L, 104, "A · Fixed 900-token test · decode tokens/s" if en else "A · Fester 900-Token-Test · Schreiben Token/s", "median over 3 prompts · higher is faster" if en else "Median über 3 Prompts · höher ist schneller")
    p = Hoch(s, L, 456, 144, 384, 100)
    p.achse(20, sp)
    for g, (name, mtp, df, plus) in enumerate(((("Quiet clocks" if en else "Profil leise"), 83.0, 92.6, 10), (("Max clocks" if en else "Profil max"), 79.0, 90.5, 15))):
        gm = L + (g + 0.5) * 192
        p.balken(gm - 32, 56, mtp, STAHL, z(mtp, sp))
        p.balken(gm + 32, 56, df, ACC, f"{z(df, sp)} · +{plus} %", True)
        s.text(gm, 404, name, 12, INK, "sans", "middle", 600)
    feld(s, 544, 104, "B · Real run, 114 tasks · index, MTP = 100" if en else "B · Echter Lauf, 114 Aufgaben · Index, MTP = 100",
         "same prompts, natural answer length · tokens and time: lower is better" if en else "gleiche Prompts, natürliche Antwortlänge · Token und Zeit: niedriger ist besser")
    p = Hoch(s, 544, R, 144, 384, 160)
    p.achse(20, sp, fett=100)
    for g, (name, wert, sub, fokus) in enumerate(((("Decode speed" if en else "Schreibtempo"), 101, f"{z(75.6, sp)} → {z(76.1, sp)} tok/s", False),
                                                    (("Output tokens" if en else "Ausgabetoken"), 128, f"{z(72321, sp)} → {z(92268, sp)}", False),
                                                    (("Wall time" if en else "Gesamtzeit"), 116, f"{z(1430, sp)} → {z(1660, sp)} s", True))):
        gm = 544 + (g + 0.5) * 128
        p.balken(gm - 26, 44, 100, STAHL, "100")
        p.balken(gm + 26, 44, wert, ACC, str(wert), True, fokus)
        s.text(gm, 404, name, 12, ACC if fokus else INK, "sans", "middle", 600)
        s.text(gm, 419, sub, 8.5, MUTED, "mono", "middle")
    s.text(560, 164, "Per-token speed is unchanged; answers get longer." if en else "Das Tempo je Token bleibt gleich, die Antworten werden länger.", 15, INK, "serif", kursiv=True)
    h = fuss(s, 444, (("balken", STAHL, "MTP (baseline)" if en else "MTP (Ausgangswert)"), ("balken", ACC, "DFlash2, confidence 0.7" if en else "DFlash2, Konfidenz 0,7")),
             "score 98 vs 96 of 102 auto-graded tasks (both misses: arithmetic) · only 51 of 114 answers identical to MTP · own measurements, 8 Nov 2026 · single XTX · data: messen/daten/2026-11-08-v0.2.12/" if en else
             "98 gegen 96 von 102 automatisch bewerteten Aufgaben (beide Fehler: Rechnen) · nur 51 von 114 Antworten gleich wie mit MTP · eigene Messung, 08.11.2026 · eine XTX · Daten: messen/daten/2026-11-08-v0.2.12/")
    return "dflash2-0.2.12", titel, ("In a fixed 900-token decode test DFlash2 is 10 to 15 percent faster than MTP, but in a real 114-task run its per-token speed is unchanged while answers get 28 percent longer, so total wall time rises 16 percent." if en else
                                     "Im festen 900-Token-Test schreibt DFlash2 10 bis 15 Prozent schneller als MTP, im echten Lauf mit 114 Aufgaben bleibt das Tempo je Token gleich, die Antworten werden 28 Prozent länger, die Gesamtzeit steigt um 16 Prozent."), s, h


def ohne_switch(d, eintraege):
    """Zieht von den USV-Werten ab, was Switch und PoE-Geräte an derselben USV ziehen (switch.json), und rechnet die Wh neu."""
    ab = json.load(open(os.path.join(d, "2026-11-15-betrieb", "switch.json"), encoding="utf-8"))["abzug_w"]
    for e in eintraege:
        if isinstance(e.get("usv_w"), dict):
            e["usv_w"] = dict(e["usv_w"], mittel=round(e["usv_w"]["mittel"] - ab, 1))
            tps = e.get("tps") or e.get("schreiben_tps_median")
            if tps:
                e["wh_je_1000_token_gesamt"] = round(e["usv_w"]["mittel"] / tps / 3.6, 3)
    return ab


def betrieb(d, sp):
    en = sp == "en"
    o = os.path.join(d, "2026-11-15-betrieb")
    ph = json.load(open(os.path.join(o, "strom-faber.json"), encoding="utf-8"))["phasen"]
    stufen = [x for f in ("dicht70-gpu.json", "dicht70-cpu.json") for x in json.load(open(os.path.join(o, f), encoding="utf-8"))["stufen"] if "fehler" not in x]
    ab = ohne_switch(d, list(ph.values()) + stufen)
    bestes = max((x for x in stufen if x["ngl"] > 0), key=lambda x: x["schreiben_tps_median"])
    cpu = next((x for x in stufen if x["ngl"] == 0), None)
    s = Svg()
    faktor = round(ph["schreiben"]["tps"] / bestes["schreiben_tps_median"])
    whs = z(ph["schreiben"]["wh_je_1000_token_gesamt"], sp)
    titel = f"{whs} Wh per 1,000 written tokens, and a dense 70B is {faktor} times slower" if en else f"{whs} Wh je 1.000 geschriebene Token, und ein dichtes 70B ist {faktor}-mal langsamer"
    kopf(s, "UGREEN iDX6011 Pro + RX 7900 XTX · measured at the UPS · 15 Nov 2026" if en else "UGREEN iDX6011 Pro + RX 7900 XTX · an der USV gemessen · 15.11.2026", titel)
    feld(s, L, 104, "A · Power · watts" if en else "A · Leistung · Watt", "Flash-Next 125B (MoE) · NAS and dock, without the network switch" if en else "Flash-Next 125B (MoE) · NAS und Dock, ohne den Netzwerk-Switch")
    p = Hoch(s, L, 456, 144, 384, 600)
    p.achse(100, sp)
    for g, (schl, name, sub) in enumerate((("leer", "idle" if en else "Leerlauf", "no model" if en else "kein Modell"), ("geladen", "loaded" if en else "geladen", "idle" if en else "ruhend"),
                                           ("schreiben", "writing" if en else "Schreiben", f"{z(ph['schreiben']['tps'], sp)} tok/s"), ("lesen", "reading" if en else "Einlesen", f"{z(ph['lesen']['tps'], sp)} tok/s"))):
        gm = L + (g + 0.5) * 96
        w, k = ph[schl]["usv_w"]["mittel"], ph[schl]["karte_w"]["mittel"]
        p.balken(gm - 20, 36, w, STAHL, z(w, sp, 0))
        p.balken(gm + 20, 36, k, ACC, z(k, sp, 0), True)
        s.text(gm, 404, name, 12, INK, "sans", "middle", 600)
        s.text(gm, 419, sub, 8.5, MUTED, "mono", "middle")
    feld(s, 544, 104, "B · Decode · tokens/s" if en else "B · Schreiben · Token/s", "same card, same NAS · higher is faster" if en else "dieselbe Karte, dasselbe NAS · höher ist schneller")
    p = Hoch(s, 544, R, 144, 384, 80)
    p.achse(20, sp)
    balken = [("MoE 125B", "Flash-Next IQ3_XXS", ph["schreiben"]["tps"], ph["schreiben"]["wh_je_1000_token_gesamt"], True),
              ("dense 70B" if en else "dichtes 70B", f"{bestes['ngl']}/81 {'layers in VRAM' if en else 'Schichten im VRAM'}", bestes["schreiben_tps_median"], bestes.get("wh_je_1000_token_gesamt"), False)]
    if cpu:
        balken.append(("dense 70B" if en else "dichtes 70B", "CPU only" if en else "nur CPU", cpu["schreiben_tps_median"], cpu.get("wh_je_1000_token_gesamt"), False))
    for g, (name, sub, v, wh, fokus) in enumerate(balken):
        gm = 544 + (g + 0.5) * 384 / len(balken)
        p.balken(gm, 56, v, ACC if fokus else STAHL, z(v, sp), fokus, fokus)
        s.text(gm, 404, name, 12, ACC if fokus else INK, "sans", "middle", 600)
        s.text(gm, 419, sub, 8.5, MUTED, "mono", "middle")
        if wh:
            s.text(gm, 433, f"{z(wh, sp, 1)} Wh / 1.000 Token" if not en else f"{z(wh, sp, 1)} Wh / 1,000 tokens", 8.5, ACC if fokus else MUTED, "mono", "middle", 600 if fokus else None)
    s.text(R, 172, "Dense weights must all be read for every token." if en else "Dichte Gewichte werden für jedes Token alle gelesen.", 15, INK, "serif", "end", kursiv=True)
    h = fuss(s, 458, (("balken", STAHL, "NAS and dock at the wall" if en else "NAS und Dock an der Steckdose"), ("balken", ACC, "card alone (sysfs)" if en else "Karte allein (sysfs)")),
             f"UPS values via NUT, the first 45 s of each phase discarded · minus {z(ab, sp, 0)} W for the network switch and its PoE devices on the same UPS (calculated, ±10 W) · dense 70B: Llama 3.3 70B Instruct Q4_K_M, llama.cpp Vulkan, 8K context · messen/betrieb.py, messen/dicht70.py · data: messen/daten/2026-11-15-betrieb/" if en else
             f"USV-Werte über NUT, die ersten 45 s jeder Phase verworfen · abzüglich {z(ab, sp, 0)} W für den Netzwerk-Switch und seine PoE-Geräte an derselben USV (gerechnet, ±10 W) · dichtes 70B: Llama 3.3 70B Instruct Q4_K_M, llama.cpp Vulkan, 8K Kontext · messen/betrieb.py, messen/dicht70.py · Daten: messen/daten/2026-11-15-betrieb/")
    return "betrieb", titel, ("Power at the UPS and at the card for idle, model loaded, writing and reading, and decode speed of the MoE 125B model against a dense 70B model on the same card." if en else
                              "Leistung an der USV und an der Karte für Leerlauf, geladenes Modell, Schreiben und Einlesen, dazu das Schreibtempo des MoE-125B-Modells gegen ein dichtes 70B-Modell auf derselben Karte."), s, h


def werksmodell(d, sp):
    en = sp == "en"
    st = {x["stufe"]: x for x in json.load(open(os.path.join(d, "2026-11-15-betrieb", "werksmodell.json"), encoding="utf-8"))["stufen"]}
    ab = ohne_switch(d, list(st.values()))
    faktor = round(st["xtx-vulkan"]["schreiben_tps_median"] / st["ugreen-werk"]["schreiben_tps_median"])
    s = Svg()
    titel = f"UGREEN's built-in model writes {faktor} times faster on the card in the dock" if en else f"UGREENs eingebautes Modell schreibt auf der Karte im Dock {faktor}-mal so schnell"
    kopf(s, "Qwen3.5-35B-A3B Q4_K_M · the file UGOS downloads itself · iDX6011 Pro · 15 Nov 2026" if en else "Qwen3.5-35B-A3B Q4_K_M · die Datei, die UGOS selbst lädt · iDX6011 Pro · 15.11.2026", titel)
    reihen = (("ugreen-werk", "as shipped" if en else "ab Werk", "UGOS server, Arc iGPU" if en else "UGOS-Server, Arc-iGPU", STAHL),
              ("cpu", "CPU only" if en else "nur CPU", "llama.cpp, 6 threads" if en else "llama.cpp, 6 Fäden", STAHL),
              ("xtx-vulkan", "RX 7900 XTX", "llama.cpp Vulkan, dock" if en else "llama.cpp Vulkan, Dock", ACC))
    felder = ((L, 456, lambda x: x["schreiben_tps_median"], 120, 20, "A · Decode · tokens/s" if en else "A · Schreiben · Token/s", "long answer · higher is faster" if en else "lange Antwort · höher ist schneller", True),
              (544, R, lambda x: x["einlesen"]["tps"], 3000, 500, "B · Prompt reading · tokens/s" if en else "B · Prompt einlesen · Token/s", "fresh prompt of about 3,700 tokens · higher is faster" if en else "frischer Prompt mit rund 3.700 Token · höher ist schneller", False))
    for x0, x1, wert, vmax, schritt, was, hilfe, strom in felder:
        feld(s, x0, 104, was, hilfe)
        p = Hoch(s, x0, x1, 144, 384, vmax)
        p.achse(schritt, sp)
        for g, (schl, name, sub, farbe) in enumerate(reihen):
            gm = x0 + (g + 0.5) * (x1 - x0) / 3
            v = wert(st[schl])
            p.balken(gm, 56, v, farbe, z(v, sp), farbe == ACC, farbe == ACC)
            s.text(gm, 404, name, 12, ACC if farbe == ACC else INK, "sans", "middle", 600)
            s.text(gm, 419, sub, 8.5, MUTED, "mono", "middle")
            if strom:
                w, wh = st[schl]["usv_w"]["mittel"], st[schl]["wh_je_1000_token_gesamt"]
                s.text(gm, 433, f"{z(w, sp, 0)} W · {z(wh, sp, 1)} Wh/1k", 8.5, ACC if farbe == ACC else MUTED, "mono", "middle", 600 if farbe == ACC else None)
    s.text(L + 24, 172, "The CPU alone out-writes the iGPU." if en else "Die CPU schreibt schneller als die iGPU.", 15, INK, "serif", kursiv=True)
    h = fuss(s, 458, None, "as shipped = the llama-server (SYCL) that UGOS starts by itself after the download, 4 threads, 7 slots, queried over its Unix socket · W for NAS and dock: UPS reading minus the network switch on the same UPS (calculated, ±10 W), Wh per 1,000 written tokens · messen/werksmodell.py · data: messen/daten/2026-11-15-betrieb/werksmodell.json" if en else
             "ab Werk = der llama-server (SYCL), den UGOS nach dem Download selbst startet, 4 Fäden, 7 Plätze, über seinen Unix-Socket angesprochen · W für NAS und Dock: USV-Wert abzüglich des Netzwerk-Switches an derselben USV (gerechnet, ±10 W), Wh je 1.000 geschriebene Token · messen/werksmodell.py · Daten: messen/daten/2026-11-15-betrieb/werksmodell.json")
    return "werksmodell", titel, ("Decode and prompt reading speed of UGREEN's built-in Qwen 3.5 35B model on three paths: the UGOS server on the Arc iGPU, CPU only, and the RX 7900 XTX in the dock." if en else
                                  "Schreib- und Einlesetempo von UGREENs eingebautem Qwen 3.5 35B auf drei Wegen: UGOS-Server auf der Arc-iGPU, nur CPU, und RX 7900 XTX im Dock."), s, h


def aufbau(d, sp):
    """Schaubild der Anlage: wer mit wem spricht, und was das Haus verlässt."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    s = Svg()
    titel = T("Chat, Agent und Bilder auf einer Karte, und fast nichts verlässt das Haus", "Chat, agent and pictures on one card, and almost nothing leaves the house")
    kopf(s, T("UGREEN iDX6011 Pro · eGPU-Dock · RX 7900 XTX · der Aufbau", "UGREEN iDX6011 Pro · eGPU dock · RX 7900 XTX · the setup"), titel)
    pf = f"pf-{sp}"
    s.roh(f'<defs><marker id="{pf}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M1,1 L7,4 L1,7 z" fill="{MUTED}"/></marker>'
          f'<marker id="{pf}-a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M1,1 L7,4 L1,7 z" fill="{ACC}"/></marker></defs>')

    def zone(x, y, w, h, name, bw):
        s.roh(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{INK}" fill-opacity="0.025" stroke="{INK}" stroke-opacity="0.16" stroke-width="0.8" stroke-dasharray="5,4"/>')
        s.roh(f'<rect x="{x + 12}" y="{y - 6}" width="{bw}" height="12" fill="{PAPER}"/>')
        s.text(x + 18, y + 3, name.upper(), 8, MUTED, "mono", weight=500, sperr="0.14em")

    def pfeil(dpfad, gestrichelt=False, fokus=False):
        farbe = ACC if fokus else MUTED
        s.roh(f'<path d="{dpfad}" fill="none" stroke="{farbe}" stroke-width="{1.6 if fokus else 1.2}"' + (' stroke-dasharray="5,4"' if gestrichelt else "") + f' marker-end="url(#{pf}{"-a" if fokus else ""})"/>')

    def knoten(x, y, marke, name, sub, art="normal", w=160, h=56):
        farbe = {"fokus": ACC, "extern": STAHL}.get(art, INK)
        s.roh(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>')
        s.roh(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{farbe}" fill-opacity="{0.14 if art == "fokus" else 0.04}" stroke="{farbe}" stroke-width="{1.6 if art == "fokus" else 1}"' + (' stroke-dasharray="5,4"' if art == "extern" else "") + "/>")
        s.text(x + 12, y + 16, marke.upper(), 7.5, farbe if art != "normal" else MUTED, "mono", weight=500, sperr="0.14em")
        s.text(x + 12, y + 33, name, 12, INK, "sans", weight=600)
        s.text(x + 12, y + 47, sub, 8.5, MUTED, "mono")

    zone(240, 104, 688, 316, T("im Heimnetz", "in the home network"), 96 if not en else 150)
    zone(728, 124, 184, 280, T("RX 7900 XTX im Dock", "RX 7900 XTX in the dock"), 152 if not en else 176)
    # Pfeile zuerst, dann die Knoten
    pfeil("M 200,160 H 270")                                                     # Geräte -> Open WebUI
    pfeil("M 136,188 V 338", gestrichelt=True)                                   # Geräte -> Messenger-Dienst
    pfeil("M 200,176 H 212 Q 220,176 220,184 V 348 Q 220,356 228,356 H 270")     # Geräte -> Hermes direkt (Browser, im Heimnetz)
    pfeil("M 200,368 H 270", gestrichelt=True)                                   # Messenger-Dienst -> Hermes
    pfeil("M 432,148 H 510")                                                     # Open WebUI -> SearXNG (die Anfrage bleibt im Heimnetz, SearXNG fragt nach außen)
    pfeil("M 400,340 V 236 Q 400,228 408,228 H 464 a 8,8 0 0,1 16,0 H 552 Q 560,228 560,220 V 190")  # Hermes -> SearXNG, mit Brücke über die Linie Open WebUI -> llama-swap
    pfeil("M 432,172 H 464 Q 472,172 472,180 V 348 Q 472,356 480,356 H 510")     # Open WebUI -> llama-swap
    pfeil("M 432,380 H 510")                                                     # Hermes -> llama-swap
    pfeil("M 672,356 H 696 Q 704,356 704,348 V 184 Q 704,176 712,176 H 742", fokus=True)  # llama-swap -> Sprachmodell
    pfeil("M 672,380 H 742")                                                     # llama-swap -> ComfyUI
    knoten(72, 132, T("Geräte", "Devices"), T("Laptop, Handy", "Laptop, phone"), T("Browser, Messenger", "browser, messenger"), w=128)
    knoten(72, 340, T("extern", "external"), T("Messenger-Dienst", "Messenger service"), T("z. B. Signal", "e.g. Signal"), "extern", w=128)
    knoten(272, 132, "Chat", "Open WebUI", T("Konten, Verlauf, Dateien", "accounts, history, files"))
    knoten(512, 132, T("Suche", "Search"), "SearXNG", T("sucht über ein VPN im Netz", "searches the web through a VPN"), "extern")
    knoten(272, 340, "Agent", "Hermes Agent", T("Werkzeuge, Aufgaben, Bilder", "tools, tasks, pictures"))
    knoten(512, 340, T("Weiche", "Switch"), "llama-swap", T("ein Modell zur Zeit", "one model at a time"))
    knoten(744, 148, T("Sprache", "Language"), "Flash-Next 125B", T("Strata · 67 Token/s · 256K", "Strata · 67 tokens/s · 256K"), "fokus", w=152)
    knoten(744, 340, T("Bilder", "Pictures"), "ComfyUI", T("8–66 s je Bild", "8–66 s per picture"), w=152)
    y = 448
    s.line(40, y, W - 40, y, 'stroke="#2a2724" stroke-opacity="0.14" stroke-width="0.8"')
    s.roh(f'<path d="M 72,{y + 22} H 104" fill="none" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#{pf})"/>')
    s.text(116, y + 26, T("bleibt im Heimnetz", "stays in the home network"), 10, INK, "sans")
    s.roh(f'<path d="M 280,{y + 22} H 312" fill="none" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="5,4" marker-end="url(#{pf})"/>')
    s.text(324, y + 26, T("verlässt das Haus", "leaves the house"), 10, INK, "sans")
    s.text(R, y + 27, T("Nur Suchanfragen und Messenger-Nachrichten verlassen das Haus.", "Only search queries and messenger messages leave the house."), 15, INK, "serif", "end", kursiv=True)
    s.text(L, y + 48, T("Open WebUI läuft auf einem zweiten kleinen Rechner im Heimnetz, alles Übrige auf dem NAS · Zugang von unterwegs über einen eigenen Zugang mit Anmeldung",
                        "Open WebUI runs on a second small machine in the home network, everything else on the NAS · access from outside through an own gateway with login"), 8.5, MUTED, "mono")
    return "aufbau", titel, T("Laptop und Handy sprechen im Heimnetz mit Open WebUI und mit Hermes Agent, mit dem Agenten auch über einen Messenger-Dienst; beide fragen llama-swap, das auf der RX 7900 XTX entweder das Sprachmodell oder ComfyUI lädt. Nur Suchanfragen und Messenger-Nachrichten verlassen das Haus.",
                              "Laptop and phone talk to Open WebUI and to Hermes Agent in the home network, to the agent also through a messenger service; both ask llama-swap, which loads either the language model or ComfyUI on the RX 7900 XTX. Only search queries and messenger messages leave the house."), s, 512


def parallel(d, sp):
    """Wer rechnet was: drei Bahnen (Karte im Dock, eingebaute iGPU, CPU und RAM) mit dem, was gleichzeitig läuft."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    n = json.load(open(os.path.join(d, "2026-11-15-betrieb", "nebenlast.json"), encoding="utf-8"))
    st = json.load(open(os.path.join(d, "2026-11-15-betrieb", "strom-faber.json"), encoding="utf-8"))["phasen"]["schreiben"]
    tr, dl = n["transkodieren"], n["download"]
    s = Svg()
    titel = T("Das NAS arbeitet weiter, während das Modell schreibt", "The NAS keeps working while the model writes")
    kopf(s, T("UGREEN iDX6011 Pro · alles gleichzeitig · Modell geladen und unter Last", "UGREEN iDX6011 Pro · everything at once · model loaded and under load"), titel)
    GUT, OFFEN = TON["salbei"][2], TON["gold"][2]
    bahnen = [
        (T("Karte im Dock", "Card in the dock"), "RX 7900 XTX · 24 GB", ACC, [
            (T("Sprachmodell", "Language model"), f"{z(st['tps'], sp)} {T('Token/s', 'tokens/s')}", T("gemessen", "measured"), GUT, True),
            (T("Bildmodelle", "Picture models"), T("8–66 s je Bild, im Wechsel", "8–66 s per picture, in turn"), T("gemessen", "measured"), GUT, False)]),
        (T("Eingebaute iGPU", "Built-in iGPU"), "Intel Arc", STAHL, [
            (T("Video: Transkodierung", "Video: transcoding"), f"{min(tr['waehrend_schreiben_bilder_s'])}–{max(tr['waehrend_schreiben_bilder_s'])} {T('Bilder/s', 'frames/s')} ({T('ohne Last', 'idle')} {tr['ohne_modell_bilder_s'][0]})", T("gemessen", "measured"), GUT, False),
            (T("Fotos: Bilderkennung", "Photos: recognition"), T("Dienst von UGOS, läuft weiter", "UGOS service, keeps running"), T("läuft · nicht gemessen", "runs · not measured"), OFFEN, False)]),
        (T("Prozessor und RAM", "Processor and RAM"), "Core Ultra 7 · 64 GB", INK, [
            (T("Dateifreigaben", "File shares"), f"{z(dl['waehrend_schreiben']['mb_s'], sp, 0)} MB/s ({T('ohne Last', 'idle')} {z(dl['ohne_modell']['mb_s'], sp, 0)})", T("gemessen · per HTTP", "measured · over HTTP"), GUT, False),
            (T("Chat und Websuche", "Chat and web search"), T("Docker · 689 + 139 MiB RAM", "Docker · 689 + 139 MiB RAM"), T("gemessen", "measured"), GUT, False),
            (T("USV-Überwachung", "UPS monitoring"), T("Dienst von UGOS, läuft weiter", "UGOS service, keeps running"), T("läuft · nicht gemessen", "runs · not measured"), OFFEN, False)]),
    ]
    y = 100
    for name, sub, farbe, kaesten in bahnen:
        s.roh(f'<rect x="{L}" y="{y}" width="{R - L}" height="88" rx="8" fill="{INK}" fill-opacity="0.025" stroke="{INK}" stroke-opacity="0.14" stroke-width="0.8"/>')
        s.roh(f'<rect x="{L}" y="{y}" width="4" height="88" fill="{farbe}"/>')
        s.text(L + 20, y + 40, name, 13, INK, "sans", weight=700)
        s.text(L + 20, y + 57, sub, 9, MUTED, "mono")
        breite = (R - 256 - 16 - 12 * (len(kaesten) - 1)) / len(kaesten)
        for i, (titel_, wert, status, sfarbe, fokus) in enumerate(kaesten):
            x = 256 + i * (breite + 12)
            s.roh(f'<rect x="{x:.1f}" y="{y + 12}" width="{breite:.1f}" height="64" rx="6" fill="{PAPER}"/>')
            s.roh(f'<rect x="{x:.1f}" y="{y + 12}" width="{breite:.1f}" height="64" rx="6" fill="{ACC if fokus else INK}" fill-opacity="{0.14 if fokus else 0.04}" stroke="{ACC if fokus else INK}" stroke-opacity="{1 if fokus else 0.45}" stroke-width="{1.6 if fokus else 1}"/>')
            s.text(x + 12, y + 32, titel_, 12, INK, "sans", weight=600)
            s.text(x + 12, y + 48, wert, 8.5, MUTED, "mono")
            s.text(x + 12, y + 64, status.upper(), 7.5, sfarbe, "mono", weight=600, sperr="0.12em")
        y += 100
    h = fuss(s, y + 12, None, T("gemessen am 15.11.2026, während das 125B-Modell durchgehend schrieb · Transkodierung 4K-HEVC nach 1080p-H.264 mit VAAPI · Datei 17,7 GB an einen Arbeitsplatz mit 5 Gbit/s, der die Grenze war · Daten: messen/daten/2026-11-15-betrieb/nebenlast.json",
                                    "measured on 15 Nov 2026 while the 125B model was writing continuously · transcoding 4K HEVC to 1080p H.264 with VAAPI · 17.7 GB file to a client with 5 Gbit/s, which was the limit · data: messen/daten/2026-11-15-betrieb/nebenlast.json"))
    return "parallel", titel, T("Drei Bahnen: Auf der Karte im Dock laufen Sprach- und Bildmodelle, auf der eingebauten iGPU Transkodierung und Bilderkennung, auf Prozessor und RAM Dateifreigaben, Chat, Websuche und USV-Überwachung, alles gleichzeitig.",
                                "Three lanes: language and picture models run on the card in the dock, transcoding and photo recognition on the built-in iGPU, file shares, chat, web search and UPS monitoring on processor and RAM, all at the same time."), s, h


ALLE = (tiefe, mtp_annahme, pool_workers, versionen, docker_image, kontext, speicher, dicht_moe, erfinden, urteil, schichten, bildmodelle, dflash2, betrieb, werksmodell, aufbau, parallel)


def main():
    arg = [a for a in sys.argv[1:] if not a.startswith("--")]
    daten, ziel = arg[0], arg[1]
    png = arg[2] if "--png" in sys.argv else None
    os.makedirs(ziel, exist_ok=True)
    dateien = []
    for f in ALLE:
        for sp in ("en", "de"):
            name, titel, desc, s, h = f(daten, sp)
            slug = f"{name}-{sp}"
            pfad = os.path.join(ziel, slug + ".html")
            with open(pfad, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(seite(slug.replace(".", "-"), sp, titel, desc, s, h))
            dateien.append((pfad, slug))
    print(f"{len(dateien)} HTML-Dateien in {ziel}")
    if png:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            try:
                b = pw.chromium.launch()
            except Exception:  # kein passendes Playwright-Chromium: das installierte Chrome nehmen
                b = pw.chromium.launch(channel="chrome")
            seite_ = b.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2)
            for pfad, slug in dateien:
                seite_.goto("file:///" + os.path.abspath(pfad).replace("\\", "/"), wait_until="networkidle")
                seite_.evaluate("document.fonts.ready")
                seite_.locator("svg").screenshot(path=os.path.join(png, slug + ".png"))
            b.close()
        print(f"{len(dateien)} PNG-Dateien in {png}")


if __name__ == "__main__":
    main()
