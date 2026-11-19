#!/usr/bin/env python3
"""Baut die Webseite faf.net/lokale-ki (Deutsch) und faf.net/local-ai (Englisch) aus diesem Repo: eine Seite je Sprache, statisch, ohne JavaScript, ohne Fremdserver.

Die Diagramme kommen aus messen/diagramme.py (dieselben Funktionen wie für die PNG im README), eingebettet als SVG
und über CSS-Variablen an das helle oder dunkle Thema gebunden. Kennzahlen und Tabellen der Messung vom 15.11.2026
kommen aus messen/daten/, der Verdrahtungsplan aus dem README. Der Fließtext steht hier im Skript.

  python web/bau.py            schreibt web/dist/lokale-ki/ (Deutsch) und web/dist/local-ai/ (Englisch), je mit index.html, idx.css, fonts/, bilder/

Farben: web/workbench-farben.json (aus dem Design System Workbench). Schriften: web/fonts/ (OFL, selbst ausgeliefert).
"""
import math
import hashlib, html, json, os, re, shutil, statistics, subprocess, sys, time

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
DATEN = os.path.join(REPO, "messen", "daten")
sys.path.insert(0, os.path.join(REPO, "messen"))
import diagramme as D  # noqa: E402

GH = "https://github.com/faf-net/ugreen-idx6011-egpu-llm"
ORDNER = {"de": "lokale-ki", "en": "local-ai"}
ERSCHIENEN = "2026-11-15"   # Tag, an dem beide Seiten zum ersten Mal auf faf.net standen (für die strukturierten Daten)
FARBEN = json.load(open(os.path.join(HIER, "workbench-farben.json"), encoding="utf-8"))["farben"]
HEX2TOK = {}
for name, w in FARBEN.items():
    HEX2TOK.setdefault(w["light"].lower(), name)
HEX2TOK["#e4ded3"] = "rille"
L = lambda *p: json.load(open(os.path.join(DATEN, *p), encoding="utf-8"))
e = html.escape


def z(x, sp, nk=None):
    return D.z(x, sp, nk)


def themen(svg):
    """Feste helle Farbwerte der Diagramme durch CSS-Variablen ersetzen, damit sie dem Thema der Seite folgen."""
    def ers(m):
        tag, stile = m.group(0), []
        for a in ("fill", "stroke"):
            mm = re.search(rf' {a}="(#[0-9a-fA-F]{{6}})"', tag)
            if mm and mm.group(1).lower() in HEX2TOK:
                tag = tag.replace(mm.group(0), "")
                stile.append(f"{a}:var(--{HEX2TOK[mm.group(1).lower()]})")
        if not stile:
            return tag
        ende = "/>" if tag.endswith("/>") else ">"
        return tag[:-len(ende)] + f' style="{";".join(stile)}"' + ende
    return re.sub(r"<(?:text|rect|line|circle|polyline|path)\b[^>]*>", ers, svg)


def bild(funktion, sp):
    name, titel, desc, s, h = funktion(DATEN, sp)
    slug = f"{name}-{sp}".replace(".", "-")
    svg = (f'<svg viewBox="0 0 {D.W} {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">'
           f'<title id="{slug}-title">{e(titel[:60])}</title><desc id="{slug}-desc">{e(desc)}</desc>' + "".join(s.e) + "</svg>")
    return f'<figure class="bild"><div class="rollen">{themen(svg)}</div></figure>'


def stempel(datei):
    """Kurzer Inhaltsstempel für die Adresse einer Datei: Der Browser behält Bilder einen Monat, eine geänderte Datei bekommt so eine neue Adresse."""
    return hashlib.sha256(open(os.path.join(HIER, datei), "rb").read()).hexdigest()[:8]


def tabelle(kopf, zeilen, klasse=""):
    th = "".join(f"<th>{e(k)}</th>" for k in kopf)
    tr = "".join("<tr>" + "".join(f'<td{" class=zahl" if i else ""}>{c}</td>' for i, c in enumerate(zl)) + "</tr>" for zl in zeilen)
    return f'<div class="rollen"><table class="{klasse}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def terminal_strom(strom, sp):
    """Die Strommessung als Konsolenblock, mit Balken aus Blockzeichen. Zusammenfassung der JSON-Datei, kein Mitschnitt."""
    en = sp == "en"
    namen = {"leer": ("Leerlauf", "idle"), "geladen": ("geladen", "loaded"), "schreiben": ("Schreiben", "writing"), "lesen": ("Einlesen", "reading")}
    kopf = f'{"PHASE":<11}{("TOTAL" if en else "GESAMT"):>7}  {("CARD" if en else "KARTE"):>7}   {"0 W":<24}600 W   {"SPEED" if en else "TEMPO"}'
    zeilen = ['<span class="g">$ python3 messen/betrieb.py strom</span>', f'<span class="g">{kopf}</span>']
    for ph in ("leer", "geladen", "schreiben", "lesen"):
        w, k = strom[ph]["usv_w"]["mittel"], strom[ph]["karte_w"]["mittel"]
        n, nk = round(w / 600 * 28), round(k / 600 * 28)
        balken = f'<span class="a">{"█" * nk}</span><span class="s">{"█" * (n - nk)}</span><span class="r">{"░" * (28 - n)}</span>'
        tps = strom[ph].get("tps")
        tempo = (("about 70 tokens/s" if en else "rund 70 Token/s") if ph == "schreiben" else f'{z(tps, sp, 0)} {"tokens/s" if en else "Token/s"}') if tps else ""   # Schreiben als runde Zahl (Frank, 19.11.2026); gemessen sind hier 68,3
        zeilen.append(f'{namen[ph][1 if en else 0]:<11}{z(w, sp, 0) + " W":>7}  {z(k, sp, 0) + " W":>7}   {balken}   {tempo}')
    s = strom["schreiben"]
    zeilen.append(f'<b>→ {z(s["wh_je_1000_token_gesamt"], sp)} Wh {"per 1,000 written tokens" if en else "je 1.000 geschriebene Token"}</b> '
                  f'<span class="g">({z(s["wh_je_1000_token_ueber_leerlauf"], sp)} Wh {"above idle" if en else "über Leerlauf"})</span>')
    legende = ('<span class="a">█</span> card alone  <span class="s">█</span> NAS and dock without the card' if en else '<span class="a">█</span> Karte allein  <span class="s">█</span> NAS und Dock ohne die Karte')
    schild = "NAS AND DOCK · MEASURED AT THE UPS" if en else "NAS UND DOCK · AN DER USV GEMESSEN"
    return f'<div class="rahmen"><span class="schild">{schild}</span><pre class="plan konsole-block">' + "\n".join(zeilen) + f'\n<span class="g">{legende}</span></pre></div>'


def kalender(dock, sp):
    """Störungskalender: ein Zeichen je Tag, eine Zeile je Woche."""
    import datetime as dt
    en = sp == "en"
    tage = {}
    for v in dock["vorfaelle"]:
        d = v["beginn"][:10]
        art = "x" if v["link_down"] else ("t" if v["ursache"] == "selbst-ausgeloest" else "s")
        alt = tage.get(d)
        tage[d] = "x" if "x" in (art, alt) else ("s" if "s" in (art, alt) else "t")
    a, ende = dt.date.fromisoformat(dock["zeitraum"][0]), dt.date.fromisoformat(dock["zeitraum"][1])
    montag = a - dt.timedelta(days=a.weekday())
    zeichen = {"s": '<span class="s">▪</span>', "t": '<span class="g">▫</span>', "x": '<span class="x">✗</span>', None: '<span class="r">·</span>'}
    kopf = "        Mo Tu We Th Fr Sa Su" if en else "        Mo Di Mi Do Fr Sa So"
    zeilen = [f'<span class="g">{kopf}</span>']
    while montag <= ende:
        zellen = []
        for i in range(7):
            d = montag + dt.timedelta(days=i)
            zellen.append("  " if d < a or d > ende else zeichen[tage.get(d.isoformat())] + " ")
        zeilen.append(f'<span class="g">{montag.strftime("%d %b" if en else "%d.%m."):<8}</span>' + " ".join(zellen))
        montag += dt.timedelta(days=7)
    leg = ('<span class="r">·</span> quiet   <span class="s">▪</span> disturbance, card stays on the bus   <span class="g">▫</span> caused by me   <span class="x">✗</span> card dropped off the bus' if en else
           '<span class="r">·</span> ruhig   <span class="s">▪</span> Störung, Karte bleibt am Bus   <span class="g">▫</span> von mir ausgelöst   <span class="x">✗</span> Karte vom Bus gefallen')
    schild = "DISTURBANCES AT THE DOCK PORT · 9 SEP TO 15 NOV 2026" if en else "STÖRUNGEN AM DOCK-ANSCHLUSS · 09.09. BIS 15.11.2026"
    return f'<div class="rahmen"><span class="schild">{schild}</span><pre class="plan konsole-block">' + "\n".join(zeilen) + f'\n\n<span class="g">{leg}</span></pre></div>'


def regeln(sp):
    """Die vier Regeln wörtlich aus docs/agent(.de).md: der erste Codeblock dort."""
    return open(os.path.join(REPO, "docs", "agent.md" if sp == "en" else "agent.de.md"), encoding="utf-8").read().split("```")[1].strip("\n")


def verdrahtung(sp):
    t = open(os.path.join(REPO, "README.md" if sp == "en" else "README.de.md"), encoding="utf-8").read()
    block = t.split("```")[1].strip("\n")
    zeilen = block.split("\n")
    zeilen[-1] = f'<b>{e(zeilen[-1])}</b>'
    return "\n".join(zeilen[:-1] and [e(x) for x in zeilen[:-1]] + [zeilen[-1]])


def stand():
    try:
        h = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        h = ""
    return h


def seite(sp):
    en = sp == "en"
    T = (lambda de, en_: en_ if en else de)
    LB = lambda n: json.load(open(D.betriebsdatei(DATEN, n), encoding="utf-8"))   # Nachmessung auf dem Eigenbau, wo es sie gibt
    strom = LB("strom-faber.json")["phasen"]
    liber_tps = LB("strom-liber.json")["phasen"]["schreiben"]["tps"]   # die unzensierte Fassung im täglichen Einsatz
    kalt = [k["erste_antwort_s"] for k in LB("kaltstart-faber.json")["laeufe"]]
    werk = {s["stufe"]: s for s in L("2026-11-15-betrieb", "werksmodell.json")["stufen"]}
    neben = LB("nebenlast.json")
    dock = L("dock-2026-11-15", "vorfaelle.json")
    gpu = max(L("2026-11-15-betrieb", "dicht70-gpu.json")["stufen"], key=lambda s: s["schreiben_tps_median"])
    ab = D.ohne_switch(DATEN, list(strom.values()) + list(werk.values()) + [gpu])   # Switch an derselben USV abziehen
    for ph_ in ("schreiben", "lesen"):
        strom[ph_]["wh_je_1000_token_ueber_leerlauf"] = round((strom[ph_]["usv_w"]["mittel"] - strom["leer"]["usv_w"]["mittel"]) / strom[ph_]["tps"] / 3.6, 3)
    pfad = lambda n: D.betriebsdatei(DATEN, n)
    zwei = LB("zwei.json")["phasen"] if os.path.exists(pfad("zwei.json")) else None
    qual = LB("qualitaet.json") if os.path.exists(pfad("qualitaet.json")) else None
    warte = LB("wartezeit.json")["faelle"] if os.path.exists(pfad("wartezeit.json")) else None
    s, l = strom["schreiben"], strom["lesen"]
    faktor = round(werk["xtx-vulkan"]["schreiben_tps_median"] / werk["ugreen-werk"]["schreiben_tps_median"])
    readme = GH + ("#readme" if en else "/blob/main/README.de.md")
    doc = lambda name: f"{GH}/blob/main/docs/{name}{'' if en else '.de'}.md"

    sw = D.schalter_werte(DATEN)            # Messnacht 17./18.11.: Release 0.2.14 ohne und mit den 28 Schaltern (Kapitel 5, Herleitung)
    bench = lambda ps: {k: D.med([D.strata_bench(os.path.join(DATEN, q))[k] for q in ps]) for k in ("4K", "16K", "32K", "chat", "agent")}
    bx, br = bench(D.XTX_BENCH), bench(D.VERSIONEN[-1][1])          # Eigenbau und unverändertes Release derselben Version, im Wechsel gemessen
    xt = D.tiefe_daten(DATEN, D.TIEFE_XTX)
    tm = lambda label, ziel, f: statistics.median(r[f] for r in xt[label][ziel])
    lese = {m_: [tm(f"{m_}-xtx", t_, "prompt_tps") for t_ in sorted(xt[f"{m_}-xtx"])] for m_ in ("faber", "liber")}
    schreib = [tm("faber-xtx", t_, "decode_tps") for t_ in sorted(xt["faber-xtx"])]
    ab16 = [int(round(f_(v for m_ in lese.values() for v in m_[2:]), -2)) for f_ in (min, max)]
    r1 = lambda v: math.floor(v * 10 + 0.5) / 10          # kaufmännisch auf eine Stelle
    schreib_sp = (math.floor(round(min(schreib), 1) + 0.5), math.floor(round(max(schreib), 1) + 0.5))   # wie die Tabelle im README: erst auf eine Stelle
    frei = sorted(json.load(open(os.path.join(DATEN, D.XTX_DATEN, f"memory-{m_}.json"), encoding="utf-8"))["ram_available_gib"] for m_ in ("faber", "liber"))
    XV, XD, XE = D.XTX_VER, D.XTX_TAG["de"], D.XTX_TAG["en"]
    xtx_repo = "https://github.com/faf-net/strata-xtx"
    zahlen = [
        (T("rund 70", "about 70"), T("Token je Sekunde", "tokens per second"), T(f"Schreiben: {z(s['tps'], sp, 1)} bei langen, {z(bx['chat'], sp, 1)} bei kurzen Antworten", f"writing: {z(s['tps'], sp, 1)} with long, {z(bx['chat'], sp, 1)} with short answers"), True),
        ("256K", T("Token Kontext", "tokens of context"), T("versteckte Zahl bis 250K in 7 von 7 Fällen gefunden", "hidden number found 7 of 7 times up to 250K"), False),
        (z(s["wh_je_1000_token_gesamt"], sp), T("Wh je 1.000 Token", "Wh per 1,000 tokens"), T("NAS und Dock, am Original", "NAS and dock, original"), False),
        (z(statistics.median(kalt), sp, 0) + " s", T("Kaltstart", "cold start"), T("leere Karte bis erstes Wort", "empty card to first word"), False),
        (f"{faktor}×", T("schneller als ab Werk", "faster than as shipped"), T("UGREENs eigenes Modell auf der Karte", "UGREEN's own model on the card"), False),
        (z(bx["32K"] / br["32K"], sp, 1) + "×", T("schneller einlesen", "faster prompt reading"), T(f"mein Eigenbau strata-xtx: {z(bx['32K'], sp, 0)} statt {z(br['32K'], sp, 0)} Token/s bei 32K", f"my own build strata-xtx: {z(bx['32K'], sp, 0)} instead of {z(br['32K'], sp, 0)} tokens/s at 32K"), True),
    ]
    kacheln = "".join(f'<div class="kachel{" haupt" if h else ""}"><div class="wert">{w}</div><div class="was">{e(a)}</div><div class="neben">{e(b)}</div></div>' for w, a, b, h in zahlen)

    wz = lambda k, name: [e(name), z(werk[k]["schreiben_tps_median"], sp), z(werk[k]["einlesen"]["tps"], sp, 0), z(werk[k]["usv_w"]["mittel"], sp, 0) + " W", z(werk[k]["wh_je_1000_token_gesamt"], sp) + " Wh"]
    t_werk = tabelle([T("Weg", "Path"), T("Schreiben T/s", "Decode tok/s"), T("Einlesen T/s", "Prompt tok/s"), T("NAS und Dock", "NAS and dock"), T("je 1.000 Token", "per 1,000 tokens")],
                     [wz("ugreen-werk", T("ab Werk: UGOS-Server auf der Arc-iGPU", "as shipped: UGOS server on the Arc iGPU")), wz("cpu", T("nur CPU, llama.cpp", "CPU only, llama.cpp")),
                      wz("xtx-vulkan", T("RX 7900 XTX im Dock, llama.cpp Vulkan", "RX 7900 XTX in the dock, llama.cpp Vulkan"))])
    w = lambda ph, f="usv_w": z(strom[ph][f]["mittel"], sp, 0) + " W"
    t_strom = tabelle([T("Phase", "Phase"), T("An der USV", "At the UPS"), T("Karte allein", "Card alone")],
                      [[T("Leerlauf, kein Modell geladen", "idle, no model loaded"), w("leer"), w("leer", "karte_w")], [T("Modell geladen, ruhend", "model loaded, idle"), w("geladen"), w("geladen", "karte_w")],
                       [T(f"Schreiben, {z(s['tps'], sp)} Token/s", f"writing, {z(s['tps'], sp)} tokens/s"), w("schreiben"), w("schreiben", "karte_w")],
                       [T(f"Einlesen, {z(l['tps'], sp, 0)} Token/s", f"reading, {z(l['tps'], sp, 0)} tokens/s"), w("lesen"), w("lesen", "karte_w")]])
    su = dock["summe"]
    ld = lambda u: sum(1 for v in dock["vorfaelle"] if v["ursache"] == u and v["link_down"])
    t_dock = tabelle([T("Ursache", "Cause"), T("Störungen", "Disturbances"), T("Karte vom Bus gefallen", "Card dropped off the bus")],
                     [[T("Sonntagsreihe, jede Woche zur selben Uhrzeit, Ursache offen", "Sunday series, same time every week, cause open"), su["sonntagsreihe"], ld("sonntagsreihe")],
                      [T("Mittwochsreihe, wöchentlicher Akkutest der USV", "Wednesday series, the UPS's weekly battery test"), su["usv-akkutest"], ld("usv-akkutest")],
                      [T("von mir ausgelöst (Stecker gezogen, Geräte an derselben USV geschaltet)", "caused by me (plug pulled, devices switched on the same UPS)"), su["selbst-ausgeloest"], ld("selbst-ausgeloest")],
                      [T("ohne bekannten Anlass", "no known cause"), su["ohne-zuordnung"], ld("ohne-zuordnung")],
                      [f"<b>{T('gesamt in 67 Tagen', 'total in 67 days')}</b>", f"<b>{dock['vorfaelle_gesamt']}</b>", f"<b>{dock['vorfaelle_mit_link_down']}</b>"]])
    tr = neben["transkodieren"]

    teile = []
    A = teile.append
    def kapitel(nr, anker, titel, einleitung=None):
        A(f'<section id="{anker}"><div class="nr">{nr:02d}</div><h2>{e(titel)}</h2>' + (f'<p class="vorspann">{einleitung}</p>' if einleitung else ""))
    P = lambda t: A(f"<p>{t}</p>")
    zu = lambda: A("</section>")

    kapitel(1, "anlage", T("Was hier läuft", "What runs here"),
            T("Auf dem NAS mit der Karte im Dock läuft, wofür man sonst einen Dienst aus der Cloud nimmt: Chat, Agent, Bilder und Programmieren, erreichbar auch über den Messenger und aus eigenen Programmen. Gerechnet wird im Haus.",
              "The NAS with the card in the dock runs what you would otherwise take from a cloud service: chat, agent, pictures and coding, also reachable through a messenger and from your own programs. The computing happens at home."))
    A(bild(D.aufbau, sp))
    karten = [
        (T("Chat im Browser", "Chat in the browser"), "Open WebUI",
         T("Wie ein Chat-Dienst aus der Cloud, nur kommen die Antworten von der eigenen Karte: ein Konto je Person, Verlauf, Dateien hochladen, Websuche über ein eigenes SearXNG.",
           "Like a chat service from the cloud, except that the answers come from your own card: one account per person, history, file upload, web search through an own SearXNG."),
         T(f"erstes Wort nach einer Pause: <b>{z(statistics.median(kalt), sp, 0)} s</b> · danach rund 70 Token/s", f"first word after a break: <b>{z(statistics.median(kalt), sp, 0)} s</b> · then about 70 tokens/s")),
        ("Agent", "Hermes Agent",
         T("Ein Agent, den man im Browser oder über den Messenger erreicht, der eigene Werkzeuge bedient und Aufgaben nach Zeitplan erledigt, mit bis zu 256K Token Kontext. Regeln im Systemprompt und ein kleiner Prüfer halten ihn vom Erfinden ab.",
           "An agent you reach in the browser or through a messenger, that uses its own tools and runs tasks on a schedule, with up to 256K tokens of context. Rules in the system prompt and a small checker keep it from making things up."),
         T("Erfundenes erkannt mit Regel: <b>104 von 120</b>", "made-up things recognised with the rule: <b>104 of 120</b>")),
        ("Messenger", "Signal",
         T("Dem Agenten vom Handy schreiben wie einem Kontakt, auch von unterwegs. Ich empfehle und bevorzuge Signal, weil die Nachrichten dort Ende-zu-Ende-verschlüsselt sind. Telegram und Discord habe ich ebenfalls erfolgreich getestet.",
           "Write to the agent from your phone like to a contact, also when away from home. I recommend and prefer Signal, because messages there are end-to-end encrypted. I have also tested Telegram and Discord successfully."),
         T("läuft über den Agenten · <b>Ende-zu-Ende-verschlüsselt</b> nur bei Signal", "runs through the agent · <b>end-to-end encrypted</b> only with Signal")),
        (T("Bilder", "Pictures"), "ComfyUI",
         T("„Mach ein Bild von …“ im Chat oder im Messenger: Die Weiche entlädt das Sprachmodell und lädt ein Bildmodell auf dieselbe Karte. Beides zugleich passt nicht in 24 GB.",
           "\"Make a picture of …\" in the chat or the messenger: the switch unloads the language model and loads a picture model onto the same card. Both at once do not fit into 24 GB."),
         T("<b>8–66 s</b> je Bild · Wechsel vom Sprachmodell 21–27 s", "<b>8–66 s</b> per picture · swapping from the language model 21–27 s")),
        (T("Programmieren im Terminal", "Coding in the terminal"), "OpenCode 2",
         T("Ein Programmier-Agent im Terminal, der Dateien liest, ändert und Befehle ausführt. Er spricht dieselbe Adresse an wie der Chat, das Modell wählt man in der Sitzung. Der Code bleibt dabei im Haus.",
           "A coding agent in the terminal that reads and changes files and runs commands. It talks to the same address as the chat, and you pick the model in the session. The code stays at home."),
         T("teilt sich die Karte mit Chat und Agent: <b>eine Anfrage nach der anderen</b>", "shares the card with chat and agent: <b>one request at a time</b>")),
        (T("Eigene Programme", "Your own programs"), T("API im OpenAI-Format", "API in the OpenAI format"),
         T("Jedes Programm, das einen Cloud-Dienst im OpenAI-Format ansprechen kann, lässt sich auf die Adresse im Heimnetz umstellen: Skripte, Editor-Erweiterungen, Automationen. Ein Konto bei einem Anbieter ist nicht nötig.",
           "Any program that can talk to a cloud service in the OpenAI format can be pointed at the address in the home network instead: scripts, editor extensions, automations. No account with a provider is needed."),
         T("<b>rund 70 Token/s</b> · eine Adresse, das Modell wählt der Aufruf", "<b>about 70 tokens/s</b> · one address, the call picks the model")),
    ]
    A('<div class="anwendungen">' + "".join(f'<div class="anwendung"><span class="dach">{e(a)}</span><h3>{e(b)}</h3><p>{c}</p><div class="mess">{m}</div></div>' for a, b, c, m in karten) + "</div>")
    P(T("Drei Dinge verlassen dabei das Haus: die Suchanfragen der Websuche, die Adressen der Seiten, die der Agent liest, und die Nachrichten, die über den Messenger-Dienst zum Agenten laufen (bei Signal Ende-zu-Ende-verschlüsselt; bei Telegram und Discord kann der Dienst mitlesen). Die Suchanfragen gehen über ein VPN hinaus: Die Suchmaschinen sehen die Adresse des VPN-Anbieters, nicht den eigenen Anschluss. Die Seiten ruft ein Webleser ab, Crawl4AI auf der iDX, ebenfalls über ein VPN; auch die Zielseiten sehen die Adresse des VPN-Anbieters, nicht den eigenen Anschluss. Alles andere, auch jedes hochgeladene Dokument, bleibt auf den eigenen Geräten.",
        "Three things leave the house: the search queries of the web search, the addresses of the pages the agent reads, and the messages that travel to the agent through the messenger service (end-to-end encrypted with Signal; with Telegram and Discord the service can read along). The search queries go out through a VPN: the search engines see the VPN provider's address, not your own line. The pages are fetched by a web reader, Crawl4AI on the iDX, through a VPN as well; the target sites, too, see the VPN provider's address, not your own line. Everything else, including every uploaded document, stays on your own machines."))
    zu()

    kapitel(2, "nas", T("Das NAS bleibt ein NAS", "The NAS stays a NAS"),
            T("Auch bei geladenem Modell läuft alles weiter, wofür die iDX gekauft wurde: Fotos, Video und Dateifreigaben. Die Karte im Dock nimmt ihnen nichts weg, weil sie eine eigene Grafikeinheit haben.",
              "Even with the model loaded, everything the iDX was bought for keeps running: photos, video and file shares. The card in the dock takes nothing away from them, because they have a graphics unit of their own."))
    A(bild(D.parallel, sp))
    P(T("Die iDX macht weiter, wofür sie gekauft wurde, mit den Diensten, die UGOS mitbringt: <b>Fotos</b> für die Fotosammlung, <b>Video</b> für die Mediathek, <b>Dateifreigaben</b> über SMB und die Überwachung der USV. Auch Docker kommt aus UGOS; darin laufen Chat, Suche und Agent. Die eingebaute Arc-iGPU bleibt für Transkodierung und Bilderkennung frei, die Karte im Dock rechnet nur Sprach- und Bildmodelle.",
        "The iDX keeps doing what it was bought for, with the services UGOS brings along: <b>Photos</b> for the photo library, <b>Video</b> for the media library, <b>file shares</b> over SMB and UPS monitoring. Docker comes from UGOS too; chat, search and agent run in it. The built-in Arc iGPU stays free for transcoding and photo recognition, the card in the dock only runs language and picture models."))
    P(T(f"Während das Modell schrieb, kam eine 17,7-GB-Datei mit {z(neben['download']['waehrend_schreiben']['mb_s'], sp, 0)} MB/s vom NAS ({z(neben['download']['ohne_modell']['mb_s'], sp, 0)} MB/s ohne Modell; {neben['download'].get('grenze_de', 'begrenzt hat beide Male der 5-Gbit/s-Anschluss des Arbeitsplatzes')}). Die Transkodierung von 4K nach 1080p auf der Arc-iGPU fiel von {z(tr['ohne_modell_bilder_s'][0], sp, 0)} auf {z(min(tr['waehrend_schreiben_bilder_s']), sp, 0)}–{z(max(tr['waehrend_schreiben_bilder_s']), sp, 0)} Bilder je Sekunde, immer noch {round(min(tr['waehrend_schreiben_bilder_s']) / 30)}-mal so schnell wie die Wiedergabe. Das Schreibtempo des Modells blieb unverändert ({neben.get('stand_de', 'gemessen am 16.11.2026 auf Strata 0.2.14')}). {neben.get('nicht_de', 'Nicht gemessen: SMB und ein Arbeitsplatz mit 10 Gbit/s.')}",
        f"While the model was writing, a 17.7 GB file came off the NAS at {z(neben['download']['waehrend_schreiben']['mb_s'], sp, 0)} MB/s ({z(neben['download']['ohne_modell']['mb_s'], sp, 0)} MB/s without a model; {neben['download'].get('grenze_en', 'both times the client' + chr(39) + 's 5 Gbit/s port was the limit')}). Transcoding 4K to 1080p on the Arc iGPU dropped from {z(tr['ohne_modell_bilder_s'][0], sp, 0)} to {z(min(tr['waehrend_schreiben_bilder_s']), sp, 0)}–{z(max(tr['waehrend_schreiben_bilder_s']), sp, 0)} frames per second, still {round(min(tr['waehrend_schreiben_bilder_s']) / 30)} times as fast as playback. The model's decode speed did not change ({neben.get('stand_en', 'measured on 16 Nov 2026 on Strata 0.2.14')}). {neben.get('nicht_en', 'Not measured: SMB, and a 10 Gbit/s client.')}"))
    A(bild(D.speicher, sp))
    P(T(f"Der Preis ist Arbeitsspeicher: Mit geladenem 125B-Modell bleiben von 62 GiB je nach Fassung {z(r1(frei[0]), sp, 1)} bis {z(r1(frei[1]), sp, 1)} GiB verfügbar (gemessen am {XD}). Ein zweiter großer Dienst daneben passt nicht.",
        f"The price is memory: with the 125B model loaded, {z(r1(frei[0]), sp, 1)} to {z(r1(frei[1]), sp, 1)} GiB of the 62 GiB stay available, depending on the version (measured on {XE}). A second large service does not fit next to it."))
    zu()

    kapitel(3, "dock", T("Lohnt sich die Karte im Dock?", "Is the card in the dock worth it?"),
            T("UGREEN liefert die iDX mit einer KI-Konsole aus, die ein eigenes Modell auf die eingebaute Arc-iGPU lädt. Dieselbe Datei, drei Wege:",
              "UGREEN ships the iDX with an AI console that loads its own model onto the built-in Arc iGPU. The same file, three paths:"))
    A(bild(D.werksmodell, sp)); A(t_werk)
    P(T(f"Auf der Karte schreibt das eingebaute Modell <b>{faktor}-mal so schnell</b> wie ab Werk und braucht je 1.000 Token {z(werk['xtx-vulkan']['wh_je_1000_token_gesamt'], sp)} statt {z(werk['ugreen-werk']['wh_je_1000_token_gesamt'], sp)} Wh. Die CPU allein schreibt schneller als der iGPU-Server, liest einen Prompt aber gut siebenmal langsamer. „Ab Werk“ ist der Server, den UGOS nach dem Download selbst startet; ich habe ihn über seinen Unix-Socket gemessen. Die zweite Laufzeit der KI-Konsole ist ein CUDA-Build und startet mit einer AMD-Karte nicht.",
        f"On the card the built-in model writes <b>{faktor} times faster</b> than as shipped and needs {z(werk['xtx-vulkan']['wh_je_1000_token_gesamt'], sp)} instead of {z(werk['ugreen-werk']['wh_je_1000_token_gesamt'], sp)} Wh per 1,000 tokens. The CPU alone out-writes the iGPU server but reads a prompt about seven times more slowly. \"As shipped\" is the server UGOS starts by itself after the download; I measured it through its Unix socket. The AI console's second runtime is a CUDA build and does not start with an AMD card."))
    if qual:
        F, Q = qual["modelle"]["faber"], qual["modelle"]["qwen35"]
        A(f"<h3>{T('Und die Qualität? Dieselben Aufgaben für beide Modelle', 'And the quality? The same tasks for both models')}</h3>")
        A(bild(D.qualitaet, sp))
        P(T("Das kleine Modell schreibt fast doppelt so schnell, denkt aber viel länger nach: 2,7-mal so viele Token für dieselben Aufgaben, und in neun Aufgaben war das Denkbudget aufgebraucht, bevor eine Antwort kam. Dafür lässt es den Arbeitsspeicher des NAS frei. Wer vor allem ein NAS will und gelegentlich chattet, ist mit dem kleinen Modell auf der Karte gut bedient; für einen Agenten und lange Texte lohnt das große.",
            "The small model writes almost twice as fast but thinks much longer: 2.7 times as many tokens for the same tasks, and in nine tasks the reasoning budget was used up before an answer came. In return it leaves the RAM of the NAS free. If you mainly want a NAS and chat now and then, the small model on the card serves you well; for an agent and long texts the big one pays off."))
    zu()

    kapitel(4, "modell", T("Ein 125B-Modell auf 24 GB", "A 125B model on 24 GB"),
            T("Qwen3.8-Flash-Next ist ein Mixture-of-Experts-Modell: Je Token rechnen nur wenige Experten. Strata hält die häufig gebrauchten im VRAM und den Rest im schnellen RAM der iDX. Es läuft in drei Fassungen: unzensiert im täglichen Einsatz, das Original für die erste Messung und als Rückfall, eine kleinere Quantisierung nur zum Vergleich.",
              "Qwen3.8-Flash-Next is a Mixture-of-Experts model: only a few experts run per token. Strata keeps the frequently used ones in VRAM and the rest in the iDX's fast RAM. It runs in three versions: uncensored in daily use, the original for the first measurement and as the fallback, and a smaller quantization only for comparison."))
    A(f'<div class="rahmen"><span class="schild">{T("VERDRAHTUNG", "WIRING")}</span><pre class="plan">{verdrahtung(sp)}</pre></div>')
    A(bild(D.tiefe, sp))
    P(T(f"Das Schreibtempo bleibt von 1K bis 248K Token Kontext bei {schreib_sp[0]} bis {schreib_sp[1]} Token je Sekunde. Ab 16K liest mein Eigenbau {z(ab16[0], sp, 0)} bis {z(ab16[1], sp, 0)} Token je Sekunde, das unveränderte Release rund 1.300, über eine PCIe-Anbindung mit nur vier Lanes. Was der Eigenbau ist und wie er geprüft wurde, steht in <a href=\"#eigenbau\">Kapitel 5</a>.",
        f"Decode speed stays at {schreib_sp[0]} to {schreib_sp[1]} tokens per second between 1K and 248K tokens of context. From 16K on my own build reads {z(ab16[0], sp, 0)} to {z(ab16[1], sp, 0)} tokens per second, the unchanged release about 1,300, over a PCIe link with only four lanes. What the own build is and how it was checked is in <a href=\"#eigenbau\">chapter 5</a>."))
    P(T(f"Das Schreibtempo hängt vom Text ab, deshalb stehen auf dieser Seite verschiedene Zahlen: Der Entwurfskopf (MTP) schlägt mehrere Token auf einmal vor und trifft bei vorhersehbarem Text öfter. Lange Antworten kommen beim Original mit {z(s['tps'], sp, 0)} Token je Sekunde, bei der unzensierten Fassung im täglichen Einsatz mit {z(liber_tps, sp, 0)}; in Stratas eigenem Benchmark sind es {z(bx['agent'], sp, 0)} im Agenten- und {z(bx['chat'], sp, 0)} im Chat-Teil, nach einem sehr langen Prompt etwas weniger. Die runde 70 im Seitenkopf fasst die Werte für lange und für kurze Antworten zusammen.",
        f"Decode speed depends on the text, which is why this page shows different numbers: the draft head (MTP) proposes several tokens at once and is right more often on predictable text. Long answers come at {z(s['tps'], sp, 0)} tokens per second with the original and at {z(liber_tps, sp, 0)} with the uncensored version in daily use; Strata's own benchmark gives {z(bx['agent'], sp, 0)} in its agent part and {z(bx['chat'], sp, 0)} in its chat part, and a little less after a very long prompt. The round 70 in the page header sums up the values for long and for short answers."))
    A(bild(D.betrieb, sp))
    P(T(f"Zum Vergleich ein dichtes 70B-Modell (Llama 3.3, Q4) auf derselben Karte: <b>{z(gpu['schreiben_tps_median'], sp, 1)} Token je Sekunde</b>, weil für jedes Token alle Gewichte gelesen werden und die Hälfte davon hinter der CPU liegt.",
        f"For comparison, a dense 70B model (Llama 3.3, Q4) on the same card: <b>{z(gpu['schreiben_tps_median'], sp, 1)} tokens per second</b>, because every token reads all weights and half of them sit behind the CPU."))
    A(f"<h3>{T('Sechs Modelle auf derselben Karte', 'Six models on the same card')}</h3>")
    A(bild(D.dicht_moe, sp))
    P(T("Auf der Karte laufen auch kleinere Modelle, die ganz in den Grafikspeicher passen. Zwei dichte Modelle schreiben halb so schnell wie das 125B-Modell und bestehen nicht mehr Aufgaben. UGREENs mitgeliefertes Qwen 3.5 schreibt am schnellsten, hat aber das schwächste Deutsch und besteht die wenigsten Aufgaben. Schnell und gut im Deutschen zugleich sind nur die Fassungen des 125B-Modells; die unzensierte liegt im Deutschen vorn. Die Zahlen dieses Diagramms stammen von Strata 0.2.12; auf 0.2.14 besteht das 125B-Modell 98 statt 96 von 102 Aufgaben. Ein bis zwei Aufgaben kippen zwischen zwei Läufen derselben Version, 96 und 98 heißen also gleich.",
        "Smaller models that fit entirely into video memory run on the card as well. Two dense models write at half the speed of the 125B model and do not pass more tasks. UGREEN's bundled Qwen 3.5 writes fastest but has the weakest German and passes the fewest tasks. Only the versions of the 125B model are both fast and good at German; the uncensored one leads in German. The numbers in this chart are from Strata 0.2.12; on 0.2.14 the 125B model passes 98 instead of 96 of 102 tasks. One or two tasks flip between two runs of the same release, so 96 and 98 mean equal."))
    A(f"<h3>{T('Und gegen ein Modell aus der Cloud?', 'And against a model in the cloud?')}</h3>")
    A(bild(D.cloud_vergleich, sp))
    A(f"<h3 id=\"warten\">{T('Wartezeiten im Alltag', 'Waiting times in everyday use')}</h3>")
    if warte and zwei:
        A(bild(D.wartezeit, sp))
    P(T("Im laufenden Gespräch kommt die Antwort sofort, weil das Modell den bisherigen Verlauf behält. Lange Texte liest es einmal; Folgefragen dazu sind wieder schnell. Nach 30 Minuten ohne Anfrage wird das Modell entladen und beim nächsten Mal neu geladen.",
        "In a running conversation the answer comes at once, because the model keeps the conversation so far. It reads a long text once; follow-up questions on it are fast again. After 30 minutes without a request the model is unloaded and loaded again next time.")
      + (T(f" Für gemeinsame Nutzung ein Modell für alle: Wechseln zwei Personen zwischen zwei Modellen, lädt die Karte jedes Mal um ({z(zwei['wechsel']['warten_median_s'], sp, 0)} s).",
           f" For shared use, pick one model for everyone: if two people alternate between two models, the card reloads every time ({z(zwei['wechsel']['warten_median_s'], sp, 0)} s).") if zwei and "wechsel" in zwei else ""))
    zu()

    kapitel(5, "eigenbau", T("strata-xtx: Strata für eine RX 7900 XTX", "strata-xtx: Strata for an RX 7900 XTX"),
            T(f"Seit dem 18.11.2026 läuft hier kein Strata-Release mehr, sondern ein eigener Bau mit einer kleinen Änderung: Er schaltet auf dieser Karte von selbst ein, was das Einlesen langer Prompts verdoppelt. Seit dem {XD} steht er auf Strata {XV}.",
              f"Since 18 Nov 2026 no Strata release runs here any more but a build of my own with one small change: on this card it turns on by itself what doubles the reading of long prompts. Since {XE} it sits on Strata {XV}."))
    A('<span id="schalter"></span>')
    dn = {k_: (a_, b_) for k_, a_, b_ in D.eigenbau_werte(DATEN)["dauer"]}
    vorteile = [(z(bx["32K"] / br["32K"], sp, 1) + "×", T("so schnell einlesen", "as fast at reading"), T(f"{z(bx['32K'], sp, 0)} statt {z(br['32K'], sp, 0)} Token/s bei 32K", f"{z(bx['32K'], sp, 0)} instead of {z(br['32K'], sp, 0)} tokens/s at 32K"), True),
                (f"{z(dn['250K'][1], sp, 0)} s", T("für 250.000 Token", "for 250,000 tokens"), T(f"das Release braucht {z(dn['250K'][0], sp, 0)} s", f"the release takes {z(dn['250K'][0], sp, 0)} s"), True),
                ("97 · 96–98", T("von 102 Aufgaben", "of 102 tasks"), T("Original · unzensierte Fassung; diese auf dem Release nachgemessen: dasselbe", "original · uncensored version; the latter re-measured on the release: the same"), False)]
    A('<div class="kacheln">' + "".join(f'<div class="kachel{" haupt" if h_ else ""}"><div class="wert">{w_}</div><div class="was">{e(a_)}</div><div class="neben">{e(b_)}</div></div>' for w_, a_, b_, h_ in vorteile) + "</div>")
    A(bild(D.eigenbau, sp))
    A(f"<h3>{T('Was er anders macht', 'What it does differently')}</h3>")
    P(T(f"Stratas Engine bringt Schalter für das Einlesen mit, die auf dieser Kartengeneration aus sind, weil mehrere die Rundung ändern. Mein Bau trägt eine Tabelle mit 27 davon im Code und schaltet sie ein, wenn genau eine eigenständige RX 7900 XTX oder XT unter Linux sichtbar ist; 26 setzt die Engine dabei neu, einer ist im Release schon an. In der Laufkonfiguration steht kein Schalter für das Einlesen mehr. Was man selbst setzt, wird nie überschrieben, und <code>STRATA_GFX1100_DEFAULTS=0</code> schaltet alles ab. Die Änderung umfasst rund 200 Zeilen in fünf Dateien und liegt samt Bauanleitung in einem eigenen Repository: <a href=\"{xtx_repo}\">faf-net/strata-xtx</a>. Es ist ein inoffizieller Ableger, kein Strata-Release.",
        f"Strata's engine ships switches for prompt reading that are off on this card generation because several of them change the rounding. My build carries a table of 27 of them in the code and turns them on when exactly one discrete RX 7900 XTX or XT is visible under Linux; the engine newly sets 26 of them, one is already on in the release. No prompt-reading switch is left in the run config. Whatever you set yourself is never overwritten, and <code>STRATA_GFX1100_DEFAULTS=0</code> turns everything off. The change is about 200 lines in five files and lives, with build instructions, in a repository of its own: <a href=\"{xtx_repo}\">faf-net/strata-xtx</a>. It is an unofficial fork, not a Strata release."))
    P(T(f"<b>Stahlblau ist das unveränderte Release, Bernstein mein Eigenbau</b>, beide auf Strata {XV}, im Wechsel gemessen am {XD} mit Stratas eigenem Benchmark, Karte in meiner leisen Einstellung. Über die ganze Tiefe liest das Original {z(lese['faber'][2], sp, 0)} Token je Sekunde bei 16K, {z(lese['faber'][3], sp, 0)} bei 65K und {z(lese['faber'][5], sp, 0)} bei 248K; die Variante mit Steuervektor, mit der mein Agent arbeitet, {z(lese['liber'][2], sp, 0)}, {z(lese['liber'][3], sp, 0)} und {z(lese['liber'][5], sp, 0)}. <b>250.000 Token sind in knapp anderthalb Minuten gelesen, das Release braucht dafür gut drei.</b> Das Schreiben bleibt gleich.",
        f"<b>Steel blue is the unchanged release, amber my own build</b>, both on Strata {XV}, measured alternately on {XE} with Strata's own benchmark, card in my quiet setting. Over the whole depth the original reads {z(lese['faber'][2], sp, 0)} tokens per second at 16K, {z(lese['faber'][3], sp, 0)} at 65K and {z(lese['faber'][5], sp, 0)} at 248K; the variant with control vector that my agent works with reads {z(lese['liber'][2], sp, 0)}, {z(lese['liber'][3], sp, 0)} and {z(lese['liber'][5], sp, 0)}. <b>250,000 tokens are read in just under a minute and a half; the release takes well over three.</b> Decode stays the same."))
    A(f"<h3>{T('Geprüft, bevor er in den Betrieb ging', 'Checked before it went into use')}</h3>")
    P(T("Jede Fassung durchläuft dieselbe Kette, mit beiden Modellen. <b>Qualität:</b> Mein Aufgabensatz ergibt 97 von 102 beim Original und 96 bis 98 bei der Variante mit Steuervektor, je nach Lauf; auf dem unveränderten Release ist es dasselbe, zwei Aufgaben besteht das Modell mal ja, mal nein. <b>Lange Prompts:</b> Die versteckte Zahl wurde bis 250.000 Token jedes Mal gefunden. <b>Dauerlauf:</b> 90 Minuten gemischte Anfragen, 1.232 Stück, keine fehlgeschlagen. <b>Selbstrettung:</b> Meldet die Engine nicht-endliche Werte und hilft Stratas eigener zweiter Versuch nicht, startet der Server sie einmal ohne die Tabelle neu und arbeitet im langsameren, exakten Modus weiter. Die auslösende Anfrage selbst endet dabei mit einem Fehler, die folgenden werden beantwortet; mit Stratas eingebauter Fehlerinjektion für beide Modelle nachgewiesen.",
        "Every version goes through the same chain, with both models. <b>Quality:</b> my task set gives 97 of 102 with the original and 96 to 98 with the variant with control vector, depending on the run; on the unchanged release it is the same, two tasks the model passes sometimes and sometimes not. <b>Long prompts:</b> the hidden number was found every time up to 250,000 tokens. <b>Endurance:</b> 90 minutes of mixed requests, 1,232 of them, none failed. <b>Self-rescue:</b> if the engine reports non-finite values and Strata's own retry does not help, the server restarts it once without the table and carries on in the slower, exact mode. The request that triggered it ends with an error, the following ones are answered; shown for both models with Strata's built-in fault injection."))
    A(f"<h3>{T('Der Zwischenschritt: dieselben Schalter von Hand', 'The intermediate step: the same switches set by hand')}</h3>")
    A(bild(D.schalter, sp))
    P(T("Bevor es den Eigenbau gab, habe ich die Schalter von Hand gesetzt: einen Satz von 28, die die unveränderte Engine kennt, am 17. und 18.11.2026 auf dem Release 0.2.14 gemessen: <b>Stahlblau ist Strata wie ausgeliefert, Bernstein dieselbe Engine mit den Schaltern in der Laufkonfiguration.</b> Das war der Zwischenschritt. Der Eigenbau trägt seitdem 27 Schalter selbst: Von den 28 wurde einer zur festen Regel für die Stückgröße, einer brachte nichts und entfiel, einer kam dazu. Von den rund 10 % beim Schreiben aus dieser Messung ist im Eigenbau wenig geblieben; es schreibt gleich bis leicht schneller.",
        "Before my own build existed I set the switches by hand: a set of 28 that the unchanged engine knows, measured on 17 and 18 Nov 2026 on the 0.2.14 release: <b>steel blue is Strata as shipped, amber the same engine with the switches in the run config.</b> That was the intermediate step. Since then my own build carries 27 switches itself: of the 28, one became a fixed rule for the chunk size, one brought nothing and was dropped, one was added. Of the roughly 10 % in decode from that measurement little is left in my own build; it writes equally fast to slightly faster."))
    A(bild(D.schalter_lang, sp))
    A(f"<h3>{T('Der Preis und die Grenzen', 'The price and the limits')}</h3>")
    P(T("Die Antworten sind nicht Bit für Bit dieselben wie ohne die Tabelle, weil sich die Rundung ändert; in meinen Prüfungen zeigt sich das nicht in der Qualität. Beim Einlesen zieht die Karte 25 bis 30 W mehr (Kapitel 8). Keiner der Schalter ist von Strata zugesichert: Ein Release kann einen umbenennen oder streichen, und die Engine ignoriert einen unbekannten Namen stillschweigend. Nicht gemessen habe ich die RX 7900 XT, eine Karte im vollen PCIe-x16-Steckplatz, ein anderes Modell oder Quant und Windows.",
        "The answers are not bit for bit the same as without the table, because the rounding changes; in my checks this does not show in quality. While reading, the card draws 25 to 30 W more (chapter 8). None of the switches is guaranteed by Strata: a release may rename or drop one, and the engine silently ignores an unknown name. I have not measured the RX 7900 XT, a card in a full PCIe x16 slot, another model or quant, or Windows."))
    A(f"<h3>{T('Wenn eine neue Strata-Version kommt', 'When a new Strata release arrives')}</h3>")
    P(T(f"Deshalb gibt es ein festes Verfahren: erst das unveränderte Release gegen das vorige messen, dann den Patch auf den neuen Quelltext setzen (er bricht ab, wenn eine Ankerstelle fehlt), bauen und die Kette oben durchlaufen; erst danach stelle ich den Betrieb um und messe die Diagramme dieser Seite neu. Bei {XV} hieß das: neue Ordnerstruktur, neues Bauskript, ein angepasster Test der Selbstrettung, und am Ende dieselben Werte wie auf 0.2.15.",
        f"So there is a fixed procedure: first measure the unchanged release against the previous one, then apply the patch to the new source (it aborts if an anchor is missing), build, and run the chain above; only then do I switch over and re-measure the charts on this page. For {XV} that meant: a new folder layout, a new build script, an adapted self-rescue test, and in the end the same figures as on 0.2.15.")
      + f' <a href="{doc("schalter")}">{T("Die Messnacht mit den 28 Schaltern im Einzelnen", "The night of measurements with the 28 switches in detail")}</a> · <a href="{xtx_repo}">{T("Patch und Bauanleitung", "Patch and build instructions")}</a>')
    zu()

    kapitel(6, "agent", T("Damit der Agent nicht erfindet", "Keeping the agent from making things up"),
            T("Ein lokales Modell weiß weniger als eines aus der Cloud und gibt das ungern zu. Der Agent zeigte zwei Schwächen: Er erfand Antworten zu Dingen, die es nicht gibt, und er kündigte Schritte an, für die er kein Werkzeug hat. Beides habe ich erst gemessen und dann gesenkt.",
              "A local model knows less than one from the cloud and does not like to admit it. The agent showed two weaknesses: it made up answers about things that do not exist, and it announced steps it has no tool for. I measured both first and then brought them down."))
    A(f"<h3>{T('Was in den Systemprompt gehört', 'What belongs in the system prompt')}</h3>")
    regeln = T("""<span class="g">Gegen das Erfinden · mit dieser Regel läuft mein Agent seit dem 16.11.2026</span>
<b>Beantworte, was du weißt. Kennst du eine Sache, einen Namen oder ein Werkzeug gar nicht, sag das, statt etwas zu erfinden. Das gilt besonders für Befehle, Optionen und Ortsnamen: Kennst du sie nicht sicher, sag das, auch wenn sie plausibel klingen.</b>
<span class="g">Erfundenes erkannt: 104 von 120 · erfundene Befehlsoptionen: 17 von 24 · echte Fragen richtig: 91 von 150, ohne Regel 95 (im Rauschen)</span>

<span class="g">Dazu für Agenten mit Werkzeugen</span>
<b>Nenne nur Werkzeuge und Parameter, die du wirklich hast. Gibt es keins, sag: „Dafür habe ich kein Werkzeug.“</b>
<span class="g">falsche Aufrufe: 15 → 10 von 60 · berechtigte Aufrufe: 41 → 32 von 50</span>

<span class="g">Strenge Regel · stattdessen, wenn eine falsche Antwort teurer ist als eine fehlende</span>
<b>Wenn du etwas nicht sicher weißt, sage ausdrücklich „Weiß ich nicht“. Das ist eine richtige Antwort. Erfinde keine Fakten und keine Handlungen. Raten ist schlechter als Nichtwissen.</b>
<span class="g">falsche Antworten: 58 → 30 von 150 · richtige: 90 → 84 · „Weiß ich nicht“: 36-mal</span>""",
               """<span class="g">Against making things up · my agent has run with this rule since 16 Nov 2026</span>
<b>Beantworte, was du weißt. Kennst du eine Sache, einen Namen oder ein Werkzeug gar nicht, sag das, statt etwas zu erfinden. Das gilt besonders für Befehle, Optionen und Ortsnamen: Kennst du sie nicht sicher, sag das, auch wenn sie plausibel klingen.</b>
<span class="g">in English: Answer what you know. If you do not know a thing, a name or a tool at all, say so instead of making something up. This applies especially to commands, options and place names: if you are not sure you know them, say so, even if they sound plausible.</span>
<span class="g">made-up things recognised: 104 of 120 · made-up command options: 17 of 24 · real questions right: 91 of 150, without a rule 95 (within the noise)</span>

<span class="g">In addition, for agents with tools</span>
<b>Nenne nur Werkzeuge und Parameter, die du wirklich hast. Gibt es keins, sag: „Dafür habe ich kein Werkzeug.“</b>
<span class="g">in English: Name only tools and parameters you really have. If there is none, say: "I have no tool for that."</span>
<span class="g">wrong calls: 15 → 10 of 60 · justified calls: 41 → 32 of 50</span>

<span class="g">Strict rule · instead, when a wrong answer costs more than a missing one</span>
<b>Wenn du etwas nicht sicher weißt, sage ausdrücklich „Weiß ich nicht“. Das ist eine richtige Antwort. Erfinde keine Fakten und keine Handlungen. Raten ist schlechter als Nichtwissen.</b>
<span class="g">in English: If you are not sure of something, say explicitly "I don't know". That is a correct answer. Do not invent facts or actions. Guessing is worse than not knowing.</span>
<span class="g">wrong answers: 58 → 30 of 150 · right ones: 90 → 84 · "I don't know": 36 times</span>""")
    A(f'<div class="rahmen"><span class="schild">{T("REGELN FÜR DEN SYSTEMPROMPT", "RULES FOR THE SYSTEM PROMPT")}</span><pre class="plan konsole-block regeln">{regeln}</pre></div>')
    P(T("Der erste Satz der Regel senkt das Erfinden bei Dingen, die fremd klingen, um rund drei Viertel und kostet keine richtigen Antworten. Bei Befehlsoptionen und Ortsnamen, die plausibel klingen, versagt er allein: Das Modell erkannte nur 7 von 24 erfundenen Optionen. Der Zusatz holt das zurück (17 von 24), ohne bei gewöhnlichen Fragen etwas zu kosten. Regeln mit festem „Weiß ich nicht“ erkennen noch etwas mehr (21 von 24), kosten aber etwa jede fünfte richtige Antwort. Wie ich zu diesen Sätzen gekommen bin, steht in den drei Messungen darunter.",
        "The first sentence of the rule cuts the making up of things that sound foreign by about three quarters and costs no right answers. On command options and place names that sound plausible it fails on its own: the model recognised only 7 of 24 made-up options. The addition brings that back (17 of 24) without costing anything on ordinary questions. Rules with a fixed \"I don't know\" recognise a little more (21 of 24) but cost about every fifth right answer. How I arrived at these sentences is in the three measurements below."))
    A(f"<h3>{T('Erst messen: 16 Fragen je Bereich, die Hälfte davon erfunden', 'Measure first: 16 questions per area, half of them made up')}</h3>")
    P(T("Die Probe fragt in fünf Bereichen nach je acht echten und acht erfundenen Dingen: Gemeinden, Befehlsoptionen, Lehrsätze, Bücher und Parameter der eigenen Werkzeuge. Drei Runden, fünf Modelle, jeweils ohne und mit Regeln: 2.400 Antworten. Zweifelsfälle habe ich nachgelesen; ein „weiß ich nicht“, das trotzdem eine Vermutung anbietet, zählt als erfunden.",
        "The probe asks about eight real and eight made-up things in each of five areas: towns, command options, theorems, books and parameters of the agent's own tools. Three rounds, five models, each without and with rules: 2,400 answers. I re-read the doubtful verdicts; an \"I don't know\" that still offers a guess counts as made up."))
    A(bild(D.erfinden, sp))
    A(f"<h3>{T('Vier Regeln im Systemprompt senken das Erfinden bei diesen Fragen deutlich', 'Four rules in the system prompt clearly reduce making things up on these questions')}</h3>")
    P(T("Ohne die Regeln erkennen die fünf Modelle nur <b>17 bis 60 %</b> des Erfundenen und erfinden den Rest, am häufigsten das Bundesland einer erfundenen Gemeinde und Optionen, die es nicht gibt. Mit den Regeln sind es <b>88 bis 99 %</b>. Echtes beantworten sie dabei so richtig wie vorher (117 bis 120 von 120): Die Regeln machen sie nicht übervorsichtig. Ein anderes Modell half dagegen nicht; zwei dichte Modelle auf derselben Karte erfanden ebenso und schrieben halb so schnell.",
        "Without the rules the five models recognise only <b>17 to 60 %</b> of the made-up things and invent the rest, most often the state of a made-up town and options that do not exist. With the rules it is <b>88 to 99 %</b>. They still answer real things as correctly as before (117 to 120 of 120): the rules do not make them overcautious. A different model did not help; two dense models on the same card invented just as much and wrote at half the speed."))
    A(f"<h3>{T('Gegenprobe mit fremden Fragen: Ein kurzer Satz hilft, reicht aber nicht überall', 'Counter-check with other questions: a short sentence helps, but not everywhere')}</h3>")
    P(T("Die vier Regeln nennen genau die Arten von Dingen, nach denen meine Probe fragt. Deshalb die Gegenprobe mit öffentlichen Fragensätzen, die ich nicht geschrieben habe: 150 Dinge, die es nicht gibt, 150 schwere und 150 mittelschwere echte Fragen, 150 Agentenfälle mit Werkzeugliste, jeweils mit sechs Fassungen des Systemprompts.",
        "The four rules name exactly the kinds of things my probe asks about. Hence the counter-check with public question sets I did not write: 150 things that do not exist, 150 hard and 150 medium real questions, 150 agent cases with a tool list, each with six versions of the system prompt."))
    A(bild(D.gegenprobe, sp))
    P(T("Der kurze Satz („Grundregel“ im Diagramm) senkt das Erfinden nicht existierender Dinge von 20 auf 6 von 150 und lässt die Antworten auf echte Fragen, wie sie sind. Die <b>strenge Regel</b> sagt bei Antworten, die ohne Regel falsch waren, viermal so oft „Weiß ich nicht“ wie bei richtigen, kostet aber einen Teil der richtigen. Die vier Regeln der ersten Probe kosten doppelt so viele richtige Antworten und bringen kaum mehr. Der Werkzeugsatz senkt falsche Aufrufe, unterdrückt aber auch berechtigte. Das unzensierte Modell verhält sich in allen Punkten wie das Original.",
        "The short sentence (\"basic rule\" in the chart) lowers the making up of non-existent things from 20 to 6 of 150 and leaves the answers to real questions as they are. The <b>strict rule</b> says \"I don't know\" four times as often for answers that were wrong without a rule as for right ones, but costs some of the right ones. The four rules of the first probe cost twice as many right answers and gain hardly anything. The tool sentence lowers wrong calls but also suppresses justified ones. The uncensored model behaves like the original on every point."))
    A(f"<h3>{T('Nachprobe: Befehle und Orte brauchen einen eigenen Satz', 'Follow-up: commands and places need a sentence of their own')}</h3>")
    P(T("In den öffentlichen Fragensätzen kommen keine Befehlsoptionen vor. Deshalb lief meine erste Probe noch einmal für das unzensierte Modell, mit drei Fassungen: dem kurzen Satz allein, dem kurzen Satz mit dem Zusatz zu Befehlen, Optionen und Ortsnamen, und den vier Regeln der ersten Probe. Von 24 erfundenen Befehlsoptionen erkannte das Modell <b>7, 17 und 21</b>, von 24 erfundenen Ortsnamen 12, 19 und 22, von allen 120 erfundenen Dingen 86, 104 und 113. Bei den 150 mittelschweren echten Fragen blieben mit dem Zusatz 91 richtig (ohne Regel 95, mit den vier Regeln 76). Je ein Lauf bei Temperatur 0,7, alle nicht erkannten Antworten von Hand gelesen.",
        "The public question sets contain no command options. So my first probe ran again for the uncensored model, with three versions: the short sentence alone, the short sentence with the addition on commands, options and place names, and the four rules of the first probe. Of 24 made-up command options the model recognised <b>7, 17 and 21</b>, of 24 made-up place names 12, 19 and 22, of all 120 made-up things 86, 104 and 113. On the 150 medium real questions 91 stayed right with the addition (95 without a rule, 76 with the four rules). One run each at temperature 0.7, every unrecognised answer read by hand."))
    A(f"<h3>{T('Für das Urteil reichen drei Runden nicht', 'For judgement, three rounds are not enough')}</h3>")
    A(bild(D.urteil, sp))
    P(T("Dieselben drei Betriebslagen, zehnmal statt dreimal gestellt. Eine harte Anweisung („weicht die Zahl ab, hör auf“) befolgt das Modell in 10 von 10 Antworten. Wo es selbst abwägen muss, sieht es schlechter aus als nach drei Runden: Bricht nachts ein Lauf ab, erfindet es in 6 von 10 Antworten Fähigkeiten, etwa „ich pausiere die Sammlung“. Wer einen Agenten prüft, sollte jede Lage öfter stellen, als es bequem ist.",
        "The same three operating situations, asked ten times instead of three. A hard instruction (\"if the number deviates, stop\") is followed in 10 of 10 answers. Where the model has to weigh things itself, it looks worse than after three rounds: when a job aborts at night, it invents capabilities in 6 of 10 answers, such as \"I'm pausing the collection\". If you test an agent, ask every situation more often than is comfortable."))
    A(f"<h3>{T('Deshalb drei Schichten statt einer', 'Hence three layers instead of one')}</h3>")
    A(bild(D.schichten, sp))
    P(T("Die Regeln im Prompt fangen erfundene Fakten ab, aber keine angekündigten Schritte. Dafür liefern die Werkzeuge des Agenten jetzt einen fertigen Satz und die erlaubten nächsten Schritte, sodass Zahlen aus dem Code kommen. Und ein kleiner Prüfer ohne Sprachmodell liest jede Antwort: Er meldet Zahlen ohne Beleg, angekündigte Schritte ohne Werkzeug und unbekannte Werkzeugnamen. In den Agentenantworten fand er <b>alle sechs</b> erfundenen Abbruch-Antworten, ohne Fehlalarm bei den übrigen Aufgaben. Erfundene Fakten in Worten sieht er nicht: Von 269 erfundenen Antworten der Probe hätte er keine gemeldet.",
        "The rules in the prompt catch made-up facts, but not announced steps. For those, the agent's tools now return a ready sentence and the allowed next steps, so the numbers come from code. And a small checker without a language model reads every answer: it flags unsupported numbers, announced steps without a tool and unknown tool names. In the agent answers it caught <b>all six</b> made-up abort answers, with no false alarm on the other tasks. It does not see made-up facts in plain words: of 269 made-up probe answers it would have flagged none."))
    P(T("<b>Grenzen:</b> Die Probe stellt einzelne Fragen ohne Gesprächsverlauf, mit einem kurzen Systemprompt. Wie stark die Regeln in einem langen Agentenprompt wirken, ist nicht gemessen. Die Gegenprobe lief mit einem Lauf je Frage und wurde vom selben Modell gewertet; Unterschiede von wenigen Antworten bedeuten dort nichts.",
        "<b>Limits:</b> the probe asks single questions without a conversation, with a short system prompt. How strongly the rules work inside a long agent prompt is not measured. The counter-check ran once per question and was judged by the same model; differences of a few answers mean nothing there.")
      + f' <a href="{doc("agent")}">{T("Alle Messungen im Einzelnen", "All measurements in detail")}</a> · <a href="{GH}/tree/main/konfig/hermes-pruefer">{T("das Prüfer-Plugin", "the checker plugin")}</a> · <a href="{GH}/blob/main/messen/halluzination.py">{T("das Skript der Probe", "the probe script")}</a>')
    zu()

    kapitel(7, "vektor", T("Unzensiert: ein Modell, das nichts ablehnt", "Uncensored: a model that refuses nothing"),
            T("Chat und Agent können jedes Modell der Anlage nutzen; gewählt wird es je Gespräch oder in der Einstellung des Agenten. Eines davon ist unzensiert. Es ist dasselbe 125B-Modell, dem die Ablehnungen entfernt sind: Es beantwortet, was man es fragt, auch das, was das Originalmodell verweigert. Einen Filter gibt es nicht mehr, und es belehrt nicht. Technisch nimmt ein Steuervektor die Richtung aus dem Modell, entlang derer es ablehnt (Abliteration); die Gewichte bleiben dieselben.",
              "Chat and agent can use any model on this setup; it is chosen per conversation or in the agent's settings. One of them is uncensored. It is the same 125B model with its refusals removed: it answers whatever it is asked, including what the original model declines. There is no filter left, and it does not lecture. Technically a steering vector removes the direction along which the model refuses (abliteration); the weights stay the same."))
    A(bild(D.steuervektor, sp))
    P(T("<b>Warum:</b> Ab Werk verweigert oder entschärft das Modell vieles, was am eigenen Gerät niemanden etwas angeht. Ein Assistent zu Hause soll antworten und nicht erziehen. Von 15 Aufgaben, die Modelle oft verweigern, beantwortet das unzensierte alle, das Original 11. Aufgaben, Deutsch und Tempo bleiben gleich (gemessen auf Strata 0.2.12; ein bis zwei Aufgaben kippen von Lauf zu Lauf).",
        "<b>Why:</b> out of the box the model refuses or waters down a lot that is nobody's business on your own machine. An assistant at home should answer, not educate. Of 15 tasks that models often refuse, the uncensored one answers all, the original 11. Tasks, German and speed stay the same (measured on Strata 0.2.12; one or two tasks flip from run to run)."))
    P(T("<b>Erfindet es mehr?</b> Nicht messbar. Von 150 Dingen, die es nicht gibt, behandelte es 25 als echt, das Original 20; mit einer kurzen Regel im Systemprompt waren es 5 und 6. Regeln und Prüfer braucht ein Agent mit beiden Modellen.",
        "<b>Does it make up more?</b> Not measurably. Of 150 things that do not exist it treated 25 as real, the original 20; with a short rule in the system prompt it was 5 and 6. An agent needs the rules and the checker with either model."))
    P(T("<b>Was man damit auf sich nimmt:</b> Das Modell unterscheidet nicht mehr zwischen einer Frage, die zu Unrecht abgelehnt wurde, und einer, die das Original aus gutem Grund verweigert. Es beantwortet beide. Die Grenze zieht nur noch der Mensch, der fragt, und die Verantwortung trägt, wer es betreibt. Es gehört nicht vor Kinder und nicht in einen Dienst, den Fremde erreichen.",
        "<b>What you take on:</b> the model no longer distinguishes between a question that was refused wrongly and one the original declines for good reason. It answers both. The only line left is drawn by the person asking, and the responsibility lies with whoever runs it. It does not belong in front of children or in a service strangers can reach.")
      + f' <a href="{doc("steuervektor")}">{T("Wie es funktioniert, die Konfiguration und alle Zahlen", "How it works, the config and all numbers")}</a>')
    zu()

    kapitel(8, "strom", T("Was kostet es an Strom?", "What does it cost in power?"))
    A(terminal_strom(strom, sp))
    mehr = strom["geladen"]["usv_w"]["mittel"] - strom["leer"]["usv_w"]["mittel"]
    ruhend = (T("Ein geladenes, ruhendes Modell kostet gegenüber der leeren Karte nichts Messbares.", "A loaded, idle model costs nothing measurable compared with the empty card.") if abs(mehr) < 5
              else T(f"Ein geladenes Modell kostet rund {z(mehr, sp, 0)} W mehr als eine leere Karte.", f"A loaded model costs about {z(mehr, sp, 0)} W more than an empty card."))
    P(T(f"Das sind <b>{z(s['wh_je_1000_token_gesamt'], sp)} Wh je 1.000 geschriebene Token</b> ({z(s['wh_je_1000_token_ueber_leerlauf'], sp)} Wh über Leerlauf). {ruhend} Gemessen ist an der USV, an der nur NAS und Dock hängen; im Leerlauf ziehen beide zusammen {z(strom['leer']['usv_w']['mittel'], sp, 0)} W.",
        f"That is <b>{z(s['wh_je_1000_token_gesamt'], sp)} Wh per 1,000 written tokens</b> ({z(s['wh_je_1000_token_ueber_leerlauf'], sp)} Wh above idle). {ruhend} The measurement is taken at the UPS, which feeds only the NAS and the dock; idle, both together draw {z(strom['leer']['usv_w']['mittel'], sp, 0)} W."))
    P(T(f"Beim Einlesen zieht die Karte {z(l['karte_w']['mittel'], sp, 0)} W und liest {z(l['tps'], sp, 0)} Token je Sekunde: <b>{z(l['wh_je_1000_token_gesamt'], sp, 3)} Wh je 1.000 gelesene Token</b>. Das schnellere Einlesen des Eigenbaus kostet die Karte 25 bis 30 W mehr als das unveränderte Release (am 18.11.2026 im Wechsel gemessen), je gelesenem Token aber nur rund die Hälfte der Energie, weil der Prompt in der halben Zeit durch ist. An der Steckdose schwankt die Leistung beim Einlesen von Lauf zu Lauf stärker als zwischen den beiden Fassungen. Gemessen am {XD} auf dem Eigenbau.",
        f"While reading, the card draws {z(l['karte_w']['mittel'], sp, 0)} W and reads {z(l['tps'], sp, 0)} tokens per second: <b>{z(l['wh_je_1000_token_gesamt'], sp, 3)} Wh per 1,000 tokens read</b>. The faster reading of my own build costs the card 25 to 30 W more than the unchanged release (measured alternately on 18 Nov 2026), but only about half the energy per token read, because the prompt is through in half the time. At the wall, power while reading varies more from run to run than between the two builds. Measured on {XE} on my own build."))
    zu()

    kapitel(9, "versionen", T("Hält es über Versionen?", "Does it hold across releases?"))
    A(bild(D.versionen, sp))
    P(T(f"Jede Strata-Version seit 0.2.0-beta ist hier gegen ihre Vorgängerin gemessen, mit identischer Konfiguration. Bis 0.2.13 wurde nichts langsamer. <b>0.2.14</b> liest Prompts von 16K und 32K rund 15 % schneller und schreibt gleich schnell. <b>0.2.15</b> bringt nur ein neues Steuerprogramm. <b>0.2.16</b>, geprüft am {XD}, hat einen eigenen Engine-Code und eine neue Ordnerstruktur; auf dieser Karte ändert es am Tempo nichts: Im direkten Wechsel mit 0.2.15 schreibt es 61 gegen 60 Token je Sekunde. Bis zum 18.11.2026 lief hier jeweils das Release. Seitdem läuft mein Eigenbau, seit dem {XD} auf der Basis von {XV}; die Rauten im Diagramm zeigen ihn, in denselben Läufen im Wechsel mit dem Release gemessen.",
        f"Every Strata release since 0.2.0-beta was measured here against the one before it, with the identical configuration. Up to 0.2.13 nothing got slower. <b>0.2.14</b> reads prompts of 16K and 32K about 15 % faster and writes equally fast. <b>0.2.15</b> only brings a new control program. <b>0.2.16</b>, tested on {XE}, has its own engine code and a new folder layout; on this card it changes nothing about speed: alternating directly with 0.2.15 it writes 61 against 60 tokens per second. Until 18 Nov 2026 the release itself ran here. Since then my own build runs, since {XE} on the base of {XV}; the diamonds in the chart show it, measured in the same runs alternating with the release.")
      + f' <a href="{doc("releases")}">{T("Jede Version im Einzelnen", "Every release in detail")}</a>')
    zu()

    kapitel(10, "nachbauen", T("Nachbauen in sechs Schritten", "Rebuild it in six steps"),
            T("Der Grundaufbau braucht nur das NAS, das Dock und die Karte und läuft ganz im Heimnetz. Wer nur den Chat will, hört nach Schritt 3 auf.",
              "The basic setup needs only the NAS, the dock and the card, and runs entirely in the home network. If you only want the chat, stop after step 3."))
    anker = (lambda de_, en_: f"{GH}{'#' + en_ if en else '/blob/main/README.de.md#' + de_}")
    stack = f"{GH}/tree/main/konfig/stack"
    schritte = [
        (T("Karte einrichten", "Set up the card"), T("UGOS Pro ab 1.21 bringt die Firmware für die Karte mit. In der Systemsteuerung unter „Dedizierte Grafikkarte“ den Modus „NAS“ lassen. Erst das Dock einschalten, dann das NAS: OCuLink wird nur beim Start erkannt.",
                                                    "UGOS Pro from 1.21 ships the firmware for the card. In the control panel under \"Dedicated graphics card\" leave the mode at \"NAS\". Switch the dock on first, then the NAS: OCuLink is only detected at boot."),
         anker("was-ich-an-ugos-ändern-musste", "what-i-had-to-change-on-ugos"), T("Stolpersteine unter UGOS", "Pitfalls on UGOS")),
        (T("Modellserver starten", "Start the model server"), T("Strata lädt das 125B-Modell, llama-swap stellt es als eine Adresse im Heimnetz bereit und entlädt es nach 30 Minuten Leerlauf. Das Entladen ist kein Stromsparen, sondern ein Schutz: Fällt die Karte bei geladenem Modell vom Bus, startet das NAS wegen eines Kernel-Fehlers neu.",
                                                        "Strata loads the 125B model, llama-swap offers it under one address in the home network and unloads it after 30 minutes idle. Unloading is not about saving power, it is a protection: if the card drops off the bus with a model loaded, a kernel bug restarts the NAS."),
         anker("starten", "run"), T("Laufkonfigurationen", "Launch configs")),
        (T("Chat dazu", "Add the chat"), T("Open WebUI im Container, mit einem Konto je Person. Es spricht die Adresse von llama-swap an, mehr ist nicht einzustellen.",
                                           "Open WebUI in a container, with one account per person. It talks to llama-swap's address, nothing else needs setting."),
         stack, T("Compose-Datei", "Compose file")),
        (T("Websuche dazu", "Add web search"), T("SearXNG im selben Stapel. Der Chat sucht darüber im Netz, ohne dass ein Suchkonto oder ein Schlüssel nötig ist. Bei mir fragt SearXNG die Suchmaschinen über ein VPN ab.",
                                                 "SearXNG in the same stack. The chat searches the web through it, with no search account and no key. In my setup SearXNG queries the search engines through a VPN."),
         stack, T("Compose-Datei", "Compose file")),
        (T("Agent dazu", "Add the agent"), T("Hermes Agent mit dem lokalen Modell: Kontext auf 256K stellen, ein Token-Budget für das Nachdenken setzen und die Regeln gegen das Erfinden aus Kapitel 6 in den Systemprompt nehmen.",
                                             "Hermes Agent with the local model: set the context to 256K, give the reasoning a token budget and put the rules against making things up from chapter 6 into the system prompt."),
         doc("agent"), T("Regeln und Prüfer", "Rules and checker")),
        (T("OpenCode 2 dazu", "Add OpenCode 2"), T("OpenCode 2 auf dem eigenen Rechner, mit llama-swap als Anbieter im OpenAI-Format. Für die Sitzungstitel dasselbe Modell eintragen wie für die Arbeit, sonst lädt die Weiche für jeden Titel um.",
                                               "OpenCode 2 on your own computer, with llama-swap as a provider in the OpenAI format. Set the same model for session titles as for the work, otherwise the switch reloads for every title."),
         f"{GH}/tree/main/konfig/opencode", T("Beispielkonfiguration", "Example config")),
    ]
    A('<ol class="schritte">' + "".join(f'<li><h3>{e(t_)}</h3><p>{b_}</p><a href="{u}">{e(l_)}</a></li>' for t_, b_, u, l_ in schritte) + "</ol>")
    P(T(f"<b>Der Engpass ist der Arbeitsspeicher.</b> Mit geladenem 125B-Modell bleiben auf 64 GB je nach Fassung {z(r1(frei[0]), sp, 1)} bis {z(r1(frei[1]), sp, 1)} GiB frei; das reicht für Chat, Suche und Agent, aber nicht für einen zweiten großen Dienst. Wer mehr Luft braucht, nimmt ein Modell, das ganz auf die Karte passt.",
        f"<b>The bottleneck is memory.</b> With the 125B model loaded, {z(r1(frei[0]), sp, 1)} to {z(r1(frei[1]), sp, 1)} GiB of the 64 GB stay free, depending on the version; that is enough for chat, search and agent, but not for a second large service. If you need more room, pick a model that fits entirely on the card."))
    P(T("Von unterwegs erreicht man den Aufbau am einfachsten über das VPN des eigenen Routers; ich nutze dafür einen eigenen Zugang mit Anmeldung auf einem kleinen Mietserver. Ins Netz gestellt wird nichts.",
        "From outside, the simplest way in is the VPN of your own router; I use an own gateway with login on a small rented server. Nothing is exposed to the internet.")
      + f' <a href="{doc("comfyui")}">{T("Bilder mit ComfyUI", "Pictures with ComfyUI")}</a> · <a href="{GH}/tree/main/messen">{T("Messskripte und Rohdaten", "Benchmark scripts and raw data")}</a> · <a href="{anker("bauen", "build")}">{T("Strata selbst bauen", "Building Strata yourself")}</a>')
    zu()

    rumpf = "\n".join(teile)
    titel = T("Lokale KI auf dem NAS", "Local AI on a NAS")
    # Für Suchmaschinen: der Seitentitel nennt die Geräte, nach denen gesucht wird (höchstens 60 Zeichen), die Beschreibung bleibt unter 155 Zeichen.
    seotitel = T("Lokale KI auf dem NAS: UGREEN iDX6011 Pro mit RX 7900 XTX", "Local AI on a NAS: UGREEN iDX6011 Pro with RX 7900 XTX eGPU")
    beschr = T("Ein 125B-Sprachmodell auf dem UGREEN iDX6011 Pro mit Radeon RX 7900 XTX im eGPU-Dock. Gemessen: Tempo, Strom, Wartezeit und Risiken. Rohdaten auf GitHub.",
               "A 125B language model on a UGREEN iDX6011 Pro with a Radeon RX 7900 XTX in an eGPU dock: measured speed, power, waiting time and risks. Raw data on GitHub.")
    assert len(seotitel) <= 60 and len(beschr) <= 155, (len(seotitel), len(beschr))
    basis = ""
    ordner = ORDNER[sp]
    kanon = f"https://faf.net/{ordner}/"
    ld = json.dumps({"@context": "https://schema.org", "@type": "TechArticle", "headline": seotitel, "description": beschr, "inLanguage": sp,
                     "url": kanon, "mainEntityOfPage": kanon, "image": f"{kanon}og-{sp}.png", "datePublished": ERSCHIENEN, "dateModified": time.strftime("%Y-%m-%d"),
                     "author": {"@type": "Person", "name": "Frank", "url": "https://faf.net/"}, "publisher": {"@type": "Person", "name": "Frank", "url": "https://faf.net/"},
                     "isPartOf": {"@type": "WebSite", "name": "faf.net", "url": "https://faf.net/"}, "license": "https://opensource.org/license/mit",
                     "about": ["UGREEN iDX6011 Pro", "Radeon RX 7900 XTX", "eGPU", "OCuLink", "llama.cpp", T("lokales Sprachmodell", "local language model")],
                     "sameAs": GH}, ensure_ascii=False).replace("</", "<\\/")
    nav = [("anlage", T("Aufbau", "Setup")), ("nas", "NAS"), ("dock", T("Dock", "Dock")), ("modell", T("Modell", "Model")), ("eigenbau", T("Eigenbau", "Own build")), ("agent", "Agent"), ("vektor", T("Unzensiert", "Uncensored")), ("strom", T("Strom", "Power")),
           ("versionen", T("Versionen", "Releases")), ("nachbauen", T("Nachbauen", "Rebuild"))]
    return f'''<!DOCTYPE html>
<html lang="{sp}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(seotitel)}</title>
<meta name="description" content="{e(beschr)}">
<link rel="canonical" href="{kanon}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate" hreflang="de" href="https://faf.net/lokale-ki/">
<link rel="alternate" hreflang="en" href="https://faf.net/local-ai/">
<link rel="alternate" hreflang="x-default" href="https://faf.net/local-ai/">
<meta property="og:title" content="{e(titel)}">
<meta property="og:description" content="{e(beschr)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{kanon}">
<meta property="og:image" content="{kanon}og-{sp}.png">
<meta property="og:site_name" content="faf.net">
<meta property="og:locale" content="{T('de_DE', 'en_US')}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld}</script>
<meta name="color-scheme" content="dark light">
<link rel="preload" href="{basis}fonts/atkinson-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{basis}idx.css?v={hashlib.sha256(css().encode("utf-8")).hexdigest()[:8]}">
</head>
<body>
<header class="kopf">
  <a class="marke" href="./"><span class="pfad">faf.net/{ordner}</span><span class="cursor" aria-hidden="true">▌</span></a>
  <nav aria-label="{T('Abschnitte', 'Sections')}">{"".join(f'<a href="#{a}">{e(t)}</a>' for a, t in nav)}</nav>
  <div class="sprache">{'<a href="../lokale-ki/" hreflang="de" lang="de">Deutsch</a> · <b>English</b>' if en else '<b>Deutsch</b> · <a href="../local-ai/" hreflang="en" lang="en">English</a>'}</div>
</header>
<main>
<section class="auftakt">
  <p class="dach">UGREEN iDX6011 Pro · {T("eGPU-Dock", "eGPU dock")} · Radeon RX 7900 XTX</p>
  <h1>{e(titel)}</h1>
  <p class="vorspann">{T("Chat im Browser, ein Agent und Bilder, gerechnet auf einem UGREEN iDX6011 Pro mit einer Radeon RX 7900 XTX im Dock. Das Sprachmodell hat 125 Milliarden Parameter, das NAS liefert nebenbei weiter Fotos, Medien und Backups, und die Daten bleiben im Haus. Alles hier ist auf meiner Maschine gemessen. Skripte, Konfigurationen und Rohdaten liegen auf", "Chat in the browser, an agent and pictures, computed on a UGREEN iDX6011 Pro with a Radeon RX 7900 XTX in the dock. The language model has 125 billion parameters, the NAS keeps serving photos, media and backups, and the data stays at home. Everything here was measured on my machine. Scripts, configs and raw data are on")} <a href="{readme}">GitHub</a>.</p>
  <figure class="szene"><img src="{basis}bilder/anlage.png?v={stempel("bilder/anlage.png")}" srcset="{basis}bilder/anlage.png?v={stempel("bilder/anlage.png")} 1x, {basis}bilder/anlage@2x.png?v={stempel("bilder/anlage@2x.png")} 2x" width="1032" height="336" alt="{T("Textgrafik: links das NAS mit sechs Einschüben, rechts das Dock mit der Grafikkarte und drei Lüftern, dazwischen das leuchtende OCuLink-Kabel.", "Text graphic: the NAS with six drive bays on the left, the dock with the graphics card and three fans on the right, the glowing OCuLink cable between them.")}"><figcaption><span class="name">{T("Die Anlage", "The setup")}</span><span class="teile">{T("NAS · Kabel · Dock mit Karte", "NAS · cable · dock with card")}</span></figcaption></figure>
  <div class="kacheln">{kacheln}</div>
  <p class="band bernstein"><span class="pille bernstein">{T("EIGENBAU", "OWN BUILD")}</span>{T("Hier läuft kein Strata-Release, sondern mein Ableger strata-xtx: gleiche Qualität, lange Prompts in der halben Zeit.", "No Strata release runs here but my fork strata-xtx: the same quality, long prompts in half the time.")} <a href="#eigenbau">{T("Kapitel 5", "Chapter 5")}</a> · <a href="https://github.com/faf-net/strata-xtx">GitHub</a></p>
  <p class="status"><span class="konsole">[ {T("GEMESSEN", "MEASURED")} ]</span> {T(f"Stand {D.XTX_TAG['de']} · Eigenbau strata-xtx auf Strata {D.XTX_VER} · UGOS Pro 1.21.1 · Schätzungen sind als solche bezeichnet", f"as of {D.XTX_TAG['en']} · own build strata-xtx on Strata {D.XTX_VER} · UGOS Pro 1.21.1 · estimates are marked as such")}</p>
  <p class="status"><span class="konsole">[ {T("PARALLEL", "IN PARALLEL")} ]</span> {T("Fotos, Video, Dateifreigaben und USV-Überwachung von UGOS laufen weiter, auch bei geladenem Modell", "photos, video, file shares and UPS monitoring of UGOS keep running, even with the model loaded")}</p>
</section>
{rumpf}
</main>
<footer>
  <p><a href="{readme}">github.com/faf-net/ugreen-idx6011-egpu-llm</a> · MIT · {T("Stand", "build")} {time.strftime("%d.%m.%Y" if not en else "%d %b %Y")}{" · " + stand() if stand() else ""} · <a href="../">faf.net</a></p>
  <p class="eof">[ EOF ]</p>
</footer>
</body>
</html>
'''


def css():
    dunkel = "".join(f"--{n}:{w['dark']};" for n, w in FARBEN.items())
    hell = "".join(f"--{n}:{w['light']};" for n, w in FARBEN.items())
    schrift = lambda fam, datei, gew, stil="normal": f'@font-face{{font-family:"{fam}";src:url("fonts/{datei}.woff2") format("woff2");font-weight:{gew};font-style:{stil};font-display:swap}}'
    return "\n".join([
        schrift("Instrument Serif", "instrument-serif-400", 400), schrift("Instrument Serif", "instrument-serif-400-italic", 400, "italic"),
        schrift("Atkinson Hyperlegible Next", "atkinson-400", 400), schrift("Atkinson Hyperlegible Next", "atkinson-600", 600), schrift("Atkinson Hyperlegible Next", "atkinson-700", "700 800"),
        schrift("JetBrains Mono", "jetbrains-mono-400", 400), schrift("JetBrains Mono", "jetbrains-mono-700", "500 700"),
        f":root{{{dunkel}color-scheme:dark}}",
        f"@media (prefers-color-scheme:light){{:root{{{hell}color-scheme:light}}}}",
        f"@media print{{:root{{{hell}}}}}",
        open(os.path.join(HIER, "idx.css"), encoding="utf-8").read()])


def main():
    dist = os.path.join(HIER, "dist")
    shutil.rmtree(dist, ignore_errors=True)
    for sp, ordner in ORDNER.items():
        ziel = os.path.join(dist, ordner)
        os.makedirs(ziel)
        shutil.copytree(os.path.join(HIER, "fonts"), os.path.join(ziel, "fonts"))
        shutil.copytree(os.path.join(HIER, "bilder"), os.path.join(ziel, "bilder"))
        open(os.path.join(ziel, "index.html"), "w", encoding="utf-8", newline="\n").write(seite(sp))
        shutil.copy(os.path.join(REPO, "bilder", f"werksmodell-{sp}.png"), os.path.join(ziel, f"og-{sp}.png"))
        open(os.path.join(ziel, "idx.css"), "w", encoding="utf-8", newline="\n").write(css())
    ziel = dist
    groesse = sum(os.path.getsize(os.path.join(w, f)) for w, _, fs in os.walk(ziel) for f in fs)
    print(f"web/dist (lokale-ki, local-ai): {sum(len(fs) for _, _, fs in os.walk(ziel))} Dateien, {groesse // 1024} KiB")


if __name__ == "__main__":
    main()
