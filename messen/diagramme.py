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

    def raute(self, x, y, farbe, r=5):
        self.e.append(f'<path d="M{x:.1f},{y - r:.1f} l{r},{r} l{-r},{r} l{-r},{-r} z" fill="{farbe}" stroke="{PAPER}" stroke-width="1"/>')

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
            elif art == "raute":
                s.raute(x + 8, y - 4, farbe)
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


TIEFE_DATEI = "tiefe-20261116.jsonl"   # 16.11.2026, Strata 0.2.14; Oktober (0.1.44.1): tiefe-20261017.jsonl
TIEFE_XTX = "tiefe-20261121.jsonl"     # 21.11.2026, Eigenbau strata-xtx (xtx-2) auf Strata 0.2.17 (Label faber-xtx, liber-xtx, faber-xtx-ohne-mtp); 0.2.16: tiefe-20261119.jsonl
XTX_DATEN = "2026-11-21-strata-xtx-0.2.17"    # Nachmessung im Betrieb auf dem Eigenbau
XTX_VER = "0.2.17"                     # Strata-Version, auf der der Eigenbau im Betrieb läuft
XTX_TAG = {"de": "21.11.2026", "en": "21 Nov 2026"}   # Tag der Nachmessung
XTX_VOR = "2026-11-19-strata-xtx-0.2.16"      # Nachmessung auf der Basis 0.2.16, zum Nachschlagen (davor 2026-11-18-strata-xtx auf 0.2.15)


def tiefe_daten(d, datei=TIEFE_DATEI):
    werte = defaultdict(lambda: defaultdict(list))
    for zeile in open(os.path.join(d, datei), encoding="utf-8"):
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
    w["xtx"] = tiefe_daten(d, TIEFE_XTX)["faber-xtx"]
    m_ = lambda label, wert: {t: med([r[wert] for r in rs]) for t, rs in w[label].items()}
    plus = [100 * (m_("mit-mtp", "decode_tps")[t] / m_("ohne-mtp", "decode_tps")[t] - 1) for t in w["mit-mtp"]]
    lesen16 = min(v for t, v in list(m_("mit-mtp", "prompt_tps").items()) + list(m_("ohne-mtp", "prompt_tps").items()) if t >= 16384)
    p_lo, p_hi, l16 = round(min(plus)), round(max(plus)), int(lesen16 // 100 * 100)
    x16 = int(min(v for t, v in m_("xtx", "prompt_tps").items() if t >= 16384) // 100 * 100)
    mal = [m_("xtx", "prompt_tps")[t] / m_("mit-mtp", "prompt_tps")[t] for t in w["xtx"]]
    s = Svg()
    titel = (f"My own build reads {z(min(mal), sp, 1)} to {z(max(mal), sp, 1)} times as fast from 1K to 248K tokens of context" if en else
             f"Der Eigenbau liest von 1K bis 248K Token Kontext {z(min(mal), sp, 1)}- bis {z(max(mal), sp, 1)}-mal so schnell")
    kopf(s, f"strata-xtx on Strata {XTX_VER} against the 0.2.14 release · Flash-Next 125B IQ3_XXS · RX 7900 XTX over OCuLink x4" if en else
         f"strata-xtx auf Strata {XTX_VER} gegen das Release 0.2.14 · Flash-Next 125B IQ3_XXS · RX 7900 XTX über OCuLink x4", titel)
    reihen = (("xtx", ACC, False, "own build" if en else "Eigenbau"), ("mit-mtp", STAHL, False, "release" if en else "Release"),
              ("ohne-mtp", STAHL, True, "without MTP" if en else "ohne MTP"))
    felder = ((L, 456, "decode_tps", 80, 20, "A · Decode · tokens/s" if en else "A · Schreiben · Token/s",
               "256 new tokens after a fresh prompt · higher is faster" if en else "256 neue Token nach frischem Prompt · höher ist schneller",
               f"MTP adds {p_lo}–{p_hi} % at every depth." if en else f"MTP bringt {p_lo}–{p_hi} % in jeder Tiefe.", 76),
              (544, R, "prompt_tps", 3200, 400, "B · Prefill · tokens/s" if en else "B · Einlesen · Token/s",
               "reading the fresh prompt · higher is faster" if en else "Einlesen des frischen Prompts · höher ist schneller",
               f"From 16K on above {z(x16, sp)} tokens/s, the release above {z(l16, sp)}." if en else f"Ab 16K über {z(x16, sp)} Token/s, das Release über {z(l16, sp)}.", 560))
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
    h = fuss(s, 444, None, f"UGREEN iDX6011 Pro, 64 GB · own build (strata-xtx on Strata {XTX_VER}, the prompt switches built in) measured {XTX_TAG['en']}, release 0.2.14 with and without MTP on 16 Nov 2026 · one fresh prompt per run, then 256 new tokens · engine timings, median of 2–3 runs · messen/tiefe.py · data: messen/daten/{TIEFE_XTX} and {TIEFE_DATEI}, October run on 0.1.44.1: tiefe-20261017.jsonl" if en else
             f"UGREEN iDX6011 Pro, 64 GB · Eigenbau (strata-xtx auf Strata {XTX_VER}, die Prompt-Schalter eingebaut) gemessen am {XTX_TAG['de']}, Release 0.2.14 mit und ohne MTP am 16.11.2026 · je Lauf ein frischer Prompt, dann 256 neue Token · Zeiten der Engine, Median aus 2–3 Läufen · messen/tiefe.py · Daten: messen/daten/{TIEFE_XTX} und {TIEFE_DATEI}, Oktober auf 0.1.44.1: tiefe-20261017.jsonl")
    return "tiefe", titel, ("Decode and prefill throughput of my own build against the release with and without the MTP draft head at six context depths from 1K to 248K tokens." if en else
                            "Schreib- und Einlesetempo des Eigenbaus gegen das Release mit und ohne MTP-Kopf in sechs Kontexttiefen von 1K bis 248K Token."), s, h


def mtp_annahme(d, sp):
    en = sp == "en"
    w = tiefe_daten(d)["mit-mtp"]
    s = Svg()
    titel = "Four to five in ten MTP drafts are accepted, at every depth" if en else "Vier bis fünf von zehn MTP-Vorschlägen werden angenommen, in jeder Tiefe"
    kopf(s, "Strata 0.2.14 · Flash-Next 125B IQ3_XXS · RX 7900 XTX", titel)
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
    h = fuss(s, 404, None, f"measured 16 Nov 2026 · 2–3 fresh prompts per depth, 256 new tokens each, drafts summed · messen/tiefe.py · data: messen/daten/{TIEFE_DATEI}" if en else
             f"gemessen am 16.11.2026 · 2–3 frische Prompts je Tiefe, je 256 neue Token, Vorschläge summiert · messen/tiefe.py · Daten: messen/daten/{TIEFE_DATEI}")
    lo, hi = round(min(v for _, v in pts)), round(max(v for _, v in pts))
    return "mtp-annahme", titel, (f"MTP draft acceptance between {lo} and {hi} percent at six context depths from 1K to 248K tokens." if en else
                                  f"MTP-Annahmequote zwischen {lo} und {hi} Prozent in sechs Kontexttiefen von 1K bis 248K Token."), s, h


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
             ("0.2.13", "2026-11-09-v0.2.13/strata-bench/2026-11-09-community-unknown-t-neu/results.json"),
             ("0.2.14", ["2026-11-15-v0.2.14/strata-bench/2026-11-15-community-unknown-t-neu/results.json"]
                        + [f"2026-11-15-v0.2.14/strata-bench-alternating/round{n}-0.2.14.json" for n in (1, 2, 3)]),   # vier Läufe, gezeigt wird der Median
             ("0.2.15", [f"2026-11-16-v0.2.15/strata-bench-alternating/round{n}-0.2.15.json" for n in (1, 2, 3)]),
             ("0.2.16", [f"{XTX_VOR}/strata-bench-alternating/round{n}-release-0.2.16.json" for n in (1, 2, 3)]),   # das unveränderte Release, im Wechsel mit dem Eigenbau (19.11.)
             ("0.2.17", [f"{XTX_DATEN}/strata-bench-alternating/round{n}-release-0.2.17.json" for n in (1, 2, 3)])]   # dasselbe am 21.11.
XTX_BENCH = [f"{XTX_DATEN}/strata-bench-alternating/round{n}-strata-xtx-{XTX_VER}.json" for n in (1, 2, 3)]            # der Eigenbau auf derselben Basis
IN_BETRIEB, GEPRUEFT = "0.2.14", XTX_VER   # letztes Release im Betrieb · Basis des Eigenbaus


def versionen(d, sp):
    en = sp == "en"
    def lauf(p):                                   # ein Lauf oder der Median mehrerer Läufe derselben Version
        ws = [strata_bench(os.path.join(d, q)) for q in ([p] if isinstance(p, str) else p)]
        return {k: med([w[k] for w in ws]) for k in ws[0]}
    werte = [lauf(p) for _, p in VERSIONEN]
    xtx = lauf(XTX_BENCH)
    n = len(werte)
    s = Svg()
    zahlwort = {8: ("Eight", "Acht"), 9: ("Nine", "Neun"), 10: ("Ten", "Zehn"), 11: ("Eleven", "Elf")}.get(n, (str(n), str(n)))
    titel = f"{zahlwort[0]} Strata releases on the same card, and my own build reads prompts about twice as fast" if en else f"{zahlwort[1]} Strata-Versionen auf derselben Karte, und der Eigenbau liest Prompts etwa doppelt so schnell"
    kopf(s, "Flash-Next 125B IQ3_XXS · RX 7900 XTX · tools/strata_bench.py --long", titel)
    felder = ((L, 456, (("agent", STAHL, True, "agent" if en else "Agent"), ("chat", ACC, False, "chat" if en else "Chat")), 100, 20,
               "A · Decode · tokens/s" if en else "A · Schreiben · Token/s", "median per release · higher is faster" if en else "Median je Version · höher ist schneller", True),
              (544, R, (("32K", PETROL, True, "32K"), ("16K", STAHL, True, "16K"), ("4K", ACC, False, "4K")), 2800, 400,
               "B · Prompt reading · tokens/s" if en else "B · Prompt einlesen · Token/s", "by prompt length · higher is faster" if en else "nach Prompt-Länge · höher ist schneller", False))
    for x0, x1, reihen, vmax, schritt, was, hilfe, jeder in felder:
        feld(s, x0, 104, was, hilfe)
        p = Hoch(s, x0, x1, 144, 384, vmax)
        p.achse(schritt, sp)
        X = lambda i: x0 + 24 + i * (x1 - x0 - 24 - 56) / (n - 1)
        s.text(X(0) - 12, 400, "0.2.", 7.5, MUTED, "mono", "end")   # gemeinsames Präfix einmal, sonst laufen ab 12 Versionen die Namen ineinander (21.11.2026)
        for i, (name, _) in enumerate(VERSIONEN):
            s.line(X(i), 384, X(i), 388, ACHSE)
            s.text(X(i), 400, name.removeprefix("0.2."), 7.5, INK if name == IN_BETRIEB else MUTED, "mono", "middle", 600 if name == IN_BETRIEB else None)
            if name in (IN_BETRIEB, GEPRUEFT):
                s.text(X(i), 411, (("to 18 Nov" if en else "bis 18.11.") if name == IN_BETRIEB else ("base" if en else "Basis")), 7.5, MUTED, "sans", "middle")
        marken = []
        for k, (schl, farbe, hohl, name) in enumerate(reihen):
            ys = [w[schl] for w in werte]
            s.zug([(X(i), p.Y(v)) for i, v in enumerate(ys)], farbe)
            for i, v in enumerate(ys):
                s.punkt(X(i), p.Y(v), farbe, hohl, r=3.5)
                if jeder:
                    s.text(X(i), p.Y(v) + (-9 if k == 0 else 17), z(v, sp), 8.5, farbe, "mono", "middle")
            if jeder:
                marken.append((p.Y(ys[-1]), farbe, name, None))
            else:                                  # der Eigenbau auf derselben Basis: Raute über dem letzten Release
                s.line(X(n - 1), p.Y(ys[-1]) - 5, X(n - 1), p.Y(xtx[schl]) + 6, f'stroke="{farbe}" stroke-width="1" stroke-dasharray="2,3"')
                s.raute(X(n - 1), p.Y(xtx[schl]), farbe)
                marken.append((p.Y(xtx[schl]), farbe, name, z(xtx[schl], sp)))
        endmarken(s, X(n - 1) + 12, marken)
        if not jeder:
            s.text(X(n - 1) + 12, p.Y(max(xtx[k_] for k_ in ("4K", "16K", "32K"))) - 22, "strata-xtx", 9, INK, "mono", weight=600)
            s.text(X(n - 1) + 12, p.Y(werte[-1]["16K"]) + 3, f"{z(werte[-1]['32K'], sp)} · {z(werte[-1]['16K'], sp)}", 8.5, STAHL, "mono")
            s.text(X(n - 1) + 12, p.Y(werte[-1]["4K"]) + 3, z(werte[-1]["4K"], sp), 8.5, ACC, "mono")
    s.text(L + 24, 344, "0.2.1's worker plan for hybrid CPUs lifted decode." if en else "Der Worker-Plan von 0.2.1 hob das Schreibtempo.", 15, INK, "serif", kursiv=True)
    h = fuss(s, 424, (("linie", STAHL, "Strata releases, unchanged" if en else "Strata-Releases, unverändert"), ("raute", STAHL, f"my own build strata-xtx on {XTX_VER}" if en else f"Eigenbau strata-xtx auf {XTX_VER}")),
             f"median per run · from 0.2.3.1: --kv-resident 32768 and 9 GiB conversation cache · 0.2.8 measured with the NAS services stopped, from 0.2.11 with them running · 0.2.14: median of four runs · 0.2.15: three runs alternating with 0.2.14 on 16 Nov · 0.2.16: three runs alternating with my own build on 19 Nov · {XTX_VER} and my own build: three runs each, alternating, on {XTX_TAG['en']} · releases were in use up to 0.2.14 (until 18 Nov 2026) · since then my own build runs, now on the base of {XTX_VER} · decode of the own build in the same runs: chat {z(xtx['chat'], sp)}, agent {z(xtx['agent'], sp)} tokens/s · data: messen/daten/<date>-v<release>/strata-bench*/ and <date>-strata-xtx-<release>/strata-bench-alternating/" if en else
             f"Median je Lauf · ab 0.2.3.1: --kv-resident 32768 und 9 GiB Gesprächs-Cache · 0.2.8 mit gestoppten NAS-Diensten gemessen, ab 0.2.11 mit laufenden · 0.2.14: Median aus vier Läufen · 0.2.15: drei Läufe im Wechsel mit 0.2.14 am 16.11. · 0.2.16: drei Läufe im Wechsel mit dem Eigenbau am 19.11. · {XTX_VER} und der Eigenbau: je drei Läufe im Wechsel am {XTX_TAG['de']} · im Betrieb liefen Releases bis 0.2.14 (bis 18.11.2026) · seitdem läuft der Eigenbau, jetzt auf der Basis von {XTX_VER} · Schreibtempo des Eigenbaus in denselben Läufen: Chat {z(xtx['chat'], sp)}, Agent {z(xtx['agent'], sp)} Token/s · Daten: messen/daten/<Datum>-v<Version>/strata-bench*/ und <Datum>-strata-xtx-<Version>/strata-bench-alternating/")
    return "versionen", titel, (f"Chat and agent decode speed and prompt reading speed at 4K, 16K and 32K for Strata releases 0.2.0-beta to {VERSIONEN[-1][0]} on one RX 7900 XTX; decode stays within its scatter, prompt reading at 16K and 32K rises with 0.2.14 and holds since. My own build strata-xtx on {XTX_VER} reads {z(xtx['4K'], sp)}, {z(xtx['16K'], sp)} and {z(xtx['32K'], sp)} tokens per second at 4K, 16K and 32K." if en else
                                f"Schreibtempo für Chat und Agent und Einlesetempo bei 4K, 16K und 32K für die Strata-Versionen 0.2.0-beta bis {VERSIONEN[-1][0]} auf einer RX 7900 XTX; das Schreibtempo bleibt in seiner Streuung, das Einlesen bei 16K und 32K steigt mit 0.2.14 und hält seitdem. Der Eigenbau strata-xtx auf {XTX_VER} liest bei 4K, 16K und 32K {z(xtx['4K'], sp)}, {z(xtx['16K'], sp)} und {z(xtx['32K'], sp)} Token je Sekunde."), s, h


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
    xt = tiefe_daten(d, TIEFE_XTX)["faber-xtx"]
    neu = [(statistics.median(r["prompt_token"] for r in xt[t]), statistics.median(r["prompt_token"] / r["prompt_tps"] for r in xt[t]), n_)
           for t, n_ in ((4096, "4K"), (16384, "16K"), (65536, "64K"), (131072, "128K"), (250000, "250K"))]
    je1000 = neu[-1][1] / neu[-1][0] * 1000
    s = Svg()
    titel = "Waiting for the first word as the prompt grows" if en else "Wartezeit bis zum ersten Wort bei wachsendem Prompt"
    kopf(s, "Flash-Next 125B IQ3_XXS · RX 7900 XTX · fresh prompts, nothing reused" if en else "Flash-Next 125B IQ3_XXS · RX 7900 XTX · frische Prompts, nichts wiederverwendet", titel)
    feld(s, L, 104, "Time to first token · seconds" if en else "Zeit bis zum ersten Token · Sekunden", "lower is faster · the needle was found every time" if en else "niedriger ist schneller · die Nadel wurde jedes Mal gefunden")
    p = Hoch(s, L, R, 144, 384, 250)
    p.achse(50, sp)
    X = lambda v: L + 8 + v / 262144 * (R - L - 40)
    s.zug([(X(x), p.Y(y)) for x, y, _ in pts], STAHL)
    for x, y, name in pts:
        s.line(X(x), 384, X(x), 388, ACHSE)
        s.text(X(x), 400, name, 9, MUTED, "mono", "middle")
        s.punkt(X(x), p.Y(y), STAHL, True)
        if x > 100000:
            s.text(X(x), p.Y(y) - 10, f"{z(y, sp)} s" if y < 90 else f"{z(y / 60, sp)} min", 9, STAHL, "mono", "middle", 600)
    s.zug([(X(x), p.Y(y)) for x, y, _ in neu], ACC)
    for x, y, name in neu:
        s.punkt(X(x), p.Y(y), ACC)
        if x > 50000:
            s.text(X(x), p.Y(y) + (20 if y > 30 else -12), f"{z(y, sp, 0)} s", 9, ACC, "mono", "middle", 600)
    s.text((L + R) / 2, 420, ("prompt length (tokens)" if en else "Prompt-Länge (Token)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
    s.text(X(20000), p.Y(215), (f"Almost linear: 0.85 s per 1,000 tokens then, {z(je1000, sp, 2)} s now." if en else f"Fast linear: damals 0,85 s je 1.000 Token, heute {z(je1000, sp, 2)} s."), 15, INK, "serif", kursiv=True)
    h = fuss(s, 444, (("linie-hohl", STAHL, "Strata 0.2.2, October 2026" if en else "Strata 0.2.2, Oktober 2026"), ("linie", ACC, f"own build strata-xtx on {XTX_VER}, {XTX_TAG['en']}" if en else f"Eigenbau strata-xtx auf {XTX_VER}, {XTX_TAG['de']}")),
             "own build: messen/tiefe.py, median of 2–3 fresh prompts, prompt tokens divided by the engine's reading speed · 4K–32K: strata_bench.py (Strata 0.2.2) · 128K and 250K: needle_bench.py (0.2.2, 0.1.44.1) · the conversation cache keeps an agent session from paying this again on every turn" if en else
             "Eigenbau: messen/tiefe.py, Median aus 2–3 frischen Prompts, Prompt-Token geteilt durch das Einlesetempo der Engine · 4K–32K: strata_bench.py (Strata 0.2.2) · 128K und 250K: needle_bench.py (0.2.2, 0.1.44.1) · der Gesprächs-Cache erspart einer Agentensitzung, das in jeder Runde neu zu zahlen")
    return "kontext", titel, (f"Time to first token for fresh prompts. In October 2026: 5.5 seconds at 4K, 26 seconds at 32K, 1.8 minutes at 128K and 3.6 minutes at 250K tokens. With my own build on {XTX_TAG['en']}: {z(neu[3][1], sp, 0)} seconds at 128K and {z(neu[4][1], sp, 0)} seconds at 250K." if en else
                              f"Zeit bis zum ersten Token bei frischen Prompts. Im Oktober 2026: 5,5 Sekunden bei 4K, 26 Sekunden bei 32K, 1,8 Minuten bei 128K und 3,6 Minuten bei 250K Token. Mit dem Eigenbau am {XTX_TAG['de']}: {z(neu[3][1], sp, 0)} Sekunden bei 128K und {z(neu[4][1], sp, 0)} Sekunden bei 250K."), s, h


def speicher(d, sp):
    en = sp == "en"
    m = json.load(open(os.path.join(d, XTX_DATEN, "memory-faber.json"), encoding="utf-8"))
    lb = json.load(open(os.path.join(d, XTX_DATEN, "memory-liber.json"), encoding="utf-8"))
    dienste = m["ram_total_gib"] - m["strata_rss_gib"] - m["ram_available_gib"]
    rest = m["vram_used_gib"] - m["expert_cache_gib"] - m["mtp_gib"]
    ram = [("Strata engine" if en else "Strata-Engine", m["strata_rss_gib"], ACC), ("NAS services, kernel" if en else "NAS-Dienste, Kernel", m["ram_total_gib"] - m["strata_rss_gib"] - m["ram_available_gib"], STAHL),
           ("available" if en else "verfügbar", m["ram_available_gib"], None)]
    vram = [("expert cache" if en else "Experten-Cache", m["expert_cache_gib"], ACC), ("MTP draft" if en else "MTP-Entwurf", m["mtp_gib"], GOLD),
            ("dense, KV, work" if en else "dicht, KV, Arbeit", m["vram_used_gib"] - m["expert_cache_gib"] - m["mtp_gib"], PETROL),
            ("free" if en else "frei", m["vram_total_gib"] - m["vram_used_gib"], None)]
    s = Svg()
    titel = "Where the memory goes with the original 125B model loaded" if en else "Wohin der Speicher geht, wenn das 125B-Original geladen ist"
    kopf(s, f"Flash-Next 125B IQ3_XXS (faber) loaded and idle · strata-xtx on Strata {XTX_VER} · 256K context" if en else f"Flash-Next 125B IQ3_XXS (faber) geladen und ruhend · strata-xtx auf Strata {XTX_VER} · 256K Kontext", titel)
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
    h = fuss(s, 384, None, f"measured {XTX_TAG['en']} · /proc, amdgpu mem_info_vram_used, engine log · dense/KV/work = used − expert cache − draft · the uncensored version in daily use (with image input, without pinned K/V): engine {z(lb['strata_rss_gib'], sp)}, available {z(lb['ram_available_gib'], sp)}, expert cache {z(lb['expert_cache_gib'], sp)} GiB · data: messen/daten/{XTX_DATEN}/ (19 Nov on the base of 0.2.16: {XTX_VOR}/, 16 Nov on the 0.2.14 release: 2026-11-16-speicher/)" if en else
             f"gemessen am {XTX_TAG['de']} · /proc, amdgpu mem_info_vram_used, Engine-Log · dicht/KV/Arbeit = belegt − Experten-Cache − Entwurf · die unzensierte Fassung im täglichen Einsatz (mit Bildeingang, ohne festgepinnte K/V): Engine {z(lb['strata_rss_gib'], sp)}, verfügbar {z(lb['ram_available_gib'], sp)}, Experten-Cache {z(lb['expert_cache_gib'], sp)} GiB · Daten: messen/daten/{XTX_DATEN}/ (19.11. auf der Basis 0.2.16: {XTX_VOR}/, 16.11. auf dem Release 0.2.14: 2026-11-16-speicher/)")
    frei = m["vram_total_gib"] - m["vram_used_gib"]
    return "speicher", titel, (f"Of {z(m['ram_total_gib'], sp)} GiB RAM the Strata engine holds {z(m['strata_rss_gib'], sp)}, NAS services and kernel {z(dienste, sp)}, and {z(m['ram_available_gib'], sp)} stay available; of 24 GiB VRAM the expert cache takes {z(m['expert_cache_gib'], sp)}, the MTP draft {z(m['mtp_gib'], sp)}, everything else {z(rest, sp)}, and {z(frei, sp)} stay free." if en else
                               f"Von {z(m['ram_total_gib'], sp)} GiB RAM hält die Strata-Engine {z(m['strata_rss_gib'], sp)}, NAS-Dienste und Kernel {z(dienste, sp)}, verfügbar bleiben {z(m['ram_available_gib'], sp)}; von 24 GiB VRAM nimmt der Experten-Cache {z(m['expert_cache_gib'], sp)}, der MTP-Entwurf {z(m['mtp_gib'], sp)}, alles Übrige {z(rest, sp)}, frei bleiben {z(frei, sp)}."), s, h


NAMEN = {"faber": "Flash-Next IQ3_XXS (MoE)", "liber": ("Flash-Next IQ3_XXS, uncensored", "Flash-Next IQ3_XXS, unzensiert"), "velox": "Flash-Next IQ2_XS (MoE)", "qwen27": ("Qwen3.8-27B (dense)", "Qwen3.8-27B (dicht)"), "gemma31": ("Gemma 4 31B (dense)", "Gemma 4 31B (dicht)"), "qwen35": ("Qwen3.5-35B-A3B (UGREEN stock model)", "Qwen3.5-35B-A3B (UGREEN-Werksmodell)")}


def modellname(m, sp):
    n = NAMEN[m]
    return n if isinstance(n, str) else n[0 if sp == "en" else 1]


def dicht_moe(d, sp):
    """Sechs Modelle auf einer Karte: Schreibtempo gegen verdeckt benotetes Deutsch."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    daten = dict(json.load(open(os.path.join(d, "2026-11-14-erfinden/nacht.json"), encoding="utf-8"))["modelle"])
    q = json.load(open(os.path.join(d, "2026-11-15-betrieb", "qualitaet.json"), encoding="utf-8"))["modelle"]
    werk = {x["stufe"]: x for x in json.load(open(os.path.join(d, "2026-11-15-betrieb", "werksmodell.json"), encoding="utf-8"))["stufen"]}
    daten["qwen35"] = {"schreiben_leise": werk["xtx-vulkan"]["schreiben_tps_median"], "deutsch_60": q["qwen35"]["deutsch_blind_60"], "punkte": {"gesamt": q["qwen35"]["bestanden_gesamt"]}}
    s = Svg()
    titel = T("Schnell und gutes Deutsch zugleich: nur die 125B-Modelle", "Fast and good German at once: only the 125B models")
    kopf(s, T("RX 7900 XTX · sechs Modelle · 13. bis 15.11.2026", "RX 7900 XTX · six models · 13 to 15 Nov 2026"), titel)
    feld(s, L, 104, T("Deutsch (verdeckt benotet, von 60) gegen Schreibtempo", "German (graded blind, of 60) against decode speed"),
         T("weiter rechts ist schneller, weiter oben ist besser · die Deutschachse beginnt bei 30", "further right is faster, further up is better · the German axis starts at 30"))
    p = Hoch(s, L, R, 144, 504, 60, 30)
    X = lambda v: L + (v - 20) / 100 * (R - L)
    p.achse(5, sp)
    s.rect(X(50), p.Y(60), R - X(50), p.Y(48) - p.Y(60), TON["salbei"][0], deck=0.16, kante=False)
    strich = f'stroke="{TON["salbei"][1]}" stroke-width="1.2" stroke-dasharray="5 4"'
    s.line(X(50), p.Y(60), X(50), p.Y(48), strich)
    s.line(X(50), p.Y(48), R, p.Y(48), strich)
    s.text(R - 10, p.Y(48) - 10, T("SCHNELL UND GUTES DEUTSCH", "FAST AND GOOD GERMAN"), 8, TON["salbei"][2], "mono", "end", 600, sperr="0.14em")
    s.text(X(50) + 6, p.Y(30) - 8, T("ab 50 Token/s", "from 50 tokens/s"), 8.5, MUTED, "mono")
    s.line(X(50), p.Y(48), X(50), p.Y(30), f'stroke="{TON["salbei"][1]}" stroke-width="1" stroke-dasharray="2 5" stroke-opacity="0.6"')
    for v in range(40, 121, 20):
        s.line(X(v), 144, X(v), 504)
        s.text(X(v), 520, str(v), 9, MUTED, "mono", "middle")
    s.text(X(20), 520, "20", 9, MUTED, "mono", "middle")
    s.text((L + R) / 2, 542, T("Schreiben, lange Antwort (Token/s)", "decode, long answer (tokens/s)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
    for m, w in daten.items():
        moe = m in ("faber", "velox", "liber")
        x, y = X(w["schreiben_leise"]), p.Y(w["deutsch_60"])
        s.punkt(x, y, ACC if moe else STAHL, not moe, r=7 if m == "liber" else 6)
        links = m == "qwen35"
        tx, anker = (x - 14, "end") if links else (x + 14, None)
        ty = y - 20 if m == "liber" else y - 10 if m == "qwen27" else y + 4
        s.text(tx, ty, modellname(m, sp) + (" *" if m == "qwen35" else ""), 11, ACC if moe else INK, "sans", anker, 600)
        s.text(tx, ty + 13, f"{z(w['schreiben_leise'], sp)} tok/s · {w['deutsch_60']}/60 · {w['punkte']['gesamt']}/102", 9, MUTED, "mono", anker)
    h = fuss(s, 566, (("punkt", ACC, T("Flash-Next 125B, auf VRAM und RAM verteilt (Strata)", "Flash-Next 125B, split between VRAM and RAM (Strata)")),
                      ("punkt-hohl", STAHL, T("kleinere Modelle, ganz im VRAM (llama.cpp)", "smaller models, fully in VRAM (llama.cpp)")),
                      ("ton", "salbei", T("Zielbereich: ab 50 Token/s und ab 48 von 60", "target area: from 50 tokens/s and from 48 of 60"))),
             T("Deutsch: 12 Aufgaben, Antworten anonymisiert und verdeckt benotet · dritte Zahl: bestandene von 102 automatisch bewerteten Aufgaben · * UGREENs Werksmodell: eigene Benotungsrunde am 15.11., in der Flash-Next IQ3_XXS 47 statt 51 Punkte erhielt; sein Wert liegt auf der Skala der übrigen also eher etwas höher · Daten: messen/daten/2026-11-14-erfinden/nacht.json, 2026-11-15-betrieb/qualitaet.json",
               "German: 12 tasks, answers anonymised and graded blind · third number: passed out of 102 auto-graded tasks · * UGREEN's stock model: separate grading round on 15 Nov in which Flash-Next IQ3_XXS got 47 instead of 51 points, so on the others' scale its value is probably a little higher · data: messen/daten/2026-11-14-erfinden/nacht.json, 2026-11-15-betrieb/qualitaet.json"))
    return "dicht-moe", titel, T("Sechs Modelle auf einer Karte nach Schreibtempo und verdeckt benotetem Deutsch: die drei 125B-Modelle schreiben mit 62 bis 74 Token je Sekunde bei 46 bis 54 von 60 Punkten, zwei dichte Modelle mit 35 und 36 bei 38 und 52, UGREENs Qwen 3.5 mit 114 bei 37.",
                                 "Six models on one card by decode speed and blind-graded German: the three 125B models write at 62 to 74 tokens per second with 46 to 54 of 60 points, two dense models at 35 and 36 with 38 and 52, UGREEN's Qwen 3.5 at 114 with 37."), s, h


def cloud_vergleich(d, sp):
    """Bestandene Aufgaben von 102: die sechs lokalen Modelle und, abgesetzt, Sonnet 5.5 mit zwei Denkstufen."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    nacht = json.load(open(os.path.join(d, "2026-11-14-erfinden/nacht.json"), encoding="utf-8"))["modelle"]
    zahl = json.load(open(os.path.join(d, "2026-11-16-cloud-vergleich", "zahlen.json"), encoding="utf-8"))["models"]
    werk = json.load(open(os.path.join(d, "2026-11-15-betrieb", "qualitaet.json"), encoding="utf-8"))["modelle"]["qwen35"]["bestanden_gesamt"]
    heute = json.load(open(betriebsdatei(d, "qualitaet.json"), encoding="utf-8"))["modelle"]["faber"]["bestanden_gesamt"]
    lokal = [("faber", heute, "Strata 0.2.14"), ("liber", zahl["liber"]["passed_after_reading"], "Strata 0.2.14"), ("velox", nacht["velox"]["punkte"]["gesamt"], "Strata 0.2.12"),
             ("gemma31", nacht["gemma31"]["punkte"]["gesamt"], "llama.cpp"), ("qwen27", nacht["qwen27"]["punkte"]["gesamt"], "llama.cpp"), ("qwen35", werk, "llama.cpp")]
    cloud = [("Sonnet 5.5 High", zahl["sonnet55-high"]["passed_after_reading"], T("über die API", "over the API")),
             ("Sonnet 5.5 Medium", zahl["sonnet55-medium"]["passed_after_reading"], T("über die API", "over the API"))]
    s = Svg()
    titel = T("Bestandene Aufgaben von 102", "Tasks passed, of 102")
    kopf(s, T("RX 7900 XTX · sechs lokale Modelle und Sonnet 5.5 · 13. bis 16.11.2026", "RX 7900 XTX · six local models and Sonnet 5.5 · 13 to 16 Nov 2026"), titel)
    x0, x1, zeile = 360, R - 60, 34
    X = lambda v: x0 + (v - 85) / (102 - 85) * (x1 - x0)
    oben, y = 112, 136
    unten = y + (len(lokal) + len(cloud)) * zeile + 30
    for v in (85, 90, 95, 100):
        s.line(X(v), oben, X(v), unten - 14)
        s.text(X(v), unten, str(v), 9, MUTED, "mono", "middle")
    s.line(X(102), oben, X(102), unten - 14, 'stroke="#2a2724" stroke-opacity="0.3" stroke-width="1" stroke-dasharray="3 3"')
    s.text(X(102), unten, "102", 9, MUTED, "mono", "middle")
    s.text(L, oben, T("LOKAL, AUF DER KARTE", "LOCAL, ON THE CARD"), 8.5, MUTED, "mono", weight=500, sperr="0.14em")
    for m, v, sub in lokal:
        moe = m in ("faber", "velox", "liber")
        s.text(L, y + 4, modellname(m, sp), 12, ACC if moe else INK, "sans", weight=600)
        s.text(L, y + 17, sub, 8.5, MUTED, "mono")
        s.punkt(X(v), y, ACC if moe else STAHL, not moe, r=6)
        s.text(X(v) + 14, y + 4, str(v), 11, INK, "mono", weight=600)
        y += zeile
    y += 6
    s.line(40, y - 18, W - 40, y - 18, 'stroke="#2a2724" stroke-opacity="0.14" stroke-width="0.8"')
    s.text(L, y, T("CLOUD, ZUM VERGLEICH", "CLOUD, FOR COMPARISON"), 8.5, MUTED, "mono", weight=500, sperr="0.14em")
    y += 24
    for name, v, sub in cloud:
        s.text(L, y + 4, name, 12, INK, "sans", weight=600)
        s.text(L, y + 17, sub, 8.5, MUTED, "mono")
        s.punkt(X(v), y, PETROL, r=6)
        s.text(X(v) + 14, y + 4, str(v), 11, INK, "mono", weight=600)
        y += zeile
    h = fuss(s, unten + 18, (("punkt", ACC, T("Flash-Next 125B (Strata)", "Flash-Next 125B (Strata)")), ("punkt-hohl", STAHL, T("kleinere Modelle, ganz im VRAM", "smaller models, fully in VRAM")), ("punkt", PETROL, "Sonnet 5.5")),
             T("102 automatisch benotete Aufgaben, Faktenfragen nachgelesen · je ein Lauf · die Achse beginnt bei 85 · Flash-Next IQ3_XXS und unzensiert am 16.11.2026, IQ2_XS und die dichten Modelle am 13.11., UGREENs Werksmodell am 15.11. · Sonnet 5.5 über die API am 16.11.2026, Denkaufwand medium und high, voreingestellte Temperatur · Daten: messen/daten/2026-11-16-cloud-vergleich/",
               "102 automatically graded tasks, fact questions read by hand · one run each · the axis starts at 85 · Flash-Next IQ3_XXS and uncensored on 16 Nov 2026, IQ2_XS and the dense models on 13 Nov, UGREEN's stock model on 15 Nov · Sonnet 5.5 over the API on 16 Nov 2026, effort medium and high, default temperature · data: messen/daten/2026-11-16-cloud-vergleich/"))
    alle = ", ".join(f"{modellname(m, sp)} {v}" for m, v, _ in lokal) + ", " + ", ".join(f"{n} {v}" for n, v, _ in cloud)
    return "cloud-vergleich", titel, T(f"Bestandene Aufgaben von 102 für sechs lokale Modelle und Sonnet 5.5 mit zwei Denkstufen: {alle}.",
                                       f"Tasks passed out of 102 for six local models and Sonnet 5.5 at two effort levels: {alle}."), s, h


def erfinden(d, sp):
    en = sp == "en"
    daten = json.load(open(os.path.join(d, "2026-11-14-erfinden/probe.json"), encoding="utf-8"))["modelle"]
    bereiche = [("ort", "town → state", "Gemeinde → Land"), ("befehl", "command option", "Befehlsoption"), ("begriff", "theorem, law", "Satz, Gesetz"),
                ("werk", "book → author", "Buch → Autor"), ("werkzeug", "agent tool, parameter", "Agentenwerkzeug")]
    summe = lambda x, f: sum(v[f] for v in x.values())
    s = Svg()
    titel = "Four rules in the system prompt make the models say “I don't know”" if en else "Vier Regeln im Systemprompt bringen die Modelle zu „weiß ich nicht“"
    kopf(s, "RX 7900 XTX · 5 areas × 8 made-up things × 3 rounds · temperature 0.7" if en else "RX 7900 XTX · 5 Bereiche × 8 erfundene Dinge × 3 Runden · Temperatur 0,7", titel)
    for i, m in enumerate(("faber", "liber", "velox", "qwen27", "gemma31")):
        x0, y0 = (L, 544)[i % 2], (104, 320, 536)[i // 2]
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
    s.text(544, 596, "Rules beat the choice of model:" if en else "Die Regeln wirken stärker als die Modellwahl:", 17, INK, "serif", kursiv=True)
    s.text(544, 620, "every model ends between 88 and 99 %." if en else "Jedes Modell landet zwischen 88 und 99 %.", 17, INK, "serif", kursiv=True)
    s.text(544, 652, "The uncensored model trails a little in this probe: 17 instead of" if en else "Das unzensierte Modell liegt in dieser Probe etwas zurück: 17 statt 29 % ohne Regeln,", 10.5, MUTED, "sans")
    s.text(544, 668, "29 % without rules, 91 instead of 98 % with them." if en else "91 statt 98 % mit Regeln.", 10.5, MUTED, "sans")
    s.text(W / 2, 740, ("made-up questions answered with “I don't know” (of 24 per area)" if en else "erfundene Fragen mit „weiß ich nicht“ beantwortet (von 24 je Bereich)").upper(), 8, MUTED, "mono", "middle", sperr="0.14em")
    h = fuss(s, 760, (("punkt-hohl", MUTED, "without rules" if en else "ohne Regeln"), ("punkt", ACC, "with the four rules" if en else "mit den vier Regeln")),
             "messen/halluzination.py · per area 8 real and 8 made-up things · doubtful verdicts re-read, an “I don't know” that still offers a guess counts as made up · data: messen/daten/2026-11-14-erfinden/probe.json" if en else
             "messen/halluzination.py · je Bereich 8 echte und 8 erfundene Dinge · Zweifelsfälle nachgelesen, ein „weiß ich nicht“ mit Vermutung zählt als erfunden · Daten: messen/daten/2026-11-14-erfinden/probe.json")
    return "erfinden", titel, ("For five models and five areas, how many of 24 made-up questions were answered with I don't know, without and with four rules in the system prompt; overall recognition rises from 17–60 percent to 88–99 percent." if en else
                               "Für fünf Modelle und fünf Bereiche, wie viele von 24 erfundenen Fragen mit weiß ich nicht beantwortet wurden, ohne und mit vier Regeln im Systemprompt; insgesamt steigt die Erkennung von 17–60 auf 88–99 Prozent."), s, h


def urteil(d, sp):
    en = sp == "en"
    daten = json.load(open(os.path.join(d, "2026-11-14-erfinden/urteil.json"), encoding="utf-8"))["lagen"]
    lagen = {"zahl_weicht_ab": (("number deviates,", "order says stop"), ("Zahl weicht ab,", "Auftrag sagt Stopp")),
             "werkzeug_fehlt": (("announced tool", "is missing"), ("angekündigtes", "Werkzeug fehlt")),
             "lauf_bricht_ab": (("job aborts,", "nobody awake"), ("Lauf bricht ab,", "niemand wach"))}
    worte = {"gut": ("salbei", "good", "gut"), "grenzfall": ("gold", "borderline", "Grenzfall"), "schlecht": ("rose", "bad", "schlecht")}
    s = Svg()
    titel = "The 125B model as an operations agent: ten rounds show what three rounds hide" if en else "Das 125B-Modell als Betriebsagent: zehn Runden zeigen, was drei verbergen"
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
    zellen = [[("g", "17–60 % → 88–99 %, five models", "17–60 % → 88–99 %, fünf Modelle"), ("n", "", ""), ("b", "0 of 269 caught", "0 von 269 erkannt")],
              [("u", "“never invent numbers”", "„nie Zahlen erfinden“"), ("u", "numbers come from code", "Zahlen kommen aus dem Code"), ("g", "", "")],
              [("n", "", ""), ("u", "only allowed steps offered", "nur erlaubte Schritte angeboten"), ("g", "6 of 6", "6 von 6")],
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
    kopf(s, "Strata 0.2.12 · RX 7900 XTX (HIP) · Flash-Next 125B · MTP vs DFlash2" if en else "Strata 0.2.12 · RX 7900 XTX (HIP) · Flash-Next 125B · MTP gegen DFlash2", titel)
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


def betriebsdatei(d, name):
    """Betriebsmessung: die Nachmessung auf Strata 0.2.14 vom 16.11.2026, wo es sie gibt, sonst die Messung vom 15.11.2026."""
    for ordner in (XTX_DATEN, XTX_VOR, "2026-11-16-betrieb"):   # neueste Messung zuerst, auch wenn sie im Vorgängerordner liegt (21.11.2026)
        neu = os.path.join(d, ordner, name)
        if os.path.exists(neu):
            return neu
    return os.path.join(d, "2026-11-15-betrieb", name)


def ohne_switch(d, eintraege):
    """Früher: Abzug für den Netzwerk-Switch an derselben USV. Seit der Nachmessung am 15.11.2026 hängen NAS und Dock allein an der USV; nichts mehr abzuziehen."""
    return 0


def betrieb(d, sp):
    en = sp == "en"
    o = os.path.join(d, "2026-11-15-betrieb")
    ph = json.load(open(betriebsdatei(d, "strom-faber.json"), encoding="utf-8"))["phasen"]
    stufen = [x for f in ("dicht70-gpu.json", "dicht70-cpu.json") for x in json.load(open(os.path.join(o, f), encoding="utf-8"))["stufen"] if "fehler" not in x]
    ab = ohne_switch(d, list(ph.values()) + stufen)
    bestes = max((x for x in stufen if x["ngl"] > 0), key=lambda x: x["schreiben_tps_median"])
    cpu = next((x for x in stufen if x["ngl"] == 0), None)
    s = Svg()
    faktor = round(ph["schreiben"]["tps"] / bestes["schreiben_tps_median"])
    whs = z(ph["schreiben"]["wh_je_1000_token_gesamt"], sp)
    titel = f"{whs} Wh per 1,000 written tokens, and a dense 70B is {faktor} times slower" if en else f"{whs} Wh je 1.000 geschriebene Token, und ein dichtes 70B ist {faktor}-mal langsamer"
    kopf(s, f"UGREEN iDX6011 Pro + RX 7900 XTX · measured at the UPS · 15 Nov and {XTX_TAG['en']}" if en else f"UGREEN iDX6011 Pro + RX 7900 XTX · an der USV gemessen · 15.11. und {XTX_TAG['de']}", titel)
    feld(s, L, 104, "A · Power · watts" if en else "A · Leistung · Watt", "Flash-Next 125B (MoE) · NAS and dock together" if en else "Flash-Next 125B (MoE) · NAS und Dock zusammen")
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
             f"UPS values via NUT, the first 45 s of each phase discarded · NAS and dock alone on the UPS · dense 70B: Llama 3.3 70B Instruct Q4_K_M, llama.cpp Vulkan, 8K context · Flash-Next on my own build on Strata {XTX_VER} ({XTX_TAG['en']}), the dense 70B measured on 15 Nov · messen/betrieb.py, messen/dicht70.py · data: messen/daten/{XTX_DATEN}/ and 2026-11-15-betrieb/" if en else
             f"USV-Werte über NUT, die ersten 45 s jeder Phase verworfen · NAS und Dock allein an der USV · dichtes 70B: Llama 3.3 70B Instruct Q4_K_M, llama.cpp Vulkan, 8K Kontext · Flash-Next auf dem Eigenbau auf Strata {XTX_VER} ({XTX_TAG['de']}), das dichte 70B am 15.11. gemessen · messen/betrieb.py, messen/dicht70.py · Daten: messen/daten/{XTX_DATEN}/ und 2026-11-15-betrieb/")
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
    h = fuss(s, 458, None, "as shipped = the llama-server (SYCL) that UGOS starts by itself after the download, 4 threads, 7 slots, queried over its Unix socket · W for NAS and dock at the UPS, Wh per 1,000 written tokens · the as-shipped watts are calculated (measured with a network switch on the same UPS, 107.5 W deducted, ±10 W) · messen/werksmodell.py · data: messen/daten/2026-11-15-betrieb/werksmodell.json" if en else
             "ab Werk = der llama-server (SYCL), den UGOS nach dem Download selbst startet, 4 Fäden, 7 Plätze, über seinen Unix-Socket angesprochen · W für NAS und Dock an der USV, Wh je 1.000 geschriebene Token · die Watt ab Werk sind gerechnet (mit einem Netzwerk-Switch an derselben USV gemessen, 107,5 W abgezogen, ±10 W) · messen/werksmodell.py · Daten: messen/daten/2026-11-15-betrieb/werksmodell.json")
    return "werksmodell", titel, ("Decode and prompt reading speed of UGREEN's built-in Qwen 3.5 35B model on three paths: the UGOS server on the Arc iGPU, CPU only, and the RX 7900 XTX in the dock." if en else
                                  "Schreib- und Einlesetempo von UGREENs eingebautem Qwen 3.5 35B auf drei Wegen: UGOS-Server auf der Arc-iGPU, nur CPU, und RX 7900 XTX im Dock."), s, h


def qualitaet(d, sp):
    """Zwei Modelle, dieselben Aufgaben: Anteil bestandener Aufgaben je Bereich, dazu zwei Zahlenpaare."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    q = json.load(open(betriebsdatei(d, "qualitaet.json"), encoding="utf-8"))["modelle"]
    F, Q = q["faber"], q["qwen35"]
    s = Svg()
    titel = T("Das 125B-Modell besteht mehr Aufgaben und schreibt das bessere Deutsch", "The 125B model passes more tasks and writes the better German")
    kopf(s, T("Flash-Next 125B gegen UGREENs Qwen3.5-35B · dieselben Aufgaben · RX 7900 XTX · 15. und 16.11.2026", "Flash-Next 125B against UGREEN's Qwen3.5-35B · the same tasks · RX 7900 XTX · 15 and 16 Nov 2026"), titel)
    feld(s, L, 104, T("A · Bestanden · Anteil der Aufgaben", "A · Passed · share of tasks"), T("länger ist besser", "longer is better"))
    x0, x1 = 232, 560
    reihen = [(T("Alle benoteten Aufgaben", "All graded tasks"), F["bestanden_gesamt"], Q["bestanden_gesamt"], 102, True)]
    for k, name in (("code", "Code"), ("logik", T("Logik", "Logic")), ("anweisung", T("Anweisungen befolgen", "Following instructions")), ("fakten", T("Fakten", "Facts"))):
        reihen.append((name, F["bestanden"][k][0], Q["bestanden"][k][0], F["bestanden"][k][1], False))
    reihen.append((T("Deutsch, verdeckt benotet", "German, graded blind"), F["deutsch_blind_60"], Q["deutsch_blind_60"], 60, True))
    y = 144
    oben, unten = y - 6, y + len(reihen) * 42 - 8
    for anteil in (0.25, 0.5, 0.75, 1.0):
        x = x0 + anteil * (x1 - x0)
        s.line(x, oben, x, unten)
        s.text(x, unten + 16, f"{int(anteil * 100)} %", 9, MUTED, "mono", "middle")
    s.line(x0, oben, x0, unten, ACHSE)
    for name, a, b, n, stark in reihen:
        s.text(x0 - 14, y + 15, name, 11.5 if stark else 10.5, INK if stark else MUTED, "sans", "end", 600 if stark else None)
        for k, (v, farbe) in enumerate(((a, ACC), (b, STAHL))):
            yy = y + k * 13
            w = v / n * (x1 - x0)
            s.rect(x0, yy, w, 10, farbe, deck=0.3 if farbe == ACC else 0.18, sw=1.6 if farbe == ACC else 1, rx=1.5)
            s.text(x0 + w + 8, yy + 8.5, f"{v}/{n}", 9, farbe, "mono", weight=600 if farbe == ACC else None)
        y += 42
    # rechts: zwei Zahlenpaare
    xr = 668
    def paar(yk, was, hilfe, va, vb, einheit):
        feld(s, xr, yk, was, hilfe)
        for k, (v, farbe, name) in enumerate(((va, ACC, "Flash-Next 125B"), (vb, STAHL, "Qwen3.5-35B"))):
            xx = xr + k * 132
            s.text(xx, yk + 62, v, 34, farbe, "mono", weight=800)
            s.text(xx + len(v) * 20.5 + 6, yk + 62, einheit, 11, MUTED, "mono")
            s.text(xx, yk + 80, name, 10, farbe, "sans", weight=600)
    paar(104, T("B · Denkbudget aufgebraucht", "B · Reasoning budget used up"), T("Aufgaben ohne Antwort · weniger ist besser", "tasks without an answer · less is better"),
         "0", str(Q["denkbudget_erschoepft"]), T("von 102", "of 102"))
    paar(236, T("C · Zeit für alle 114 Aufgaben", "C · Time for all 114 tasks"), T("weniger ist besser", "less is better"),
         z(F["sekunden_114_aufgaben"] / 60, sp, 0), z(Q["sekunden_114_aufgaben"] / 60, sp, 0), "min")
    s.text(xr, 356, T("Das kleine Modell schreibt schneller,", "The small model writes faster"), 15, INK, "serif", kursiv=True)
    s.text(xr, 374, T("denkt aber viel länger nach.", "but thinks much longer."), 15, INK, "serif", kursiv=True)
    h = fuss(s, unten + 40, [("balken", ACC, "Flash-Next 125B"), ("balken", STAHL, T("Qwen3.5-35B (UGREENs Modell)", "Qwen3.5-35B (UGREEN's model)"))],
             T("102 automatisch benotete Aufgaben, davon je 15 in den vier gezeigten Bereichen · Deutsch: 12 Texte, verdeckt benotet, höchstens 60 Punkte · beide Modelle auf derselben Karte, gleiche Aufgaben, ein Lauf · Flash-Next auf Strata 0.2.14 (16.11.), seine Deutsch-Note vom Lauf auf 0.2.12",
               "102 automatically graded tasks, 15 each in the four areas shown · German: 12 texts, graded blind, at most 60 points · both models on the same card, the same tasks, one run · Flash-Next on Strata 0.2.14 (16 Nov), its German grade from the run on 0.2.12"))
    return "qualitaet", titel, T(f"Flash-Next 125B besteht {F['bestanden_gesamt']} von 102 Aufgaben, UGREENs Qwen3.5-35B {Q['bestanden_gesamt']}; im Deutschen {F['deutsch_blind_60']} gegen {Q['deutsch_blind_60']} von 60 Punkten. Beim kleinen Modell war in {Q['denkbudget_erschoepft']} Aufgaben das Denkbudget aufgebraucht.",
                                 f"Flash-Next 125B passes {F['bestanden_gesamt']} of 102 tasks, UGREEN's Qwen3.5-35B {Q['bestanden_gesamt']}; in German {F['deutsch_blind_60']} against {Q['deutsch_blind_60']} of 60 points. The small model used up its reasoning budget in {Q['denkbudget_erschoepft']} tasks."), s, h


def wartezeit(d, sp):
    """Wartezeit bis zum ersten Wort als Zeitstrahl: oben Texte zum Lesen nach Länge, unten Gespräch und besondere Fälle."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    lade = lambda name: json.load(open(betriebsdatei(d, name), encoding="utf-8"))
    warte = lade("wartezeit.json")["faelle"]
    zwei = lade("zwei.json")["phasen"]
    kalt = statistics.median(k["erste_antwort_s"] for k in lade("kaltstart-faber.json")["laeufe"])
    med = lambda name, f: statistics.median(x[f] for x in warte[name])
    s = Svg()
    titel = T("Im Gespräch kommt die Antwort sofort, ein ganzes Buch liest das Modell in gut einer Minute", "In a conversation the answer comes at once, a whole book takes the model a good minute to read")
    kopf(s, T(f"Qwen3.8-Flash-Next 125B · Warten bis zum ersten Wort der Antwort · iDX6011 Pro · strata-xtx auf Strata {XTX_VER} · {XTX_TAG['de']}", f"Qwen3.8-Flash-Next 125B · wait for the first word of the answer · iDX6011 Pro · strata-xtx on Strata {XTX_VER} · {XTX_TAG['en']}"), titel)
    x0, x1, lo, hi, ya = 96, 896, 0.2, 300.0, 240
    X = lambda v: x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)
    dauer = lambda v: (f"{z(v, sp, 1)} s" if v < 90 else f"{z(v / 60, sp, 1)} min")
    feld(s, L, 104, T("Oben · mit einem Text zum Lesen", "Above · with a text to read"))
    s.text(L, 372, T("UNTEN · IM GESPRÄCH UND IN BESONDEREN FÄLLEN", "BELOW · IN A CONVERSATION AND IN SPECIAL CASES"), 8.5, MUTED, "mono", weight=500, sperr="0.14em")
    for v, name in ((1, "1 s"), (10, "10 s"), (60, "1 min"), (180, "3 min")):
        s.line(X(v), 132, X(v), 352)
        s.text(X(v), 126, name, 8.5, MUTED, "mono", "middle")
    s.line(x0 - 16, ya, x1 + 16, ya, ACHSE)
    # oben: Texte nach Länge
    lesen = [("eine_seite", T("1 Seite", "1 page")), ("artikel_10_seiten", T("10 Seiten", "10 pages")), ("bericht_50_seiten", T("50 Seiten", "50 pages")), ("buch_300_seiten", T("300 Seiten", "300 pages"))]
    pts = [(X(med(n, "erste_anfrage_s")), ya) for n, _ in lesen]
    for k, (n, name) in enumerate(lesen):
        v = med(n, "erste_anfrage_s")
        farbe = ACC if k == len(lesen) - 1 else STAHL
        x = X(v)
        s.line(x, ya - 8, x, 196, f'stroke="{farbe}" stroke-width="1.2"')
        s.punkt(x, ya, farbe, r=5)
        s.text(x, 166, dauer(v), 21, farbe if farbe == ACC else TITLE, "mono", "middle", 700)
        s.text(x, 186, name, 11, farbe if farbe == ACC else INK, "sans", "middle", 600)
    # unten: Gespräch und besondere Fälle
    a = zwei["allein"]["A"]["warten_median_s"]
    b = med("kurze_frage", "erste_anfrage_s")
    g = sorted((zwei["gleichzeitig"]["A"]["warten_median_s"], zwei["gleichzeitig"]["B"]["warten_median_s"]))
    def unten(xa, xb, tiefe, zahl, name, anker="middle", xt=None):
        xm = (xa + xb) / 2
        if xb - xa > 1:
            s.roh(f'<rect x="{xa - 5:.1f}" y="{ya - 5}" width="{xb - xa + 10:.1f}" height="10" rx="5" fill="{PAPER}" stroke="{INK}" stroke-width="1.6"/>')
        else:
            s.punkt(xm, ya, INK, hohl=True, r=5)
        s.line(xm, ya + 8, xm, tiefe + 262, f'stroke="{INK}" stroke-opacity="0.45" stroke-width="1.2"')
        xt = xm if xt is None else xt
        s.text(xt, tiefe + 284, zahl, 16, TITLE, "mono", anker, 700)
        s.text(xt, tiefe + 300, name, 10.5, MUTED, "sans", anker)
    kurz = f"{z(a, sp, 1)}–{z(b, sp, 1)} s" if z(a, sp, 1) != z(b, sp, 1) else T(f"rund {z(a, sp, 1)} s", f"about {z(a, sp, 1)} s")
    unten(X(a), X(b), 0, kurz, T("Fragen im laufenden Gespräch", "questions in a running conversation"), "start", X(a) - 5)
    spanne = f"{z(g[0], sp, 0)}–{z(g[1], sp, 0)} s" if z(g[0], sp, 0) != z(g[1], sp, 0) else T(f"rund {z(g[0], sp, 0)} s", f"about {z(g[0], sp, 0)} s")
    unten(X(g[0]), X(g[1]), 0, spanne, T("zwei fragen zugleich", "two people ask at once"))
    unten(X(kalt), X(kalt), 36, f"{z(kalt, sp, 0)} s", T("erste Frage nach 30 min Pause", "first question after a 30-minute break"))
    h = fuss(s, 388, None,
             T("Median aus bis zu drei Läufen, das Buch mit 300 Seiten ein Lauf · auf dem Release 0.2.14 am 16.11.2026: 50 Seiten 27 s, das Buch 2,7 min · die Zeitachse ist logarithmisch: gleiche Abstände sind gleiche Vielfache · eine Folgefrage zum selben langen Text kommt wieder nach rund 0,3 s · nach 30 Minuten ohne Anfrage wird das Modell entladen",
               "median of up to three runs, the 300-page book one run · on the 0.2.14 release on 16 Nov 2026: 50 pages 27 s, the book 2.7 min · the time axis is logarithmic: equal distances are equal multiples · a follow-up question on the same long text comes after about 0.3 s again · after 30 minutes without a request the model is unloaded"))
    return "wartezeit", titel, T(f"Zeitstrahl der Wartezeit bis zum ersten Wort: Fragen im Gespräch unter einer halben Sekunde, eine Seite Text unter zwei Sekunden, zehn Seiten gut fünf, 50 Seiten rund 13 Sekunden, ein Buch von 300 Seiten gut eine Minute; nach einer Pause {z(kalt, sp, 0)} Sekunden, zu zweit rund sieben.",
                                 f"Timeline of the wait for the first word: questions in a conversation under half a second, one page of text under two seconds, ten pages a good five, 50 pages about 13 seconds, a 300-page book a good minute; after a break {z(kalt, sp, 0)} seconds, two people at once about seven."), s, h


def gegenprobe(d, sp):
    """Gegenprobe mit öffentlichen Fragen: Erfundenes als echt behandelt und der Preis bei echten Fragen, je Regelfassung."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    q = json.load(open(os.path.join(d, "2026-11-16-erfinden2", "zahlen.json"), encoding="utf-8"))["modelle"]["faber"]["fassungen"]
    s = Svg()
    titel = T("Die Grundregel kostet nichts, die strenge Regel halbiert die falschen Antworten", "The basic rule costs nothing, the strict rule halves the wrong answers")
    kopf(s, T("Flash-Next 125B · vier Fassungen des Systemprompts · öffentliche Fragensätze · 15./16.11.2026", "Flash-Next 125B · four versions of the system prompt · public question sets · 15/16 Nov 2026"), titel)
    reihen = (("A", T("ohne Regel", "no rule"), False), ("E", T("Grundregel", "basic rule"), True), ("B", T("strenge Regel", "strict rule"), False), ("D", T("Regeln der ersten Probe", "rules of the first probe"), False))
    x0 = 232
    # links: Erfundenes als echt behandelt
    xa, xb = x0, 452
    feld(s, L, 104, T("A · Erfundenes als echt behandelt", "A · Made-up things treated as real"), T("von 150 Dingen, die es nicht gibt · kürzer ist besser", "of 150 things that do not exist · shorter is better"))
    # rechts: echte Fragen
    xc, xd = 540, 900
    feld(s, xc, 104, T("B · Mittelschwere echte Fragen", "B · Medium real questions"), T("150 Fragen: richtig · falsch · „weiß ich nicht“", "150 questions: right · wrong · \"I don't know\""))
    y = 150
    for anteil in (10, 20):
        x = xa + anteil / 25 * (xb - xa)
        s.line(x, y - 10, x, y + 4 * 44 - 12)
        s.text(x, y + 4 * 44 + 4, str(anteil), 9, MUTED, "mono", "middle")
    s.line(xa, y - 10, xa, y + 4 * 44 - 12, ACHSE)
    for k, name, fokus in reihen:
        f = q[k]
        erf = f["nichts_dreistufig"]["A"] if "nichts_dreistufig" in f else f["nichts"]["erfunden"]
        m = f["mittel"] if "mittel" in f else f["leicht"]
        farbe = ACC if fokus else STAHL
        s.text(x0 - 14, y + 15, name, 11.5, ACC if fokus else INK, "sans", "end", 600)
        w = erf / 25 * (xb - xa)
        s.rect(xa, y + 3, max(w, 1.5), 16, farbe, deck=0.3 if fokus else 0.18, sw=1.6 if fokus else 1, rx=2)
        s.text(xa + max(w, 1.5) + 8, y + 15.5, str(erf), 11, farbe if fokus else INK, "mono", weight=700)
        # gestapelter Balken richtig / falsch / enthalten
        x = xc
        for wert, ton, deck, kante in ((m["richtig"], STAHL, 0.30, STAHL), (m["falsch"], "#9c4d40", 0.28, "#9c4d40"), (m["nicht_versucht"], BASE, 0.10, BASE)):
            br = wert / 150 * (xd - xc)
            s.rect(x, y + 3, br, 16, ton, deck=deck, kante=kante, sw=1, rx=2)
            if br > 22:
                s.text(x + br / 2, y + 15, str(wert), 10, TITLE, "mono", "middle", 600)
            x += br
        y += 44
    s.text(xa + 12, y + 30, T("Die Grundregel lässt echte Antworten, wie sie sind.", "The basic rule leaves real answers as they are."), 15, INK, "serif", kursiv=True)
    h = fuss(s, y + 52, [("balken", STAHL, T("richtig", "right")), ("balken", "#9c4d40", T("falsch", "wrong")), ("leer", BASE, T("„weiß ich nicht“", "\"I don't know\""))],
             T("ein Lauf je Frage bei Temperatur 0,7 · gewertet vom selben Modell, Stichproben von Hand gelesen · „weiß ich nicht“ ist genau gezählt, bei richtig gegen falsch irrt der Richter bei etwa jedem sechsten Urteil · Unterschiede unter etwa 8 Antworten bedeuten nichts · linkes Feld: bei „ohne Regel“ und „Grundregel“ nur klare Fälle (dreistufiges Urteil), bei den beiden strengen Fassungen das einfachere Urteil · Fragen: HalluLens und MKQA (deutsch)",
               "one run per question at temperature 0.7 · judged by the same model, samples read by hand · \"I don't know\" is counted exactly, on right against wrong the judge errs on about every sixth verdict · differences below about 8 answers mean nothing · left field: clear cases only (three-level verdict) for \"no rule\" and \"basic rule\", the simpler verdict for the two strict versions · questions: HalluLens and MKQA (German)"))
    a, e_, b = q["A"], q["E"], q["B"]
    ma, me, mb = (x["mittel"] if "mittel" in x else x["leicht"] for x in (a, e_, b))
    return "gegenprobe", titel, T(f"Ohne Regel behandelt das Modell {a['nichts_dreistufig']['A']} von 150 erfundenen Dingen als echt, mit der Grundregel {e_['nichts_dreistufig']['A']}. Auf 150 mittelschweren echten Fragen bleiben mit der Grundregel {me['richtig']} richtig (ohne Regel {ma['richtig']}); die strenge Regel senkt die falschen Antworten von {ma['falsch']} auf {mb['falsch']} und sagt {mb['nicht_versucht']}-mal „weiß ich nicht“.",
                                  f"Without a rule the model treats {a['nichts_dreistufig']['A']} of 150 made-up things as real, with the basic rule {e_['nichts_dreistufig']['A']}. On 150 medium real questions {me['richtig']} stay right with the basic rule (no rule: {ma['richtig']}); the strict rule cuts wrong answers from {ma['falsch']} to {mb['falsch']} and says \"I don't know\" {mb['nicht_versucht']} times."), s, h


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

    # Raster: Spalte A Geräte, B Oberflächen mit ihren Netz-Werkzeugen, C Weiche, D Karte; vier Zeilen. So kreuzt keine Linie eine andere.
    A_, B_, C_, D_ = 72, 272, 512, 744
    r1, r2, r3, r4 = 132, 224, 316, 408
    zone(254, 104, 674, 392, T("im Heimnetz", "in the home network"), 96 if not en else 150)
    zone(728, 124, 184, 264, T("RX 7900 XTX im Dock", "RX 7900 XTX in the dock"), 152 if not en else 158)
    # Pfeile zuerst, dann die Knoten
    pfeil(f"M 200,{r1 + 28} H 270")                                                                     # Geräte -> Open WebUI
    pfeil(f"M 200,{r1 + 44} H 228 Q 236,{r1 + 44} 236,{r1 + 52} V {r3 + 8} Q 236,{r3 + 16} 244,{r3 + 16} H 270")   # Geräte -> Hermes direkt (Browser, im Heimnetz)
    pfeil(f"M 136,{r1 + 56} V {r3 - 2}", gestrichelt=True)                                              # Geräte -> Messenger-Dienst
    pfeil(f"M 200,{r3 + 38} H 270", gestrichelt=True)                                                   # Messenger-Dienst -> Hermes
    pfeil(f"M 72,{r1 + 28} H 60 Q 52,{r1 + 28} 52,{r1 + 36} V {r4 + 20} Q 52,{r4 + 28} 60,{r4 + 28} H 70")         # Geräte -> OpenCode 2, links außen
    pfeil(f"M 352,{r1 + 56} V {r2 - 2}")                                                                # Open WebUI -> SearXNG
    pfeil(f"M 352,{r3} V {r2 + 58}")                                                                    # Hermes -> SearXNG
    pfeil(f"M 352,{r3 + 56} V {r4 - 2}")                                                                # Hermes -> Crawl4AI, direkt darunter
    pfeil(f"M 432,{r1 + 28} H 464 Q 472,{r1 + 28} 472,{r1 + 36} V {r2 + 8} Q 472,{r2 + 16} 480,{r2 + 16} H 510")   # Open WebUI -> llama-swap
    pfeil(f"M 432,{r3 + 28} H 464 Q 472,{r3 + 28} 472,{r3 + 20} V {r2 + 48} Q 472,{r2 + 40} 480,{r2 + 40} H 510")  # Hermes -> llama-swap
    pfeil(f"M 136,{r4 + 56} V {r4 + 64} Q 136,{r4 + 72} 144,{r4 + 72} H 584 Q 592,{r4 + 72} 592,{r4 + 64} V {r2 + 58}")  # OpenCode 2 -> llama-swap, unten herum
    pfeil(f"M 672,{r2 + 16} H 696 Q 704,{r2 + 16} 704,{r2 + 8} V 184 Q 704,176 712,176 H 742", fokus=True)        # llama-swap -> Sprachmodell
    pfeil(f"M 672,{r2 + 40} H 696 Q 704,{r2 + 40} 704,{r2 + 48} V {r3 + 20} Q 704,{r3 + 28} 712,{r3 + 28} H 742")  # llama-swap -> ComfyUI
    knoten(A_, r1, T("Geräte", "Devices"), T("Laptop, Handy", "Laptop, phone"), T("Browser, Messenger", "browser, messenger"), w=128)
    knoten(A_, r3, T("extern", "external"), T("Messenger-Dienst", "Messenger service"), T("z. B. Signal", "e.g. Signal"), "extern", w=128)
    knoten(A_, r4, "Terminal", "OpenCode 2", T("am eigenen Rechner", "on your own computer"), w=128)
    knoten(B_, r1, "Chat", "Open WebUI", T("Konten, Verlauf, Dateien", "accounts, history, files"))
    knoten(B_, r2, T("Suche", "Search"), "SearXNG", T("sucht über ein VPN im Netz", "searches through a VPN"), "extern")
    knoten(B_, r3, "Agent", "Hermes Agent", T("Werkzeuge, Aufgaben, Bilder", "tools, tasks, pictures"))
    # Webleser: seit 19.11.2026 im Heimnetz, nur der Agent ruft ihn; er holt die Seiten über ein VPN (wie SearXNG).
    knoten(B_, r4, T("Seiten lesen", "Read pages"), "Crawl4AI", T("liest über ein VPN im Netz", "reads through a VPN"), "extern")
    knoten(C_, r2, T("Weiche", "Switch"), "llama-swap", T("ein Modell zur Zeit", "one model at a time"))
    knoten(D_, 148, T("Sprache", "Language"), "Flash-Next 125B", T("Strata · 70 Token/s · 256K", "Strata · 70 tok/s · 256K"), "fokus", w=152)
    knoten(D_, r3, T("Bilder", "Pictures"), "ComfyUI", T("8–66 s je Bild", "8–66 s per picture"), w=152)
    y = 536
    s.line(40, y, W - 40, y, 'stroke="#2a2724" stroke-opacity="0.14" stroke-width="0.8"')
    s.roh(f'<path d="M 72,{y + 22} H 104" fill="none" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#{pf})"/>')
    s.text(116, y + 26, T("bleibt im Heimnetz", "stays in the home network"), 10, INK, "sans")
    s.roh(f'<path d="M 280,{y + 22} H 312" fill="none" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="5,4" marker-end="url(#{pf})"/>')
    s.text(324, y + 26, T("verlässt das Haus", "leaves the house"), 10, INK, "sans")
    s.text(R, y + 27, T("Nur Suchanfragen, gelesene Seiten und Messenger-Nachrichten verlassen das Haus.", "Only search queries, pages the agent reads and messenger messages leave the house."), 15, INK, "serif", "end", kursiv=True)
    s.text(L, y + 48, T("Chat, Suche und Agent laufen als Container, die Modelle auf der Karte im Dock",
                        "Chat, search and agent run as containers, the models on the card in the dock"), 8.5, MUTED, "mono")
    return "aufbau", titel, T("Laptop und Handy sprechen im Heimnetz mit Open WebUI und mit Hermes Agent, mit dem Agenten auch über einen Messenger-Dienst; beide fragen llama-swap, ebenso OpenCode 2 aus dem Terminal des eigenen Rechners. llama-swap lädt auf der RX 7900 XTX entweder das Sprachmodell oder ComfyUI. Webseiten liest der Agent über Crawl4AI auf der iDX, das sie über ein VPN abruft. Nur Suchanfragen, die vom Agenten gelesenen Seiten und Messenger-Nachrichten verlassen das Haus.",
                              "Laptop and phone talk to Open WebUI and to Hermes Agent in the home network, to the agent also through a messenger service; both ask llama-swap, as does OpenCode 2 from the terminal of your own computer. llama-swap loads either the language model or ComfyUI on the RX 7900 XTX. The agent reads web pages through Crawl4AI on the iDX, which fetches them through a VPN. Only search queries, the pages the agent reads and messenger messages leave the house."), s, 600


def parallel(d, sp):
    """Wer rechnet was: drei Bahnen (Karte im Dock, eingebaute iGPU, CPU und RAM) mit dem, was gleichzeitig läuft."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    n = json.load(open(betriebsdatei(d, "nebenlast.json"), encoding="utf-8"))
    st = json.load(open(betriebsdatei(d, "strom-faber.json"), encoding="utf-8"))["phasen"]["schreiben"]
    tag = n["gemessen"]
    tag_de, tag_en = f"{int(tag[8:])}.{int(tag[5:7])}.{tag[:4]}", f"{int(tag[8:])} Nov {tag[:4]}"
    ordner = os.path.basename(os.path.dirname(betriebsdatei(d, "nebenlast.json")))
    tr, dl = n["transkodieren"], n["download"]
    s = Svg()
    titel = T("Das NAS arbeitet weiter, während das Modell schreibt", "The NAS keeps working while the model writes")
    kopf(s, T("UGREEN iDX6011 Pro · alles gleichzeitig · Modell geladen und unter Last", "UGREEN iDX6011 Pro · everything at once · model loaded and under load"), titel)
    GUT, OFFEN = TON["salbei"][2], TON["gold"][2]
    bahnen = [
        (T("Karte im Dock", "Card in the dock"), "RX 7900 XTX · 24 GB", ACC, [
            (T("Sprachmodell", "Language model"), T("rund 70 Token/s", "about 70 tokens/s"), T("gemessen", "measured"), GUT, True),
            (T("Bildmodelle", "Picture models"), T("8–66 s je Bild, im Wechsel", "8–66 s per picture, in turn"), T("gemessen", "measured"), GUT, False)]),
        (T("Eingebaute iGPU", "Built-in iGPU"), "Intel Arc", STAHL, [
            (T("Video: Transkodierung", "Video: transcoding"), f"{z(min(tr['waehrend_schreiben_bilder_s']), sp, 0)}–{z(max(tr['waehrend_schreiben_bilder_s']), sp, 0)} {T('Bilder/s', 'frames/s')} ({T('ohne Last', 'idle')} {z(tr['ohne_modell_bilder_s'][0], sp, 0)})", T("gemessen", "measured"), GUT, False),
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
    h = fuss(s, y + 12, None, T(f"gemessen am {tag_de}, während das 125B-Modell durchgehend schrieb · Transkodierung 4K-HEVC nach 1080p-H.264 mit VAAPI · {dl.get('fuss_de', 'Datei 17,7 GB an einen Arbeitsplatz mit 5 Gbit/s, der die Grenze war')} · Daten: messen/daten/{ordner}/nebenlast.json",
                                    f"measured on {tag_en} while the 125B model was writing continuously · transcoding 4K HEVC to 1080p H.264 with VAAPI · {dl.get('fuss_en', '17.7 GB file to a client with 5 Gbit/s, which was the limit')} · data: messen/daten/{ordner}/nebenlast.json"))
    return "parallel", titel, T("Drei Bahnen: Auf der Karte im Dock laufen Sprach- und Bildmodelle, auf der eingebauten iGPU Transkodierung und Bilderkennung, auf Prozessor und RAM Dateifreigaben, Chat, Websuche und USV-Überwachung, alles gleichzeitig.",
                                "Three lanes: language and picture models run on the card in the dock, transcoding and photo recognition on the built-in iGPU, file shares, chat, web search and UPS monitoring on processor and RAM, all at the same time."), s, h


def steuervektor(d, sp):
    """Dasselbe Modell zensiert und unzensiert: was sich ändert (Ablehnungen) und was es kostet."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    v = json.load(open(os.path.join(d, "2026-11-14-erfinden", "steuervektor.json"), encoding="utf-8"))
    s = Svg()
    titel = T("Unzensiert beantwortet das Modell alles und bleibt sonst gleich gut", "Uncensored, the model answers everything and stays as good otherwise")
    kopf(s, T("Flash-Next 125B IQ3_XXS · Original und unzensiert (Ablehnungen per Steuervektor entfernt) · Strata 0.2.12", "Flash-Next 125B IQ3_XXS · original and uncensored (refusals removed by a steering vector) · Strata 0.2.12"), titel)
    feld(s, L, 104, T("A · 15 Aufgaben, die Modelle oft verweigern", "A · 15 tasks that models often refuse"), T("aus Fiktion, Humor, Gesundheit, Sicherheit und Ethik · von Hand gelesen", "from fiction, humour, health, security and ethics · read by hand"))
    X = lambda n: L + n * (456 - L) / 15
    for i, (schl, name) in enumerate((("faber", T("Original", "original")), ("liber", T("unzensiert", "uncensored")))):
        y = 160 + i * 92
        s.text(L, y, name, 11, INK, "sans", weight=600)
        links = 0
        for feld_, ton in (("beantwortet", "salbei"), ("ausgewichen", "gold"), ("abgelehnt", "rose")):
            n = v["heikle_aufgaben_15"][schl][feld_]
            if n:
                s.rect(X(links) + 1, y + 10, X(n) - L - 2, 44, TON[ton][0], deck=1, kante=TON[ton][1])
                s.text(X(links + n / 2), y + 37, str(n), 12, TON[ton][2], "sans", "middle", 700)
            links += n
    for n in (0, 5, 10, 15):
        s.text(X(n), 334, str(n), 9, MUTED, "mono", "middle")
    s.line(L, 320, 456, 320, ACHSE)
    feld(s, 544, 104, T("B · Was sich sonst ändert", "B · What else changes"), T("derselbe Aufgabensatz, dieselbe Karte", "the same task set, the same card"))
    s.text(796, 148, T("ORIGINAL", "ORIGINAL"), 8, MUTED, "mono", "end", 500, sperr="0.14em")
    s.text(824, 148, T("UNZENSIERT", "UNCENSORED"), 8, MUTED, "mono", weight=500, sperr="0.14em")
    g = v["gegenprobe_als_echt_von_150"]
    zeilen = [(T("Aufgaben bestanden (von 102)", "graded tasks passed (of 102)"), str(v["aufgaben_102"]["faber"]), str(v["aufgaben_102"]["liber"]), T("gleich", "equal"), "neutral"),
              (T("Deutsch, verdeckt benotet (von 60)", "German, graded blind (of 60)"), str(v["deutsch_blind_60"]["faber"]), str(v["deutsch_blind_60"]["liber"]), T("etwas besser", "a little better"), "salbei"),
              (T("Erfundenes als echt behandelt (von 150)", "made-up things treated as real (of 150)"), str(g["ohne_regel"]["faber"]), str(g["ohne_regel"]["liber"]), T("gleich", "equal"), "neutral"),
              (T("dasselbe mit kurzer Regel", "the same with a short rule"), str(g["kurze_regel"]["faber"]), str(g["kurze_regel"]["liber"]), T("gleich", "equal"), "neutral"),
              (T("Schreibtempo (Token/s)", "decode speed (tokens/s)"), z(v["schreiben_tps"]["faber"], sp), z(v["schreiben_tps"]["liber"], sp), T("gleich", "equal"), "neutral")]
    for i, (name, ohne, mit, wort, ton) in enumerate(zeilen):
        y = 176 + i * 30
        s.line(544, y + 10, R, y + 10, GITTER)
        s.text(544, y, name, 10.5, INK, "sans")
        s.text(796, y, ohne, 10, MUTED, "mono", "end")
        s.text(806, y, "→", 10, MUTED, "mono")
        s.text(824, y, mit, 10, ACC, "mono", weight=600)
        s.text(R, y, wort.upper(), 8, TON[ton][2], "mono", "end", 600, sperr="0.1em")
    s.text(R, 350, T("Es lehnt nichts mehr ab und kann dasselbe wie vorher.", "It refuses nothing any more and can do what it could before."), 15, INK, "serif", "end", kursiv=True)
    h = fuss(s, 372, (("ton", "salbei", T("beantwortet", "answered")), ("ton", "gold", T("ausgewichen, belehrt oder entschärft", "evasive, lecturing or toned down")), ("ton", "rose", T("abgelehnt", "refused"))),
             T("Aufgaben und Deutsch: Nachtvergleich 13./14.11.2026 · Erfinden: 150 Dinge, die es nicht gibt, aus einem öffentlichen Fragensatz, 16.11.2026, Unterschiede unter 8 bedeuten nichts · ein einzelner Lauf streut um ein bis zwei Aufgaben · Daten: messen/daten/2026-11-14-erfinden/steuervektor.json",
               "tasks and German: night comparison 13/14 Nov 2026 · making things up: 150 things that do not exist from a public question set, 16 Nov 2026, differences below 8 mean nothing · a single run varies by one or two tasks · data: messen/daten/2026-11-14-erfinden/steuervektor.json"))
    return "steuervektor", titel, T("Das Originalmodell beantwortet 11 von 15 Aufgaben, die Modelle oft verweigern, weicht bei 3 aus und lehnt 1 ab; das unzensierte beantwortet alle 15. Bei Aufgaben, Deutsch, Tempo und beim Erfinden bleibt es gleich oder etwas besser.",
                                    "The original model answers 11 of 15 tasks that models often refuse, is evasive on 3 and refuses 1; the uncensored one answers all 15. On tasks, German, speed and making things up it stays equal or a little better."), s, h


SCHALTER_DATEN = "2026-11-18-prompt-switches"


def schalter_werte(d):
    """Mit und ohne die 28 Umgebungsschalter: Einlesen bei 4K, 16K und 58K, Schreiben in Chat und Agent (gedrosseltes Kartenprofil)."""
    o = os.path.join(d, SCHALTER_DATEN)
    t = json.load(open(os.path.join(o, "speed-summary.json"), encoding="utf-8"))["medians"]
    e = json.load(open(os.path.join(o, "endurance-summary.json"), encoding="utf-8"))
    ohne, mit = t["baseline / quiet"], t["switches / quiet"]
    lang_mit = e["endurance_with_switches"]["last_30_min"]["long 64000"]["read_tok_s_mean"]
    lang_ohne = e["control_without_switches"]["long_requests"][1]["read_tok_s"]     # Anfrage 2: Modell schon geladen
    return {"lesen": [("4K", ohne["prompt_4k_tok_s"], mit["prompt_4k_tok_s"]), ("16K", ohne["prompt_16k_tok_s"], mit["prompt_16k_tok_s"]), ("58K", lang_ohne, lang_mit)],
            "schreiben": [("chat", ohne["chat_decode_tok_s"], mit["chat_decode_tok_s"]), ("agent", ohne["agent_decode_tok_s"], mit["agent_decode_tok_s"])]}


def schalter(d, sp, modell="faber"):
    """Dieselbe Engine ohne und mit 28 Umgebungsschaltern für das Einlesen: Stahl ist vorher, Bernstein nachher."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    w = schalter_werte(d)
    s = Svg()
    faktor = w["lesen"][-1][2] / w["lesen"][-1][1]
    titel = T(f"28 Umgebungsschalter: lange Prompts werden bis {z(faktor, sp, 1)}-mal so schnell gelesen",
              f"28 environment switches: long prompts are read up to {z(faktor, sp, 1)} times as fast")
    kopf(s, T("Flash-Next 125B IQ3_XXS · RX 7900 XTX · Strata 0.2.14, unveränderte Engine · 17./18.11.2026",
              "Flash-Next 125B IQ3_XXS · RX 7900 XTX · Strata 0.2.14, stock engine · 17/18 Nov 2026"), titel)
    felder = ((L, 560, w["lesen"], 3200, 800, 56, T("A · Prompt einlesen · Token/s", "A · Prompt reading · tokens/s"),
               T("nach Prompt-Länge · höher ist schneller", "by prompt length · higher is faster"),
               {"4K": T("4K-Prompt", "4K prompt"), "16K": T("16K-Prompt", "16K prompt"), "58K": T("58K-Prompt", "58K prompt")}),
              (640, R, w["schreiben"], 100, 20, 44, T("B · Schreiben · Token/s", "B · Decode · tokens/s"),
               T("Median aus 3 Läufen · höher ist schneller", "median of 3 runs · higher is faster"),
               {"chat": "Chat", "agent": T("Agent", "agent")}))
    for x0, x1, gruppen, vmax, schritt, breite, was, hilfe, namen in felder:
        feld(s, x0, 104, was, hilfe)
        p = Hoch(s, x0, x1, 144, 384, vmax)
        p.achse(schritt, sp)
        for g, (schl, ohne, mit) in enumerate(gruppen):
            gm = x0 + (g + 0.5) * (x1 - x0) / len(gruppen)
            p.balken(gm - breite / 2 - 4, breite, ohne, STAHL, z(ohne, sp))
            p.balken(gm + breite / 2 + 4, breite, mit, ACC, z(mit, sp), True, True)
            s.text(gm, 404, namen[schl], 12, INK, "sans", "middle", 600)
            s.text(gm, 420, f"+{z((mit / ohne - 1) * 100, sp, 0)} %", 9.5, ACC, "mono", "middle", 600)
    s.text(L + 24, 172, T("Einlesen 68 bis 127 % schneller, Schreiben rund 10 %.", "Reading 68 to 127 % faster, decode about 10 %."), 15, INK, "serif", kursiv=True)
    h = fuss(s, 444, (("balken", STAHL, T("Strata 0.2.14 wie ausgeliefert", "Strata 0.2.14 as shipped")),
                      ("balken", ACC, T("dieselbe Engine mit 28 Umgebungsschaltern", "the same engine with 28 environment switches"))),
             T("4K, 16K, Chat, Agent: tools/strata_bench.py, Median aus 3 Läufen im Wechsel, gedrosseltes Kartenprofil · 58K: derselbe Prompt mit 58.199 Token, mit Schaltern Mittel aus 15 Anfragen der letzten halben Stunde eines 90-Minuten-Laufs, ohne Schalter eine Anfrage direkt danach · gleiche Punktzahl im Aufgabensatz (98 und 97 von 102 in beiden Varianten) · Karte beim Einlesen 25 bis 30 W mehr, beim Schreiben gleich · 12 der 28 Schalter sind nicht dokumentiert, zugesichert ist keiner; jeder kann mit einem Release entfallen · Daten: messen/daten/2026-11-18-prompt-switches/",
               "4K, 16K, chat, agent: tools/strata_bench.py, median of 3 interleaved runs, capped card profile · 58K: the same 58,199-token prompt, with switches the mean of 15 requests in the last half hour of a 90-minute run, without switches one request right after it · same score on the task set (98 and 97 of 102 in both variants) · card draws 25 to 30 W more while reading, the same while writing · 12 of the 28 switches are undocumented, none is guaranteed; any of them may vanish with a release · data: messen/daten/2026-11-18-prompt-switches/"))
    l = {k: (o, m) for k, o, m in w["lesen"]}
    return "schalter", titel, T(f"Einlesetempo ohne und mit 28 Umgebungsschaltern: bei 4K {z(l['4K'][0], sp)} gegen {z(l['4K'][1], sp)} Token je Sekunde, bei 16K {z(l['16K'][0], sp)} gegen {z(l['16K'][1], sp)}, bei 58K {z(l['58K'][0], sp)} gegen {z(l['58K'][1], sp)}; das Schreibtempo steigt um rund zehn Prozent.",
                                f"Prompt reading speed without and with 28 environment switches: at 4K {z(l['4K'][0], sp)} against {z(l['4K'][1], sp)} tokens per second, at 16K {z(l['16K'][0], sp)} against {z(l['16K'][1], sp)}, at 58K {z(l['58K'][0], sp)} against {z(l['58K'][1], sp)}; decode speed rises by about ten per cent."), s, h


def eigenbau_werte(d):
    """Unverändertes Release und Eigenbau derselben Strata-Version: Einlesen (strata_bench, im Wechsel) und Dauer langer Prompts (needle_bench)."""
    lauf = lambda ps: {k: med([strata_bench(os.path.join(d, q))[k] for q in ps]) for k in ("4K", "16K", "32K", "chat", "agent")}
    rel, xtx = lauf(VERSIONEN[-1][1]), lauf(XTX_BENCH)
    o = os.path.join(d, XTX_DATEN)
    nadel = lambda datei, laenge: next(r["seconds"] for r in json.load(open(os.path.join(o, datei), encoding="utf-8")) if r["length"] == laenge and r["depth"] == 50)
    return {"rel": rel, "xtx": xtx,
            "dauer": [("128K", nadel(f"release-{XTX_VER}/needles-32k-128k.json", "128k"), nadel("needles-32k-128k-faber.json", "128k")),
                      ("250K", nadel(f"release-{XTX_VER}/needles-250k.json", "250k"), nadel("needles-250k-faber.json", "250k"))]}


def eigenbau(d, sp):
    """Der Eigenbau gegen das unveränderte Release derselben Version: Stahl ist das Release, Bernstein der Eigenbau."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    w = eigenbau_werte(d)
    rel, xtx = w["rel"], w["xtx"]
    lang = json.load(open(os.path.join(d, XTX_DATEN, "strom-faber.json"), encoding="utf-8"))["phasen"]["schreiben"]["tps"]
    td = tiefe_daten(d, TIEFE_XTX)["faber-xtx"]   # Schreibtempo nach frischem Prompt über die Tiefe 1K bis 250K, Median je Tiefe
    tief = [med([r["decode_tps"] for r in td[k]]) for k in td]
    tief_von, tief_bis = z(min(tief), sp, 0), z(max(tief), sp, 0)
    aufg = json.load(open(os.path.join(d, XTX_DATEN, "task-set-summary.json"), encoding="utf-8"))["runs"]
    a_plain, a_steer = (next(v["passed"] for k, v in aufg.items() if k.startswith(m)) for m in ("plain", "steered"))
    s = Svg()
    faktor = xtx["32K"] / rel["32K"]
    titel = T(f"strata-xtx liest lange Prompts {z(faktor, sp, 1)}-mal so schnell wie das Release", f"strata-xtx reads long prompts {z(faktor, sp, 1)} times as fast as the release")
    kopf(s, T(f"Flash-Next 125B IQ3_XXS · RX 7900 XTX · Strata {XTX_VER}: Release gegen Eigenbau · {XTX_TAG['de']}",
              f"Flash-Next 125B IQ3_XXS · RX 7900 XTX · Strata {XTX_VER}: release against my own build · {XTX_TAG['en']}"), titel)
    feld(s, L, 104, T("A · Prompt einlesen · Token/s", "A · Prompt reading · tokens/s"), T("nach Prompt-Länge · höher ist schneller", "by prompt length · higher is faster"))
    p = Hoch(s, L, 430, 144, 384, 3200)
    p.achse(800, sp)
    for g, k in enumerate(("4K", "16K", "32K")):
        gm = L + (g + 0.5) * (430 - L) / 3
        p.balken(gm - 24, 40, rel[k], STAHL, z(rel[k], sp))
        p.balken(gm + 24, 40, xtx[k], ACC, z(xtx[k], sp), True, True)
        s.text(gm, 404, T(f"{k}-Prompt", f"{k} prompt"), 12, INK, "sans", "middle", 600)
        s.text(gm, 420, f"+{z((xtx[k] / rel[k] - 1) * 100, sp, 0)} %", 9.5, ACC, "mono", "middle", 600)
    feld(s, 490, 104, T("B · Warten · Sekunden", "B · Waiting · seconds"), T("frischer Prompt · niedriger ist schneller", "fresh prompt · lower is faster"))
    p = Hoch(s, 490, 700, 144, 384, 240)
    p.achse(60, sp)
    for g, (k, a, b) in enumerate(w["dauer"]):
        gm = 490 + (g + 0.5) * (700 - 490) / 2
        p.balken(gm - 24, 40, a, STAHL, z(a, sp, 0))
        p.balken(gm + 24, 40, b, ACC, z(b, sp, 0), True, True)
        s.text(gm, 404, T(f"{k} Token", f"{k} tokens"), 12, INK, "sans", "middle", 600)
        s.text(gm, 420, f"−{z((1 - b / a) * 100, sp, 0)} %", 9.5, ACC, "mono", "middle", 600)
    feld(s, 760, 104, T("C · Schreiben · Token/s", "C · Decode · tokens/s"), T("kurze Chat-Antworten · höher ist schneller", "short chat answers · higher is faster"))
    p = Hoch(s, 760, R, 144, 384, 100)
    p.achse(20, sp)
    gm = (760 + R) / 2
    p.balken(gm - 24, 40, rel["chat"], STAHL, z(rel["chat"], sp))
    p.balken(gm + 24, 40, xtx["chat"], ACC, z(xtx["chat"], sp), True, True)
    s.text(gm, 404, "Chat", 12, INK, "sans", "middle", 600)
    s.text(gm, 420, T("gleich bis leicht schneller", "equal to slightly faster"), 9, MUTED, "mono", "middle")
    s.text(L + 20, 168, T("Dieselbe Karte, kein Schalter gesetzt.", "The same card, no switch set."), 15, INK, "serif", kursiv=True)
    h = fuss(s, 444, (("balken", STAHL, T(f"Strata {XTX_VER}, unverändertes Release", f"Strata {XTX_VER}, unchanged release")), ("balken", ACC, T(f"Eigenbau strata-xtx auf {XTX_VER}", f"my own build strata-xtx on {XTX_VER}"))),
             T(f"A und C: tools/strata_bench.py --long, Median aus 3 Läufen im Wechsel, jede Engine frisch geladen, leise Karteneinstellung · B: tools/needle_bench.py, eine versteckte Zahl in der Mitte des Prompts, jedes Mal gefunden · C misst kurze, gut vorhersehbare Antworten; lange Antworten (1.500 Token) schreibt der Eigenbau mit {z(lang, sp)} Token/s, nach einem frischen langen Prompt mit {tief_von} bis {tief_bis} · Aufgabensatz auf {XTX_VER}: {a_plain} von 102 beim Original, {a_steer} bei der unzensierten Fassung · Preis: Antworten nicht Bit für Bit gleich, Karte beim Einlesen 25 bis 30 W mehr (gemessen am 18.11.) · Daten: messen/daten/{XTX_DATEN}/",
               f"A and C: tools/strata_bench.py --long, median of 3 alternating runs, each engine freshly loaded, quiet card setting · B: tools/needle_bench.py, one hidden number in the middle of the prompt, found every time · C measures short, easily predicted answers; long answers (1,500 tokens) my own build writes at {z(lang, sp)} tokens/s, after a fresh long prompt at {tief_von} to {tief_bis} · task set on {XTX_VER}: {a_plain} of 102 with the original, {a_steer} with the uncensored version · price: answers not bit for bit the same, card draws 25 to 30 W more while reading (measured 18 Nov) · data: messen/daten/{XTX_DATEN}/"))
    da = {k: (a, b) for k, a, b in w["dauer"]}
    return "eigenbau", titel, T(f"Release {XTX_VER} gegen den Eigenbau strata-xtx: Einlesen bei 4K {z(rel['4K'], sp)} gegen {z(xtx['4K'], sp)} Token je Sekunde, bei 16K {z(rel['16K'], sp)} gegen {z(xtx['16K'], sp)}, bei 32K {z(rel['32K'], sp)} gegen {z(xtx['32K'], sp)}; ein Prompt von 250.000 Token braucht {z(da['250K'][0], sp, 0)} gegen {z(da['250K'][1], sp, 0)} Sekunden; Schreiben im Chat {z(rel['chat'], sp)} gegen {z(xtx['chat'], sp)} Token je Sekunde.",
                                f"Release {XTX_VER} against my own build strata-xtx: reading at 4K {z(rel['4K'], sp)} against {z(xtx['4K'], sp)} tokens per second, at 16K {z(rel['16K'], sp)} against {z(xtx['16K'], sp)}, at 32K {z(rel['32K'], sp)} against {z(xtx['32K'], sp)}; a prompt of 250,000 tokens takes {z(da['250K'][0], sp, 0)} against {z(da['250K'][1], sp, 0)} seconds; decode in chat {z(rel['chat'], sp)} against {z(xtx['chat'], sp)} tokens per second."), s, h


def schalter_lang(d, sp):
    """Lange Prompts (70K bis 250K) ohne und mit den 28 Schaltern, Variante mit Steuervektor und Originalmodell."""
    en = sp == "en"
    T = lambda de, en_: en_ if en else de
    rows = json.load(open(os.path.join(d, SCHALTER_DATEN, "memory-summary.json"), encoding="utf-8"))["rows"]
    w = {(r["model"], r["variant"], r["target_tokens"]): r for r in rows}
    m = lambda werte: sum(werte) / len(werte)
    stufen = sorted({r["target_tokens"] for r in rows})
    gross = stufen[-1]
    s_ohne, s_mit = m(w[("cvec", "baseline", gross)]["seconds"]), m(w[("cvec", "switches", gross)]["seconds"])
    ram = min(min(r["min_available_gib"]) for r in rows if r["variant"] == "switches")
    s = Svg()
    titel = T(f"{z(gross / 1000, sp, 0)}K Token: {z(s_ohne, sp, 0)} Sekunden werden zu {z(s_mit, sp, 0)}, mit und ohne Steuervektor",
              f"{z(gross / 1000, sp, 0)}K tokens: {z(s_ohne, sp, 0)} seconds become {z(s_mit, sp, 0)}, with and without control vector")
    kopf(s, T("Flash-Next 125B IQ3_XXS · RX 7900 XTX · Strata 0.2.14, unveränderte Engine · 18.11.2026",
              "Flash-Next 125B IQ3_XXS · RX 7900 XTX · Strata 0.2.14, stock engine · 18 Nov 2026"), titel)
    felder = ((L, 472, "cvec", T("A · Variante mit Steuervektor · Token/s", "A · Variant with control vector · tokens/s"),
               T("das Arbeitsmodell · Prompt einlesen", "the working model · prompt reading")),
              (536, R, "plain", T("B · Originalmodell · Token/s", "B · Original model · tokens/s"),
               T("Bezugsgröße und Rückfall · Prompt einlesen", "reference and fallback · prompt reading")))
    for x0, x1, modell, was, hilfe in felder:
        feld(s, x0, 104, was, hilfe)
        p = Hoch(s, x0, x1, 144, 384, 3200)
        p.achse(800, sp)
        for g, st in enumerate(stufen):
            gm = x0 + (g + 0.5) * (x1 - x0) / len(stufen)
            o, mi = w[(modell, "baseline", st)], w[(modell, "switches", st)]
            p.balken(gm - 19, 32, m(o["read_tps"]), STAHL, z(m(o["read_tps"]), sp, 0))
            p.balken(gm + 19, 32, m(mi["read_tps"]), ACC, z(m(mi["read_tps"]), sp, 0), True, True)
            s.text(gm, 404, f"{z(st / 1000, sp, 0)}K", 12, INK, "sans", "middle", 600)
            s.text(gm, 420, f"{z(m(o['seconds']), sp, 0)} → {z(m(mi['seconds']), sp, 0)} s", 9.5, ACC, "mono", "middle", 600)
    h = fuss(s, 444, (("balken", STAHL, T("Strata 0.2.14 wie ausgeliefert", "Strata 0.2.14 as shipped")),
                      ("balken", ACC, T("dieselbe Engine mit 28 Umgebungsschaltern", "the same engine with 28 environment switches"))),
             T(f"je Balken das Mittel aus 2 Anfragen auf frisch geladener Engine, gedrosseltes Kartenprofil · unter jeder Gruppe die Dauer der ganzen Anfrage ohne und mit Schaltern · alle 32 Anfragen fanden die im Prompt versteckte Zahl · kleinster verfügbarer Arbeitsspeicher des NAS mit Schaltern: {z(ram, sp, 2)} GiB von 62 · kein Dauerlauf mit der Steuervektor-Variante · Daten: messen/daten/2026-11-18-prompt-switches/memory-summary.json",
               f"each bar is the mean of 2 requests on a freshly loaded engine, capped card profile · below each group the duration of the whole request without and with switches · all 32 requests found the number hidden in the prompt · lowest available memory of the NAS with switches: {z(ram, sp, 2)} GiB of 62 · no endurance run with the control-vector variant · data: messen/daten/2026-11-18-prompt-switches/memory-summary.json"))
    return "schalter-lang", titel, T(f"Einlesetempo langer Prompts von 70.000 bis 250.000 Token ohne und mit 28 Umgebungsschaltern, für die Variante mit Steuervektor und das Originalmodell: in beiden gut doppelt so schnell, 250.000 Token dauern {z(s_mit, sp, 0)} statt {z(s_ohne, sp, 0)} Sekunden.",
                                     f"Reading speed for long prompts from 70,000 to 250,000 tokens without and with 28 environment switches, for the variant with control vector and the original model: a good twice as fast in both, 250,000 tokens take {z(s_mit, sp, 0)} instead of {z(s_ohne, sp, 0)} seconds."), s, h


ALLE = (eigenbau, schalter, schalter_lang, tiefe,mtp_annahme, pool_workers, versionen, docker_image, kontext, speicher, dicht_moe, cloud_vergleich, erfinden, gegenprobe, urteil, schichten, bildmodelle, dflash2, betrieb, werksmodell, aufbau, parallel, steuervektor)


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
