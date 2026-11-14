#!/usr/bin/env python3
"""Charts für den Nachtrag 14./15.11.2026: Erfinden messen und senken (gleiches helles Workbench-Design wie charts.py).

Alle Zahlen kommen aus messen/daten/2026-11-14-erfinden/ (probe.json, nacht.json, urteil.json).

  python charts3.py messen/daten/2026-11-14-erfinden bilder/
"""
import json, os, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import charts
from charts import GEDAEMPFT, SCHWACH, LINIE, FETT, SCHRIFT, BERNSTEIN, STAHL, PETROL, GOLD, GRUND, zahl

ROSE, SALBEI = "#9c4d40", "#5e7040"
plt.rcParams["font.family"] = ["Atkinson Hyperlegible Next", "DejaVu Sans"]
import logging; logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)  # Pfeil → fehlt in Atkinson
NAMEN = {"faber": "faber (MoE)", "velox": "velox (MoE)", "qwen27": "Qwen3.8-27B (dense)", "gemma31": "Gemma 4 31B (dense)"}
NAMEN_DE = {"faber": "faber (MoE)", "velox": "velox (MoE)", "qwen27": "Qwen3.8-27B (dicht)", "gemma31": "Gemma 4 31B (dicht)"}
BEREICHE = ["ort", "befehl", "begriff", "werk", "werkzeug"]

T = {
    "en": {
        "b": {"ort": "town → state", "befehl": "command option", "begriff": "theorem, law", "werk": "book → author",
              "werkzeug": "agent tool, parameter"},
        "p_t": "Recognising made-up things, without and with four rules in the system prompt",
        "p_x": "made-up questions answered with “I don't know” (of 24)", "ohne": "without rules", "mit": "with rules",
        "echt": "real things answered correctly", "gesamt": "total",
        "p_fuss": "messen/halluzination.py · 5 areas × 8 real + 8 made-up items · 3 rounds · temperature 0.7 · doubtful verdicts re-read",
        "n_t": "Dense models on the same card: half the speed, no better results", "n_x": "decode, long answer (tokens / s, quiet mode)",
        "n_y": "graded tasks passed (of 102)",
        "n_fuss": "Night run 13/14 Nov 2026 · RX 7900 XTX · all weights in VRAM · Strata 0.2.12 vs llama.cpp Vulkan · German and judgement in the table",
        "u_t": "faber as an operations agent: 10 rounds per situation", "u_x": "answers (of 10)",
        "lagen": {"zahl_weicht_ab": "number deviates,\norder says stop", "werkzeug_fehlt": "announced tool\nis missing",
                  "lauf_bricht_ab": "job aborts,\nnobody awake"},
        "gut": "good", "grenzfall": "borderline", "schlecht": "bad / invents capabilities", "nacht": "night run, 3 rounds (scaled)",
        "u_fuss": "messen/agent_de.py · temperature 0.7 · every answer read · with 3 rounds the same model looked better",
        "s_t": "Three layers against made-up answers, and what each one catches",
        "zeilen": ["made-up facts in words\n(“lies in Bavaria”)", "made-up numbers", "announced steps\nwithout a tool", "unknown tool names"],
        "spalten": ["rules in the\nsystem prompt", "tool returns a ready sentence\nand the allowed steps", "rule-based checker\n(plugin, no LLM)"],
        "zellen": [["catches it\n29–60 % → 88–99 %\n(four models)", "—", "blind\n0 of 269 caught"],
                   ["“never invent numbers”\nnot measured separately", "numbers come from code", "catches it"],
                   ["not aimed at this", "only allowed steps offered\nnot measured", "catches it\n6 of 6 (faber)"],
                   ["catches it\n10–20 → 23–24 of 24", "—", "catches it"]],
        "s_fuss": "measured = numbers in the cell · the tool layer is in use but not measured as a whole · the checker had 0 false alarms on the other tasks",
        "gemessen": "measured", "ungemessen": "not measured", "blind": "does not see it",
    },
    "de": {
        "b": {"ort": "Gemeinde → Land", "befehl": "Befehlsoption", "begriff": "Satz, Gesetz", "werk": "Buch → Autor",
              "werkzeug": "Agentenwerkzeug"},
        "p_t": "Erfundenes erkennen, ohne und mit vier Regeln im Systemprompt",
        "p_x": "erfundene Fragen mit „weiß ich nicht“ beantwortet (von 24)", "ohne": "ohne Regeln", "mit": "mit Regeln",
        "echt": "Echtes richtig", "gesamt": "gesamt",
        "p_fuss": "messen/halluzination.py · 5 Bereiche × 8 echte + 8 erfundene Gegenstände · 3 Runden · Temperatur 0,7 · Zweifelsfälle nachgelesen",
        "n_t": "Dichte Modelle auf derselben Karte: halb so schnell, nicht besser", "n_x": "Schreiben, lange Antwort (Token / s, Modus leise)",
        "n_y": "bestandene Aufgaben (von 102)",
        "n_fuss": "Nachtlauf 13./14.11.2026 · RX 7900 XTX · alle Gewichte im VRAM · Strata 0.2.12 gegen llama.cpp Vulkan · Deutsch und Urteil in der Tabelle",
        "u_t": "faber als Betriebsagent: 10 Runden je Lage", "u_x": "Antworten (von 10)",
        "lagen": {"zahl_weicht_ab": "Zahl weicht ab,\nAuftrag sagt Stopp", "werkzeug_fehlt": "angekündigtes\nWerkzeug fehlt",
                  "lauf_bricht_ab": "Lauf bricht ab,\nniemand wach"},
        "gut": "gut", "grenzfall": "Grenzfall", "schlecht": "schlecht / erfindet Fähigkeiten", "nacht": "Nachtlauf, 3 Runden (hochgerechnet)",
        "u_fuss": "messen/agent_de.py · Temperatur 0,7 · jede Antwort gelesen · mit 3 Runden sah dasselbe Modell besser aus",
        "s_t": "Drei Schichten gegen Erfinden, und was jede abfängt",
        "zeilen": ["erfundene Fakten in Worten\n(„liegt in Bayern“)", "erfundene Zahlen", "angekündigte Schritte\nohne Werkzeug", "unbekannte Werkzeugnamen"],
        "spalten": ["Regeln im\nSystemprompt", "Werkzeug liefert fertigen Satz\nund erlaubte Schritte", "Prüfer aus Regeln\n(Plugin, kein Sprachmodell)"],
        "zellen": [["fängt es ab\n29–60 % → 88–99 %\n(vier Modelle)", "—", "blind\n0 von 269 erkannt"],
                   ["„nie Zahlen erfinden“\nnicht einzeln gemessen", "Zahlen kommen aus dem Code", "fängt es ab"],
                   ["zielt nicht darauf", "nur erlaubte Schritte angeboten\nnicht gemessen", "fängt es ab\n6 von 6 (faber)"],
                   ["fängt es ab\n10–20 → 23–24 von 24", "—", "fängt es ab"]],
        "s_fuss": "gemessen = Zahl in der Zelle · die Werkzeugschicht ist im Einsatz, als Ganzes nicht gemessen · der Prüfer meldete in den übrigen Aufgaben 0 Fehlalarme",
        "gemessen": "gemessen", "ungemessen": "nicht gemessen", "blind": "sieht es nicht",
    },
}


def fuss(fig, text):
    fig.text(0.01, 0.012, text, fontsize=8, color=GEDAEMPFT, family="JetBrains Mono", wrap=True)


def summe(d, feld):
    return sum(v[feld] for v in d.values())


def probe(daten, ziel, sp):
    t = T[sp]
    modelle = [m for m in ("faber", "velox", "qwen27", "gemma31") if m in daten["modelle"]]
    spalten = 2 if len(modelle) > 1 else 1
    zeilen_n = (len(modelle) + spalten - 1) // spalten
    fig, achsen = plt.subplots(zeilen_n, spalten, figsize=(12, 2.9 * zeilen_n + 1.1), squeeze=False)
    farbe = {"faber": BERNSTEIN, "velox": STAHL, "qwen27": PETROL, "gemma31": GOLD}
    for i, m in enumerate(modelle):
        ax = achsen[i // spalten][i % spalten]
        d = daten["modelle"][m]
        o, mi = d.get("ohne_regeln"), d.get("mit_regeln")
        for j, b in enumerate(BEREICHE):
            y = len(BEREICHE) - 1 - j
            a = o[b]["erfunden_erkannt"] if o else None
            z = mi[b]["erfunden_erkannt"] if mi else None
            if a is not None and z is not None:
                ax.plot([a, z], [y, y], color=LINIE, lw=3, zorder=1, solid_capstyle="round")
            if a is not None:
                ax.scatter([a], [y], s=60, color=SCHWACH, zorder=2)
            if z is not None:
                ax.scatter([z], [y], s=70, color=farbe[m], zorder=3)
        ax.set_yticks(range(len(BEREICHE)))
        ax.set_yticklabels([t["b"][b] for b in reversed(BEREICHE)])
        ax.set_xlim(-1, 25.5)
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.grid(axis="y", visible=False)
        def pz(x):
            return f"{round(100 * summe(x, 'erfunden_erkannt') / summe(x, 'erfunden_n'))} %" if x else "–"
        def ez(x):
            return f"{summe(x, 'echt_richtig')}/{summe(x, 'echt_n')}" if x else "–"
        name = (NAMEN_DE if sp == "de" else NAMEN)[m]
        ax.set_title(f"{name}   {pz(o)} → {pz(mi)}", fontsize=12, color=FETT, loc="left", pad=20)
        ax.text(0.0, 1.03, f"{t['echt']}: {ez(o)} → {ez(mi)}", transform=ax.transAxes, ha="left", va="bottom",
                fontsize=9, color=GEDAEMPFT)
        if i // spalten == zeilen_n - 1:
            ax.set_xlabel(t["p_x"])
    for k in range(len(modelle), zeilen_n * spalten):
        achsen[k // spalten][k % spalten].axis("off")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], marker="o", ls="", color=SCHWACH, label=t["ohne"]),
                        Line2D([], [], marker="o", ls="", color=BERNSTEIN, label=t["mit"])],
               loc="upper right", frameon=False, ncol=2, bbox_to_anchor=(0.99, 0.995))
    fig.suptitle(t["p_t"], x=0.01, ha="left", fontsize=14, color=FETT, fontweight="semibold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fuss(fig, t["p_fuss"])
    fig.savefig(os.path.join(ziel, f"erfinden-{sp}.png"), dpi=150)
    plt.close(fig)


def nacht(daten, ziel, sp):
    t = T[sp]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    farbe = {"faber": BERNSTEIN, "velox": STAHL, "qwen27": PETROL, "gemma31": GOLD}
    for m, d in daten["modelle"].items():
        x, y = d["schreiben_leise"], d["punkte"]["gesamt"]
        ax.scatter([x], [y], s=160, color=farbe[m], zorder=3, edgecolor=GRUND, linewidth=1.5)
        name = (NAMEN_DE if sp == "de" else NAMEN)[m]
        ax.annotate(f"{name}\n{zahl(x, sp)} t/s · {y}/102", (x, y), textcoords="offset points",
                    xytext=(10, -4 if m != "gemma31" else 8), fontsize=10, color=SCHRIFT)
    ax.set_xlim(25, 90)
    ax.set_ylim(88, 101)
    ax.set_xlabel(t["n_x"])
    ax.set_ylabel(t["n_y"])
    ax.set_title(t["n_t"])
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fuss(fig, t["n_fuss"])
    fig.savefig(os.path.join(ziel, f"dicht-moe-{sp}.png"), dpi=150)
    plt.close(fig)


def urteil(daten, ziel, sp):
    t = T[sp]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    lagen = list(daten["lagen"])
    for i, l in enumerate(lagen):
        y = len(lagen) - 1 - i
        d = daten["lagen"][l]
        links = 0
        for feld, farbe in (("gut", SALBEI), ("grenzfall", GOLD), ("schlecht", ROSE)):
            w = d[feld]
            if w:
                ax.barh(y, w, left=links, color=farbe, height=0.55, edgecolor=GRUND, linewidth=1.5)
                ax.text(links + w / 2, y, str(w), ha="center", va="center", color=GRUND, fontsize=11, fontweight="semibold")
            links += w
        ax.scatter([d["nacht_3_gut"] / 3 * 10], [y + 0.38], marker="v", s=70, color=FETT, zorder=4, clip_on=False)
    ax.set_yticks(range(len(lagen)))
    ax.set_yticklabels([t["lagen"][l] for l in reversed(lagen)])
    ax.set_xlim(0, 10)
    ax.set_xticks(range(0, 11, 2))
    ax.set_xlabel(t["u_x"])
    ax.grid(axis="y", visible=False)
    ax.set_title(t["u_t"])
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    ax.legend(handles=[Patch(color=SALBEI, label=t["gut"]), Patch(color=GOLD, label=t["grenzfall"]),
                       Patch(color=ROSE, label=t["schlecht"]),
                       Line2D([], [], marker="v", ls="", color=FETT, label=t["nacht"])],
              loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4, frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fuss(fig, t["u_fuss"])
    fig.savefig(os.path.join(ziel, f"urteil-{sp}.png"), dpi=150)
    plt.close(fig)


def schichten(ziel, sp):
    t = T[sp]
    # Bewertung je Zelle: g = fängt ab (gemessen), u = trägt bei, nicht gemessen, b = blind, n = nicht zuständig
    art = [["g", "n", "b"], ["u", "u", "g"], ["n", "u", "g"], ["g", "n", "g"]]
    farbe = {"g": ("#c3c5b1", SALBEI), "u": ("#d8d0ba", GOLD), "b": ("#d6bbb1", ROSE), "n": ("#e2dbcf", LINIE)}
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.set_xlim(0, 3.9)
    ax.set_ylim(0, 4.9)
    ax.axis("off")
    for j, s in enumerate(t["spalten"]):
        ax.text(1.0 + j * 0.97 + 0.45, 4.55, s, ha="center", va="center", fontsize=10.5, color=FETT, fontweight="semibold")
    for i, z in enumerate(t["zeilen"]):
        y = 3.6 - i * 1.0
        ax.text(0.0, y, z, ha="left", va="center", fontsize=10.5, color=SCHRIFT)
        for j in range(3):
            a = art[i][j]
            fl, kante = farbe[a]
            x = 1.0 + j * 0.97
            ax.add_patch(Rectangle((x, y - 0.42), 0.9, 0.84, facecolor=fl, edgecolor="none"))
            ax.add_patch(Rectangle((x, y - 0.42), 0.025, 0.84, facecolor=kante, edgecolor="none"))
            ax.text(x + 0.47, y, t["zellen"][i][j], ha="center", va="center", fontsize=9.5, color=SCHRIFT)
    ax.set_title(t["s_t"])
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fuss(fig, t["s_fuss"])
    fig.savefig(os.path.join(ziel, f"schichten-{sp}.png"), dpi=150)
    plt.close(fig)


def main():
    quelle, ziel = sys.argv[1], sys.argv[2]
    os.makedirs(ziel, exist_ok=True)
    p = json.load(open(os.path.join(quelle, "probe.json"), encoding="utf-8"))
    n = json.load(open(os.path.join(quelle, "nacht.json"), encoding="utf-8"))
    u = json.load(open(os.path.join(quelle, "urteil.json"), encoding="utf-8"))
    for sp in ("de", "en"):
        probe(p, ziel, sp)
        nacht(n, ziel, sp)
        urteil(u, ziel, sp)
        schichten(ziel, sp)


if __name__ == "__main__":
    main()
