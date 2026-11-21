#!/usr/bin/env python3
"""Rendert die Textgrafik für den Seitenkopf nach web/bilder/ (einfach und doppelt aufgelöst).

Braucht den Baustein textgrafik.js (Pfad als erstes Argument) und playwright:
  uv run --with playwright python web/szene.py <Pfad>/textgrafik.js
"""
import os, sys, tempfile
from playwright.sync_api import sync_playwright
HIER = os.path.dirname(os.path.abspath(__file__))
baustein = open(os.path.expanduser(sys.argv[1]), encoding="utf-8").read()
szene = open(os.path.join(HIER, "szene", "anlage.js"), encoding="utf-8").read()
# Die Schriften der Seite fest einbinden (web/fonts), damit das Bild auf jedem Rechner gleich wird, auch ohne installierte Schriften.
F = os.path.join(HIER, "fonts").replace("\\", "/")
schriften = "".join(f'@font-face{{font-family:"{n}";font-weight:{w};font-style:{st};src:url("file:///{F.lstrip("/")}/{d}") format("woff2")}}' for n, w, st, d in (
    ("JetBrains Mono", 400, "normal", "jetbrains-mono-400.woff2"), ("JetBrains Mono", 500, "normal", "jetbrains-mono-400.woff2"),
    ("JetBrains Mono", 700, "normal", "jetbrains-mono-700.woff2"), ("Instrument Serif", 400, "italic", "instrument-serif-400-italic.woff2")))
laden = "Promise.all([document.fonts.load('500 11px \\\"JetBrains Mono\\\"'),document.fonts.load('700 11px \\\"JetBrains Mono\\\"'),document.fonts.load('italic 400 20px \\\"Instrument Serif\\\"')])"
with sync_playwright() as pw:
    try: b = pw.chromium.launch()
    except Exception: b = pw.chromium.launch(channel="chrome")
    for s, name in ((3, "anlage"), (6, "anlage@2x")):
        seite = f'<!DOCTYPE html><meta charset="utf-8"><style>{schriften}</style><body style="margin:0;background:#0d0c0b"><canvas id="cv"></canvas><script>{baustein}</script><script>{szene}</script><script>{laden}.then(function(){{Anlage(document.getElementById("cv"),{s});document.title="fertig"}})</script>'
        t = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8"); t.write(seite); t.close()
        p = b.new_page(viewport={"width": 344 * s, "height": 112 * s}, device_scale_factor=1)
        p.goto("file:///" + t.name.replace("\\", "/")); p.wait_for_function('document.title === "fertig"')
        p.locator("#cv").screenshot(path=os.path.join(HIER, "bilder", name + ".png"))
        os.unlink(t.name)
        print(name, os.path.getsize(os.path.join(HIER, "bilder", name + ".png")))
    b.close()
