#!/usr/bin/env python3
"""Weitere Charts für das Repo (23.10.2026): Versionsverlauf, Docker-Image, Bildmodelle, Kontext, Speicher.

Gleiches helles Workbench-Design wie charts.py (Farben und Schriften von dort). Alle Zahlen kommen aus
den Dateien unter messen/daten/, nur der Speicherplan aus einer Messung am laufenden Server
(23.10.2026, siehe messen/daten/2026-10-23-v0.2.3.1/memory.json).

  python charts2.py messen/daten bilder/
"""
import json, os, statistics, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import charts
from charts import GEDAEMPFT, SCHWACH, LINIE, FETT, SCHRIFT, BERNSTEIN, STAHL, PETROL, GOLD, GRUND, zahl

T = {
    "en": {
        "ver_t": "Strata releases on the same RX 7900 XTX", "ver_dec": "decode (tokens / s)", "ver_pre": "prompt reading (tokens / s)",
        "chat": "chat", "agent": "agent", "ver_fuss": "tools/strata_bench.py --long · Flash-Next 125B IQ3_XXS · median · 0.2.3.1 ran with --kv-resident 32768 and a 9 GiB conversation cache",
        "dock_t": "Docker image defaults vs a tuned run config", "dock_y": "prompt reading (tokens / s)",
        "img021": "image 0.2.1", "img022": "image 0.2.2", "img023": "image 0.2.3", "tuned": "tuned, 0.2.3.1",
        "dock_fuss": "strata bench run --suite standard-v1 · median of 3 · the 0.2.3 engine finds the gfx1100 hipBLASLt table by itself",
        "img_t": "Image models in ComfyUI on the same card (one 1344×768 or 1664×928 image)", "img_x": "seconds per image",
        "warm": "warm", "kalt": "first image after the chat model", "img_fuss": "ComfyUI 0.42.1 · ROCm 7.2 · PyTorch 2.13 · started by llama-swap, which unloads Strata first · median of 2 warm runs",
        "ctx_t": "Waiting for the first word as the prompt grows", "ctx_x": "prompt length (tokens)", "ctx_y": "time to first token (s)",
        "ctx_fuss": "fresh prompts, no reuse · 4K–32K strata_bench.py (0.2.2) · 128K, 250K needle_bench.py (0.2.2, 0.1.44.1), needle found",
        "mem_t": "Where the memory goes with the 125B model loaded", "mem_x": "GiB",
        "ram": "RAM\n62.3 GiB", "vram": "VRAM\n24.0 GiB",
        "strata": "Strata engine", "andere": "NAS services, kernel", "frei": "available",
        "experten": "expert cache", "mtp": "MTP draft", "dicht": "dense, KV, work", "vfrei": "free",
        "mem_fuss": "measured 23 Oct 2026, faber loaded and idle · /proc, amdgpu mem_info_vram_used, engine log · dense/KV/work = used − cache − draft",
    },
    "de": {
        "ver_t": "Strata-Versionen auf derselben RX 7900 XTX", "ver_dec": "Schreiben (Token / s)", "ver_pre": "Prompt einlesen (Token / s)",
        "chat": "Chat", "agent": "Agent", "ver_fuss": "tools/strata_bench.py --long · Flash-Next 125B IQ3_XXS · Median · 0.2.3.1 lief mit --kv-resident 32768 und 9 GiB Gesprächs-Cache",
        "dock_t": "Docker-Image mit Voreinstellungen gegen abgestimmte Konfiguration", "dock_y": "Prompt einlesen (Token / s)",
        "img021": "Image 0.2.1", "img022": "Image 0.2.2", "img023": "Image 0.2.3", "tuned": "abgestimmt, 0.2.3.1",
        "dock_fuss": "strata bench run --suite standard-v1 · Median aus 3 · die Engine 0.2.3 findet die hipBLASLt-Tabelle für gfx1100 selbst",
        "img_t": "Bildmodelle in ComfyUI auf derselben Karte (ein Bild, 1344×768 bzw. 1664×928)", "img_x": "Sekunden je Bild",
        "warm": "warm", "kalt": "erstes Bild nach dem Sprachmodell", "img_fuss": "ComfyUI 0.42.1 · ROCm 7.2 · PyTorch 2.13 · gestartet von llama-swap, das vorher Strata entlädt · Median aus 2 warmen Läufen",
        "ctx_t": "Wartezeit bis zum ersten Wort bei wachsendem Prompt", "ctx_x": "Prompt-Länge (Token)", "ctx_y": "Zeit bis zum ersten Token (s)",
        "ctx_fuss": "frische Prompts ohne Wiederverwendung · 4K–32K strata_bench.py (0.2.2) · 128K, 250K needle_bench.py (0.2.2, 0.1.44.1), Nadel gefunden",
        "mem_t": "Wohin der Speicher geht, wenn das 125B-Modell geladen ist", "mem_x": "GiB",
        "ram": "RAM\n62,3 GiB", "vram": "VRAM\n24,0 GiB",
        "strata": "Strata-Engine", "andere": "NAS-Dienste, Kernel", "frei": "verfügbar",
        "experten": "Experten-Cache", "mtp": "MTP-Entwurf", "dicht": "dicht, KV, Arbeit", "vfrei": "frei",
        "mem_fuss": "gemessen am 23.10.2026, faber geladen und ruhend · /proc, amdgpu mem_info_vram_used, Engine-Log · dicht/KV/Arbeit = belegt − Cache − Entwurf",
    },
}


def fuss(fig, text):
    fig.text(0.01, 0.01, text, fontsize=8, color=GEDAEMPFT, family="JetBrains Mono", wrap=True)


def med(werte):
    werte = [w for w in werte if w is not None]
    return statistics.median(werte) if werte else None


def strata_bench(pfad):
    r = json.load(open(pfad, encoding="utf-8"))["results"]
    ok = lambda rs: [x for x in rs if x.get("ok")]
    out = {"chat": med([x["decode_tps"] for x in ok(r["chat"]["requests"])]),
           "agent": med([x["decode_tps"] for s in r["agent"]["sessions"] for x in ok(s)])}
    for k in ("4K", "16K", "32K"):
        reqs = ok(r["prompts"][k]["requests"])
        out[k] = med([x["prompt_tps"] for x in reqs])
        out["ttft_" + k] = med([x["ttft_s"] for x in reqs])
    return out


def standard(pfad):
    s = json.load(open(pfad, encoding="utf-8"))["summaries"]
    return {(x["case_id"], x["metric"]): x["median"] for x in s if x.get("concurrency") == 1}


def versionen(d, ziel, sp):
    t = T[sp]
    v = [("0.2.0-beta", "2026-10-19/strata-0.2.0-beta/strata-bench-results.json"),
         ("0.2.1", "2026-10-21/strata-bench/2026-10-21-community-unknown-b021/results.json"),
         ("0.2.2", "2026-10-21-v0.2.2/strata-bench/2026-10-21-community-unknown-b022/results.json"),
         ("0.2.3.1", "2026-10-23-v0.2.3.1/strata-bench/2026-10-23-community-unknown-b023/results.json")]
    werte = [strata_bench(os.path.join(d, p)) for _, p in v]
    x = list(range(len(v)))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for k, farbe in (("chat", BERNSTEIN), ("agent", STAHL)):
        ys = [w[k] for w in werte]
        a1.plot(x, ys, marker="o", color=farbe, lw=2, label=t[k])
        for xi, y in zip(x, ys):
            a1.annotate(zahl(y, sp), (xi, y), textcoords="offset points", xytext=(0, 8 if k == "agent" else -16),
                        ha="center", fontsize=9, color=farbe)
    a1.set_ylim(0, 95); a1.set_ylabel(t["ver_dec"]); a1.legend(frameon=False, loc="lower right")
    for k, farbe in (("4K", BERNSTEIN), ("16K", STAHL), ("32K", PETROL)):
        ys = [w[k] for w in werte]
        a2.plot(x, ys, marker="o", color=farbe, lw=2, label=k)
        a2.annotate(zahl(ys[-1], sp), (x[-1], ys[-1]), textcoords="offset points", xytext=(8, {"4K": -3, "16K": -12, "32K": 4}[k]),
                    fontsize=9, color=farbe)
    a2.set_ylim(0, 1400); a2.set_ylabel(t["ver_pre"]); a2.legend(frameon=False, loc="lower right")
    charts.tausender(a2, sp)
    for a in (a1, a2):
        a.set_xticks(x, [n for n, _ in v]); a.set_xlim(-0.3, len(v) - 0.6)
    fig.suptitle(t["ver_t"], x=0.01, ha="left", fontsize=13, fontweight="semibold", color=FETT)
    fuss(fig, t["ver_fuss"])
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(ziel, f"versionen-{sp}.png"), dpi=150)
    plt.close(fig)


def docker(d, ziel, sp):
    t = T[sp]
    reihen = [(t["img021"], "2026-10-21/standard-v1/docker-default/results.json", LINIE),
              (t["img022"], "2026-10-21-v0.2.2/standard-v1/docker-image-0.2.2-default/results.json", SCHWACH),
              (t["img023"], "2026-10-23-v0.2.3.1/standard-v1/docker-image-0.2.3-default/results.json", STAHL),
              (t["tuned"], "2026-10-23-v0.2.3.1/standard-v1/package-0.2.3.1/results.json", BERNSTEIN)]
    werte = [standard(os.path.join(d, p)) for _, p, _ in reihen]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    breite = 0.2
    for i, ((name, _, farbe), w) in enumerate(zip(reihen, werte)):
        ys = [w[("prompt-4k", "prompt_tps")], w[("prompt-16k", "prompt_tps")]]
        xs = [j + (i - 1.5) * breite for j in range(2)]
        ax.bar(xs, ys, breite * 0.92, color=farbe, label=name)
        for xi, y in zip(xs, ys):
            ax.text(xi, y + 15, zahl(y, sp), ha="center", fontsize=9, color=SCHRIFT)
    ax.set_xticks([0, 1], ["4K", "16K"]); ax.set_ylabel(t["dock_y"]); ax.set_ylim(0, 1400)
    charts.tausender(ax, sp)
    ax.legend(frameon=False, ncol=4, loc="upper left"); ax.set_axisbelow(True)
    ax.set_title(t["dock_t"])
    fuss(fig, t["dock_fuss"])
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(ziel, f"docker-image-{sp}.png"), dpi=150)
    plt.close(fig)


def bilder(d, ziel, sp):
    t = T[sp]
    namen = {"z-image-turbo": "Z-Image Turbo", "qwen-image-turbo": "Qwen-Image 2.1 Turbo",
             "qwen-image": "Qwen-Image 2.1", "chroma": "Chroma1-HD (bf16)"}
    zeilen = [json.loads(z) for z in open(os.path.join(d, "2026-10-23-bilder/bilder.jsonl"), encoding="utf-8")]
    modelle = [m for m in namen if any(z["model"] == m for z in zeilen)]
    warm = [med([z["ergebnis"]["seconds"] for z in zeilen if z["model"] == m and not z["kalt"] and z["ergebnis"].get("success")]) for m in modelle]
    kalt = [med([z["ergebnis"]["seconds"] for z in zeilen if z["model"] == m and z["kalt"] and z["ergebnis"].get("success")]) for m in modelle]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ys = list(range(len(modelle)))[::-1]
    ax.barh(ys, kalt, 0.6, color=LINIE, label=t["kalt"])
    ax.barh(ys, warm, 0.6, color=BERNSTEIN, label=t["warm"])
    for y, w, k in zip(ys, warm, kalt):
        ax.text(w - 1, y, zahl(w, sp) + " s", va="center", ha="right", fontsize=9, color=GRUND)
        ax.text(k + 1, y, zahl(k, sp) + " s", va="center", fontsize=9, color=GEDAEMPFT)
    ax.set_yticks(ys, [namen[m] for m in modelle]); ax.set_xlabel(t["img_x"])
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title(t["img_t"])
    fuss(fig, t["img_fuss"])
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(ziel, f"bildmodelle-{sp}.png"), dpi=150)
    plt.close(fig)


def kontext(d, ziel, sp):
    t = T[sp]
    w = strata_bench(os.path.join(d, "2026-10-21-v0.2.2/strata-bench/2026-10-21-community-unknown-b022/results.json"))
    n128 = next(r for r in json.load(open(os.path.join(d, "2026-10-21-v0.2.2/needles-32k-128k.json"))) if r["length"] == "128k" and r["depth"] == 10)
    n250 = next(r for r in json.load(open(os.path.join(d, "needles-250k.json"))) if r["depth"] == 10)
    pts = [(4019, w["ttft_4K"]), (16000, w["ttft_16K"]), (32049, w["ttft_32K"]),
           (n128["prompt_tokens"], n128["seconds"]), (n250["prompt_tokens"], n250["seconds"])]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=BERNSTEIN, lw=2)
    for x, y in pts:
        m = y / 60
        lab = (zahl(y, sp) + " s") if y < 90 else (f"{zahl(m, sp)} min")
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(-6, 8), ha="right", fontsize=9, color=SCHRIFT)
    ax.set_xticks([p[0] for p in pts], ["4K", "16K", "32K", "128K", "250K"])
    ax.set_xlabel(t["ctx_x"]); ax.set_ylabel(t["ctx_y"]); ax.set_ylim(0, 260)
    ax.set_title(t["ctx_t"])
    fuss(fig, t["ctx_fuss"])
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(ziel, f"kontext-{sp}.png"), dpi=150)
    plt.close(fig)


def speicher(d, ziel, sp):
    t = T[sp]
    m = json.load(open(os.path.join(d, "2026-10-23-v0.2.3.1/memory.json"), encoding="utf-8"))
    ram = [(t["strata"], m["strata_rss_gib"], BERNSTEIN), (t["andere"], m["ram_total_gib"] - m["strata_rss_gib"] - m["ram_available_gib"], STAHL),
           (t["frei"], m["ram_available_gib"], LINIE)]
    dicht = m["vram_used_gib"] - m["expert_cache_gib"] - m["mtp_gib"]
    vram = [(t["experten"], m["expert_cache_gib"], BERNSTEIN), (t["mtp"], m["mtp_gib"], GOLD),
            (t["dicht"], dicht, PETROL), (t["vfrei"], m["vram_total_gib"] - m["vram_used_gib"], LINIE)]
    fig, ax = plt.subplots(figsize=(11, 3.6))
    for y, teile in ((1, ram), (0, vram)):
        links = 0
        for name, wert, farbe in teile:
            ax.barh(y, wert, 0.55, left=links, color=farbe)
            if wert >= 2.5:
                ax.text(links + wert / 2, y, f"{name}\n{zahl(wert, sp)}", ha="center", va="center", fontsize=8.5,
                        color=GRUND if farbe not in (LINIE,) else SCHRIFT)
            else:
                ax.annotate(f"{name} {zahl(wert, sp)}", (links + wert / 2, y + 0.3), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=8, color=GEDAEMPFT)
            links += wert
    ax.set_yticks([1, 0], [t["ram"], t["vram"]]); ax.set_xlabel(t["mem_x"]); ax.set_xlim(0, 64); ax.set_axisbelow(True)
    ax.grid(axis="y", visible=False)
    ax.set_title(t["mem_t"])
    fuss(fig, t["mem_fuss"])
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(ziel, f"speicher-{sp}.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    daten, ziel = sys.argv[1], sys.argv[2]
    for sp in ("en", "de"):
        for f in (versionen, docker, bilder, kontext, speicher):
            f(daten, ziel, sp)
    print("ok")
