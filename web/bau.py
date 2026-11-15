#!/usr/bin/env python3
"""Baut die Webseite faf.net/lokale-ki (Deutsch) und faf.net/local-ai (Englisch) aus diesem Repo: eine Seite je Sprache, statisch, ohne JavaScript, ohne Fremdserver.

Die Diagramme kommen aus messen/diagramme.py (dieselben Funktionen wie für die PNG im README), eingebettet als SVG
und über CSS-Variablen an das helle oder dunkle Thema gebunden. Kennzahlen und Tabellen der Messung vom 15.11.2026
kommen aus messen/daten/, der Verdrahtungsplan aus dem README. Der Fließtext steht hier im Skript.

  python web/bau.py            schreibt web/dist/lokale-ki/ (Deutsch) und web/dist/local-ai/ (Englisch), je mit index.html, idx.css, fonts/, bilder/

Farben: web/workbench-farben.json (aus dem Design System Workbench). Schriften: web/fonts/ (OFL, selbst ausgeliefert).
"""
import html, json, os, re, shutil, statistics, subprocess, sys, time

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
DATEN = os.path.join(REPO, "messen", "daten")
sys.path.insert(0, os.path.join(REPO, "messen"))
import diagramme as D  # noqa: E402

GH = "https://github.com/faf-net/ugreen-idx6011-egpu-llm"
ORDNER = {"de": "lokale-ki", "en": "local-ai"}
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
        tempo = f'{z(tps, sp, 0 if tps >= 100 else 1)} {"tokens/s" if en else "Token/s"}' if tps else ""
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
    strom = L("2026-11-15-betrieb", "strom-faber.json")["phasen"]
    kalt = [k["erste_antwort_s"] for k in L("2026-11-15-betrieb", "kaltstart-faber.json")["laeufe"]]
    werk = {s["stufe"]: s for s in L("2026-11-15-betrieb", "werksmodell.json")["stufen"]}
    neben = L("2026-11-15-betrieb", "nebenlast.json")
    dock = L("dock-2026-11-15", "vorfaelle.json")
    gpu = max(L("2026-11-15-betrieb", "dicht70-gpu.json")["stufen"], key=lambda s: s["schreiben_tps_median"])
    ab = D.ohne_switch(DATEN, list(strom.values()) + list(werk.values()) + [gpu])   # Switch an derselben USV abziehen
    for ph_ in ("schreiben", "lesen"):
        strom[ph_]["wh_je_1000_token_ueber_leerlauf"] = round((strom[ph_]["usv_w"]["mittel"] - strom["leer"]["usv_w"]["mittel"]) / strom[ph_]["tps"] / 3.6, 3)
    pfad = lambda n: os.path.join(DATEN, "2026-11-15-betrieb", n)
    zwei = L("2026-11-15-betrieb", "zwei.json")["phasen"] if os.path.exists(pfad("zwei.json")) else None
    qual = L("2026-11-15-betrieb", "qualitaet.json") if os.path.exists(pfad("qualitaet.json")) else None
    warte = L("2026-11-15-betrieb", "wartezeit.json")["faelle"] if os.path.exists(pfad("wartezeit.json")) else None
    s, l = strom["schreiben"], strom["lesen"]
    faktor = round(werk["xtx-vulkan"]["schreiben_tps_median"] / werk["ugreen-werk"]["schreiben_tps_median"])
    readme = GH + ("#readme" if en else "/blob/main/README.de.md")
    doc = lambda name: f"{GH}/blob/main/docs/{name}{'' if en else '.de'}.md"

    zahlen = [
        (z(s["tps"], sp, 0), T("Token je Sekunde", "tokens per second"), T("Schreiben, 125B-Modell", "writing, 125B model"), True),
        ("256K", T("Token Kontext", "tokens of context"), T("Nadel bis 250K in 9 von 9 Fällen gefunden", "needle found 9 of 9 times up to 250K"), False),
        (z(s["wh_je_1000_token_gesamt"], sp), T("Wh je 1.000 Token", "Wh per 1,000 tokens"), T("NAS und Dock zusammen", "NAS and dock together"), False),
        (z(statistics.median(kalt), sp, 0) + " s", T("Kaltstart", "cold start"), T("leere Karte bis erstes Wort", "empty card to first word"), False),
        (f"{faktor}×", T("schneller als ab Werk", "faster than as shipped"), T("UGREENs eigenes Modell auf der Karte", "UGREEN's own model on the card"), False),
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
            T("Auf dem NAS mit der Karte im Dock laufen drei Dinge, für die man sonst einen Dienst aus der Cloud nimmt. Gerechnet wird im Haus.",
              "On the NAS with the card in the dock run three things you would otherwise take from a cloud service. The computing happens at home."))
    A(bild(D.aufbau, sp))
    karten = [
        (T("Chat im Browser", "Chat in the browser"), "Open WebUI",
         T("Wie ein Chat-Dienst aus der Cloud, nur kommen die Antworten von der eigenen Karte: ein Konto je Person, Verlauf, Dateien hochladen, Websuche über ein eigenes SearXNG. Seit dem 15.11.2026 im Test.",
           "Like a chat service from the cloud, except that the answers come from your own card: one account per person, history, file upload, web search through an own SearXNG. In testing since 15 Nov 2026."),
         T(f"erstes Wort nach einer Pause: <b>{z(statistics.median(kalt), sp, 0)} s</b> · danach {z(s['tps'], sp, 0)} Token/s", f"first word after a break: <b>{z(statistics.median(kalt), sp, 0)} s</b> · then {z(s['tps'], sp, 0)} tokens/s")),
        ("Agent", "Hermes Agent",
         T("Ein Agent, den man im Browser oder über den Messenger erreicht, der eigene Werkzeuge bedient und Aufgaben nach Zeitplan erledigt, mit bis zu 256K Token Kontext. Vier Regeln im Systemprompt und ein kleiner Prüfer halten ihn vom Erfinden ab.",
           "An agent you reach in the browser or through a messenger, that uses its own tools and runs tasks on a schedule, with up to 256K tokens of context. Four rules in the system prompt and a small checker keep it from making things up."),
         T("Erfundenes erkannt: 17–60 % → <b>88–99 %</b>", "made-up things recognised: 17–60 % → <b>88–99 %</b>")),
        (T("Bilder", "Pictures"), "ComfyUI",
         T("„Mach ein Bild von …“ im Chat oder im Messenger: Die Weiche entlädt das Sprachmodell und lädt ein Bildmodell auf dieselbe Karte. Beides zugleich passt nicht in 24 GB.",
           "\"Make a picture of …\" in the chat or the messenger: the switch unloads the language model and loads a picture model onto the same card. Both at once do not fit into 24 GB."),
         T("<b>8–66 s</b> je Bild · Wechsel vom Sprachmodell 21–27 s", "<b>8–66 s</b> per picture · swapping from the language model 21–27 s")),
    ]
    A('<div class="anwendungen">' + "".join(f'<div class="anwendung"><span class="dach">{e(a)}</span><h3>{e(b)}</h3><p>{c}</p><div class="mess">{m}</div></div>' for a, b, c, m in karten) + "</div>")
    P(T("Zwei Dinge verlassen dabei das Haus: die Suchanfragen der Websuche und die Nachrichten, die über den Messenger-Dienst zum Agenten laufen (bei Signal Ende-zu-Ende-verschlüsselt). Die Suchanfragen gehen über ein VPN hinaus: Die Suchmaschinen sehen die Adresse des VPN-Anbieters, nicht den eigenen Anschluss. Alles andere, auch jedes hochgeladene Dokument, bleibt auf den eigenen Geräten. Von unterwegs ist die Anlage über einen eigenen Zugang mit Anmeldung erreichbar.",
        "Two things leave the house: the search queries of the web search, and the messages that travel to the agent through the messenger service (end-to-end encrypted with Signal). The search queries go out through a VPN: the search engines see the VPN provider's address, not your own line. Everything else, including every uploaded document, stays on your own machines. From outside, the setup is reachable through an own gateway with login."))
    zu()

    kapitel(2, "nas", T("Das NAS bleibt ein NAS", "The NAS stays a NAS"),
            T("Auch bei geladenem Modell läuft alles weiter, wofür die iDX gekauft wurde: Fotos, Video und Dateifreigaben. Die Karte im Dock nimmt ihnen nichts weg, weil sie eine eigene Grafikeinheit haben.",
              "Even with the model loaded, everything the iDX was bought for keeps running: photos, video and file shares. The card in the dock takes nothing away from them, because they have a graphics unit of their own."))
    A(bild(D.parallel, sp))
    P(T("Die iDX macht weiter, wofür sie gekauft wurde, mit den Diensten, die UGOS mitbringt: <b>Fotos</b> für die Fotosammlung, <b>Video</b> für die Mediathek, <b>Dateifreigaben</b> über SMB und die Überwachung der USV. Auch Docker kommt aus UGOS; darin laufen Chat, Suche und Agent. Die eingebaute Arc-iGPU bleibt für Transkodierung und Bilderkennung frei, die Karte im Dock rechnet nur Sprach- und Bildmodelle.",
        "The iDX keeps doing what it was bought for, with the services UGOS brings along: <b>Photos</b> for the photo library, <b>Video</b> for the media library, <b>file shares</b> over SMB and UPS monitoring. Docker comes from UGOS too; chat, search and agent run in it. The built-in Arc iGPU stays free for transcoding and photo recognition, the card in the dock only runs language and picture models."))
    P(T(f"Während das Modell schrieb, kam eine 17,7-GB-Datei mit {z(neben['download']['waehrend_schreiben']['mb_s'], sp, 0)} MB/s vom NAS ({z(neben['download']['ohne_modell']['mb_s'], sp, 0)} MB/s ohne Modell; begrenzt hat beide Male der 5-Gbit/s-Anschluss des Arbeitsplatzes). Die Transkodierung von 4K nach 1080p auf der Arc-iGPU fiel von {tr['ohne_modell_bilder_s'][0]} auf {min(tr['waehrend_schreiben_bilder_s'])}–{max(tr['waehrend_schreiben_bilder_s'])} Bilder je Sekunde, das Fünf- bis Achtfache der Echtzeit. Das Schreibtempo des Modells blieb unverändert. Nicht gemessen: SMB und ein Arbeitsplatz mit 10 Gbit/s.",
        f"While the model was writing, a 17.7 GB file came off the NAS at {z(neben['download']['waehrend_schreiben']['mb_s'], sp, 0)} MB/s ({z(neben['download']['ohne_modell']['mb_s'], sp, 0)} MB/s without a model; both times the client's 5 Gbit/s port was the limit). Transcoding 4K to 1080p on the Arc iGPU dropped from {tr['ohne_modell_bilder_s'][0]} to {min(tr['waehrend_schreiben_bilder_s'])}–{max(tr['waehrend_schreiben_bilder_s'])} frames per second, five to eight times real time. The model's decode speed did not change. Not measured: SMB, and a 10 Gbit/s client."))
    A(bild(D.speicher, sp))
    P(T("Der Preis ist Arbeitsspeicher: Mit geladenem 125B-Modell bleiben von 62 GiB rund 7,5 GiB verfügbar. Ein zweiter großer Dienst daneben passt nicht.",
        "The price is memory: with the 125B model loaded, about 7.5 GiB of the 62 GiB stay available. A second large service does not fit next to it."))
    zu()

    kapitel(3, "dock", T("Lohnt sich die Karte im Dock?", "Is the card in the dock worth it?"),
            T("UGREEN liefert die iDX mit einer KI-Konsole aus, die ein eigenes Modell auf die eingebaute Arc-iGPU lädt. Dieselbe Datei, drei Wege:",
              "UGREEN ships the iDX with an AI console that loads its own model onto the built-in Arc iGPU. The same file, three paths:"))
    A(bild(D.werksmodell, sp)); A(t_werk)
    P(T(f"Auf der Karte schreibt das eingebaute Modell <b>{faktor}-mal so schnell</b> wie ab Werk und braucht je 1.000 Token {z(werk['xtx-vulkan']['wh_je_1000_token_gesamt'], sp)} statt {z(werk['ugreen-werk']['wh_je_1000_token_gesamt'], sp)} Wh. Die CPU allein schreibt schneller als der iGPU-Server, liest einen Prompt aber gut siebenmal langsamer. „Ab Werk“ ist der Server, den UGOS nach dem Download selbst startet; ich habe ihn über seinen Unix-Socket gemessen. Die zweite Laufzeit der KI-Konsole ist ein CUDA-Build und startet mit einer AMD-Karte nicht.",
        f"On the card the built-in model writes <b>{faktor} times faster</b> than as shipped and needs {z(werk['xtx-vulkan']['wh_je_1000_token_gesamt'], sp)} instead of {z(werk['ugreen-werk']['wh_je_1000_token_gesamt'], sp)} Wh per 1,000 tokens. The CPU alone out-writes the iGPU server but reads a prompt about seven times more slowly. \"As shipped\" is the server UGOS starts by itself after the download; I measured it through its Unix socket. The AI console's second runtime is a CUDA build and does not start with an AMD card."))
    if qual:
        F, Q = qual["modelle"]["faber"], qual["modelle"]["qwen35"]
        zl = lambda k, name: [name, f"{F['bestanden'][k][0]}/{F['bestanden'][k][1]}", f"{Q['bestanden'][k][0]}/{Q['bestanden'][k][1]}"]
        A(f"<h3>{T('Und die Qualität? Dieselben Aufgaben für beide Modelle', 'And the quality? The same tasks for both models')}</h3>")
        A(tabelle(["", "Flash-Next 125B", T("Qwen3.5-35B (UGREENs Modell)", "Qwen3.5-35B (UGREEN's model)")],
                  [[f"<b>{T('bestandene Aufgaben (von 102)', 'graded tasks passed (of 102)')}</b>", f"<b>{F['bestanden_gesamt']}</b>", f"<b>{Q['bestanden_gesamt']}</b>"],
                   zl("code", "Code"), zl("logik", T("Logik", "logic")), zl("anweisung", T("Anweisungen befolgen", "following instructions")), zl("fakten", T("Fakten", "facts")),
                   [T("Denkbudget aufgebraucht, keine Antwort", "reasoning budget used up, no answer"), 0, Q["denkbudget_erschoepft"]],
                   [T("Deutsch, verdeckt benotet (von 60)", "German, graded blind (of 60)"), F["deutsch_blind_60"], Q["deutsch_blind_60"]],
                   [T("Zeit für alle 114 Aufgaben", "time for all 114 tasks"), f"{z(F['sekunden_114_aufgaben'] / 60, sp, 0)} min", f"{z(Q['sekunden_114_aufgaben'] / 60, sp, 0)} min"]]))
        P(T("Das kleine Modell schreibt fast doppelt so schnell, denkt aber viel länger nach: 2,6-mal so viele Token für dieselben Aufgaben, und in neun Aufgaben war das Denkbudget aufgebraucht, bevor eine Antwort kam. Dafür lässt es den Arbeitsspeicher des NAS frei. Wer vor allem ein NAS will und gelegentlich chattet, ist mit dem kleinen Modell auf der Karte gut bedient; für einen Agenten und lange Texte lohnt das große.",
            "The small model writes almost twice as fast but thinks much longer: 2.6 times as many tokens for the same tasks, and in nine tasks the reasoning budget was used up before an answer came. In return it leaves the RAM of the NAS free. If you mainly want a NAS and chat now and then, the small model on the card serves you well; for an agent and long texts the big one pays off."))
    zu()

    kapitel(4, "modell", T("Ein 125B-Modell auf 24 GB", "A 125B model on 24 GB"),
            T("Qwen3.8-Flash-Next ist ein Mixture-of-Experts-Modell: Je Token rechnen nur wenige Experten. Strata hält die häufig gebrauchten im VRAM und den Rest im schnellen RAM der iDX.",
              "Qwen3.8-Flash-Next is a Mixture-of-Experts model: only a few experts run per token. Strata keeps the frequently used ones in VRAM and the rest in the iDX's fast RAM."))
    A(f'<div class="rahmen"><span class="schild">{T("VERDRAHTUNG", "WIRING")}</span><pre class="plan">{verdrahtung(sp)}</pre></div>')
    A(bild(D.tiefe, sp))
    P(T("Das Schreibtempo fällt von 1K bis 248K Token Kontext nur von 62 auf 56 Token je Sekunde. Ab 16K liest das Modell über 1.000 Token je Sekunde, über eine PCIe-Anbindung mit nur vier Lanes.",
        "Decode speed drops only from 62 to 56 tokens per second between 1K and 248K tokens of context. From 16K on the model reads more than 1,000 tokens per second, over a PCIe link with only four lanes."))
    A(bild(D.betrieb, sp))
    P(T(f"Zum Vergleich ein dichtes 70B-Modell (Llama 3.3, Q4) auf derselben Karte: <b>{z(gpu['schreiben_tps_median'], sp, 1)} Token je Sekunde</b>, weil für jedes Token alle Gewichte gelesen werden und die Hälfte davon hinter der CPU liegt.",
        f"For comparison, a dense 70B model (Llama 3.3, Q4) on the same card: <b>{z(gpu['schreiben_tps_median'], sp, 1)} tokens per second</b>, because every token reads all weights and half of them sit behind the CPU."))
    A(f"<h3>{T('Sechs Modelle auf derselben Karte', 'Six models on the same card')}</h3>")
    A(bild(D.dicht_moe, sp))
    P(T("Auf der Karte laufen auch kleinere Modelle, die ganz in den Grafikspeicher passen. Zwei dichte Modelle schreiben halb so schnell wie das 125B-Modell und bestehen nicht mehr Aufgaben. UGREENs mitgeliefertes Qwen 3.5 schreibt am schnellsten, hat aber das schwächste Deutsch und besteht die wenigsten Aufgaben. Schnell und gut im Deutschen zugleich sind nur die Fassungen des 125B-Modells; die unzensierte liegt im Deutschen vorn.",
        "Smaller models that fit entirely into video memory run on the card as well. Two dense models write at half the speed of the 125B model and do not pass more tasks. UGREEN's bundled Qwen 3.5 writes fastest but has the weakest German and passes the fewest tasks. Only the versions of the 125B model are both fast and good at German; the uncensored one leads in German."))
    A(f"<h3 id=\"warten\">{T('Wartezeiten im Alltag', 'Waiting times in everyday use')}</h3>")
    zeilen = []
    if zwei:
        zeilen.append([T("Folgefrage im laufenden Gespräch", "follow-up question in a running conversation"), f"{z(zwei['allein']['A']['warten_median_s'], sp, 2)} s"])
    if warte:
        med = lambda name, feld: statistics.median(x[feld] for x in warte[name])
        sek = lambda v: f"{z(v, sp, 1)} s" if v < 90 else f"{z(v / 60, sp, 1)} min"
        for name, de, en_ in (("kurze_frage", "neue kurze Frage", "new short question"), ("eine_seite", "eine Seite Text zum Lesen", "one page of text to read"),
                              ("artikel_10_seiten", "ein Artikel von zehn Seiten", "a ten-page article"), ("bericht_50_seiten", "ein Bericht von 50 Seiten", "a 50-page report"),
                              ("buch_300_seiten", "ein Buch von 300 Seiten", "a 300-page book")):
            if name in warte:
                zeilen.append([T(de, en_), sek(med(name, "erste_anfrage_s"))])
        lang = [n for n in ("bericht_50_seiten", "buch_300_seiten") if n in warte]
        if lang:
            zeilen.append([T("Folgefrage zum selben langen Text", "follow-up question on the same long text"), sek(max(med(n, "folgefrage_s") for n in lang))])
    zeilen.append([T("erste Frage nach einer Pause von 30 Minuten", "first question after a 30-minute break"), f"{z(statistics.median(kalt), sp, 0)} s"])
    if zwei:
        g = zwei["gleichzeitig"]
        zeilen.append([T("zwei Personen fragen gleichzeitig", "two people ask at the same time"), f"{z(min(g['A']['warten_median_s'], g['B']['warten_median_s']), sp, 0)}–{z(max(g['A']['warten_median_s'], g['B']['warten_median_s']), sp, 0)} s"])
    A(tabelle([T("Situation", "Situation"), T("Warten bis zum ersten Wort", "Wait for the first word")], zeilen))
    P(T("Im laufenden Gespräch kommt die Antwort sofort, weil das Modell den bisherigen Verlauf behält. Lange Texte liest es einmal; Folgefragen dazu sind wieder schnell. Nach 30 Minuten ohne Anfrage wird das Modell entladen und beim nächsten Mal neu geladen.",
        "In a running conversation the answer comes at once, because the model keeps the conversation so far. It reads a long text once; follow-up questions on it are fast again. After 30 minutes without a request the model is unloaded and loaded again next time.")
      + (T(f" Für gemeinsame Nutzung ein Modell für alle: Wechseln zwei Personen zwischen zwei Modellen, lädt die Karte jedes Mal um ({z(zwei['wechsel']['warten_median_s'], sp, 0)} s).",
           f" For shared use, pick one model for everyone: if two people alternate between two models, the card reloads every time ({z(zwei['wechsel']['warten_median_s'], sp, 0)} s).") if zwei and "wechsel" in zwei else ""))
    zu()

    kapitel(5, "agent", T("Damit der Agent nicht erfindet", "Keeping the agent from making things up"),
            T("Ein lokales Modell weiß weniger als eines aus der Cloud und gibt das ungern zu. Der Agent zeigte zwei Schwächen: Er erfand Antworten zu Dingen, die es nicht gibt, und er kündigte Schritte an, für die er kein Werkzeug hat. Beides habe ich erst gemessen und dann gesenkt.",
              "A local model knows less than one from the cloud and does not like to admit it. The agent showed two weaknesses: it made up answers about things that do not exist, and it announced steps it has no tool for. I measured both first and then brought them down."))
    A(f"<h3>{T('Erst messen: 16 Fragen je Bereich, die Hälfte davon erfunden', 'Measure first: 16 questions per area, half of them made up')}</h3>")
    P(T("Die Probe fragt in fünf Bereichen nach je acht echten und acht erfundenen Dingen: Gemeinden, Befehlsoptionen, Lehrsätze, Bücher und Parameter der eigenen Werkzeuge. Drei Runden, fünf Modelle, jeweils ohne und mit Regeln: 2.400 Antworten. Zweifelsfälle habe ich nachgelesen; ein „weiß ich nicht“, das trotzdem eine Vermutung anbietet, zählt als erfunden.",
        "The probe asks about eight real and eight made-up things in each of five areas: towns, command options, theorems, books and parameters of the agent's own tools. Three rounds, five models, each without and with rules: 2,400 answers. I re-read the doubtful verdicts; an \"I don't know\" that still offers a guess counts as made up."))
    A(bild(D.erfinden, sp))
    A(f"<h3>{T('Vier Regeln im Systemprompt senken das Erfinden bei diesen Fragen deutlich', 'Four rules in the system prompt clearly reduce making things up on these questions')}</h3>")
    P(T("Ohne die Regeln erkennen die fünf Modelle nur <b>17 bis 60 %</b> des Erfundenen und erfinden den Rest, am häufigsten das Bundesland einer erfundenen Gemeinde und Optionen, die es nicht gibt. Mit den Regeln sind es <b>88 bis 99 %</b>. Echtes beantworten sie dabei so richtig wie vorher (117 bis 120 von 120): Die Regeln machen sie nicht übervorsichtig. Ein anderes Modell half dagegen nicht; zwei dichte Modelle auf derselben Karte erfanden ebenso und schrieben halb so schnell.",
        "Without the rules the five models recognise only <b>17 to 60 %</b> of the made-up things and invent the rest, most often the state of a made-up town and options that do not exist. With the rules it is <b>88 to 99 %</b>. They still answer real things as correctly as before (117 to 120 of 120): the rules do not make them overcautious. A different model did not help; two dense models on the same card invented just as much and wrote at half the speed."))
    A(f"<h3>{T('Für das Urteil reichen drei Runden nicht', 'For judgement, three rounds are not enough')}</h3>")
    A(bild(D.urteil, sp))
    P(T("Dieselben drei Betriebslagen, zehnmal statt dreimal gestellt. Eine harte Anweisung („weicht die Zahl ab, hör auf“) befolgt das Modell in 10 von 10 Antworten. Wo es selbst abwägen muss, sieht es schlechter aus als nach drei Runden: Bricht nachts ein Lauf ab, erfindet es in 6 von 10 Antworten Fähigkeiten, etwa „ich pausiere die Sammlung“. Wer einen Agenten prüft, sollte jede Lage öfter stellen, als es bequem ist.",
        "The same three operating situations, asked ten times instead of three. A hard instruction (\"if the number deviates, stop\") is followed in 10 of 10 answers. Where the model has to weigh things itself, it looks worse than after three rounds: when a job aborts at night, it invents capabilities in 6 of 10 answers, such as \"I'm pausing the collection\". If you test an agent, ask every situation more often than is comfortable."))
    A(f"<h3>{T('Deshalb drei Schichten statt einer', 'Hence three layers instead of one')}</h3>")
    A(bild(D.schichten, sp))
    P(T("Die Regeln im Prompt fangen erfundene Fakten ab, aber keine angekündigten Schritte. Dafür liefern die Werkzeuge des Agenten jetzt einen fertigen Satz und die erlaubten nächsten Schritte, sodass Zahlen aus dem Code kommen. Und ein kleiner Prüfer ohne Sprachmodell liest jede Antwort: Er meldet Zahlen ohne Beleg, angekündigte Schritte ohne Werkzeug und unbekannte Werkzeugnamen. In den Agentenantworten fand er <b>alle sechs</b> erfundenen Abbruch-Antworten, ohne Fehlalarm bei den übrigen Aufgaben. Erfundene Fakten in Worten sieht er nicht: Von 269 erfundenen Antworten der Probe hätte er keine gemeldet.",
        "The rules in the prompt catch made-up facts, but not announced steps. For those, the agent's tools now return a ready sentence and the allowed next steps, so the numbers come from code. And a small checker without a language model reads every answer: it flags unsupported numbers, announced steps without a tool and unknown tool names. In the agent answers it caught <b>all six</b> made-up abort answers, with no false alarm on the other tasks. It does not see made-up facts in plain words: of 269 made-up probe answers it would have flagged none."))
    P(T("<b>Grenzen:</b> Die Probe stellt einzelne Fragen ohne Gesprächsverlauf, mit einem kurzen Systemprompt. Wie stark die Regeln in einem langen Agentenprompt wirken, ist nicht gemessen. Die Regeln nennen außerdem genau die Arten von Dingen, nach denen die Probe fragt (Bundesländer, Autoren, Optionen). Ob sie bei anderen Fragen ebenso gut wirken, ist nicht gemessen.",
        "<b>Limits:</b> the probe asks single questions without a conversation, with a short system prompt. How strongly the rules work inside a long agent prompt is not measured. The rules also name exactly the kinds of things the probe asks about (states, authors, options). Whether they work as well on other questions is not measured.")
      + f' <a href="{doc("agent")}">{T("Alle Messungen im Einzelnen", "All measurements in detail")}</a> · <a href="{GH}/tree/main/konfig/hermes-pruefer">{T("das Prüfer-Plugin", "the checker plugin")}</a> · <a href="{GH}/blob/main/messen/halluzination.py">{T("das Skript der Probe", "the probe script")}</a>')
    zu()

    kapitel(6, "vektor", T("Unzensiert: ein Modell, das nichts ablehnt", "Uncensored: a model that refuses nothing"),
            T("Chat und Agent können jedes Modell der Anlage nutzen; gewählt wird es je Gespräch oder in der Einstellung des Agenten. Eines davon ist unzensiert. Es ist dasselbe 125B-Modell, dem die Ablehnungen entfernt sind: Es beantwortet, was man es fragt, auch das, was das Originalmodell verweigert. Einen Filter gibt es nicht mehr, und es belehrt nicht. Technisch nimmt ein Steuervektor die Richtung aus dem Modell, entlang derer es ablehnt (Abliteration); die Gewichte bleiben dieselben.",
              "Chat and agent can use any model on this setup; it is chosen per conversation or in the agent's settings. One of them is uncensored. It is the same 125B model with its refusals removed: it answers whatever it is asked, including what the original model declines. There is no filter left, and it does not lecture. Technically a steering vector removes the direction along which the model refuses (abliteration); the weights stay the same."))
    A(bild(D.steuervektor, sp))
    P(T("<b>Warum:</b> Ab Werk verweigert oder entschärft das Modell vieles, was am eigenen Gerät niemanden etwas angeht. Ein Assistent zu Hause soll antworten und nicht erziehen. Von 15 Aufgaben, die Modelle oft verweigern, beantwortet das unzensierte alle, das Original 11. Aufgaben, Deutsch und Tempo bleiben gleich.",
        "<b>Why:</b> out of the box the model refuses or waters down a lot that is nobody's business on your own machine. An assistant at home should answer, not educate. Of 15 tasks that models often refuse, the uncensored one answers all, the original 11. Tasks, German and speed stay the same."))
    P(T("<b>Der Preis: Es erfindet leichter.</b> Ein Modell, das nicht mehr „nein“ sagt, sagt auch seltener „weiß ich nicht“. Ohne Regeln erkennt es nur 17 % des Erfundenen statt 29 %; mit den vier Regeln von oben sind es 91 % statt 98 %. Wer es für einen Agenten nimmt, kann auf Regeln und Prüfer nicht verzichten.",
        "<b>The price: it makes things up more easily.</b> A model that no longer says \"no\" also says \"I don't know\" less often. Without rules it recognises only 17 % of made-up things instead of 29 %; with the four rules from above it is 91 % instead of 98 %. If you use it for an agent, the rules and the checker are not optional."))
    P(T("<b>Was man damit auf sich nimmt:</b> Das Modell unterscheidet nicht mehr zwischen einer Frage, die zu Unrecht abgelehnt wurde, und einer, die das Original aus gutem Grund verweigert. Es beantwortet beide. Die Grenze zieht nur noch der Mensch, der fragt, und die Verantwortung trägt, wer es betreibt. Es gehört nicht vor Kinder und nicht in einen Dienst, den Fremde erreichen.",
        "<b>What you take on:</b> the model no longer distinguishes between a question that was refused wrongly and one the original declines for good reason. It answers both. The only line left is drawn by the person asking, and the responsibility lies with whoever runs it. It does not belong in front of children or in a service strangers can reach.")
      + f' <a href="{doc("steuervektor")}">{T("Wie es funktioniert, die Konfiguration und alle Zahlen", "How it works, the config and all numbers")}</a>')
    zu()

    kapitel(7, "strom", T("Was kostet es an Strom?", "What does it cost in power?"))
    A(terminal_strom(strom, sp))
    P(T(f"Das sind <b>{z(s['wh_je_1000_token_gesamt'], sp)} Wh je 1.000 geschriebene Token</b> ({z(s['wh_je_1000_token_ueber_leerlauf'], sp)} Wh über Leerlauf). Ein geladenes Modell kostet rund 3 W mehr als eine leere Karte. Gemessen ist an der USV, an der nur NAS und Dock hängen; im Leerlauf ziehen beide zusammen {z(strom['leer']['usv_w']['mittel'], sp, 0)} W.",
        f"That is <b>{z(s['wh_je_1000_token_gesamt'], sp)} Wh per 1,000 written tokens</b> ({z(s['wh_je_1000_token_ueber_leerlauf'], sp)} Wh above idle). A loaded model costs about 3 W more than an empty card. The measurement is taken at the UPS, which feeds only the NAS and the dock; idle, both together draw {z(strom['leer']['usv_w']['mittel'], sp, 0)} W."))
    zu()

    kapitel(8, "versionen", T("Hält es über Versionen?", "Does it hold across releases?"))
    A(bild(D.versionen, sp))
    P(T("Jede Strata-Version seit 0.2.0-beta ist hier gegen ihre Vorgängerin gemessen, mit identischer Konfiguration. Nichts wurde langsamer.",
        "Every Strata release since 0.2.0-beta was measured here against the one before it, with the identical configuration. Nothing got slower.")
      + f' <a href="{doc("releases")}">{T("Jede Version im Einzelnen", "Every release in detail")}</a>')
    zu()

    kapitel(9, "nachbauen", T("Nachbauen in fünf Schritten", "Rebuild it in five steps"),
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
        (T("Agent dazu", "Add the agent"), T("Hermes Agent mit dem lokalen Modell: Kontext auf 256K stellen, ein Token-Budget für das Nachdenken setzen und die vier Regeln gegen das Erfinden in den Systemprompt nehmen.",
                                             "Hermes Agent with the local model: set the context to 256K, give the reasoning a token budget and put the four rules against making things up into the system prompt."),
         doc("agent"), T("Regeln und Prüfer", "Rules and checker")),
    ]
    A('<ol class="schritte">' + "".join(f'<li><h3>{e(t_)}</h3><p>{b_}</p><a href="{u}">{e(l_)}</a></li>' for t_, b_, u, l_ in schritte) + "</ol>")
    P(T("<b>Der Engpass ist der Arbeitsspeicher.</b> Mit geladenem 125B-Modell bleiben auf 64 GB rund 7 GiB frei; das reicht für Chat, Suche und Agent, aber nicht für einen zweiten großen Dienst. Wer mehr Luft braucht, nimmt ein Modell, das ganz auf die Karte passt.",
        "<b>The bottleneck is memory.</b> With the 125B model loaded, about 7 GiB of the 64 GB stay free; that is enough for chat, search and agent, but not for a second large service. If you need more room, pick a model that fits entirely on the card."))
    P(T("Von unterwegs erreicht man den Aufbau am einfachsten über das VPN des eigenen Routers; ich nutze dafür einen eigenen Zugang mit Anmeldung auf einem kleinen Mietserver. Ins Netz gestellt wird nichts.",
        "From outside, the simplest way in is the VPN of your own router; I use an own gateway with login on a small rented server. Nothing is exposed to the internet.")
      + f' <a href="{doc("comfyui")}">{T("Bilder mit ComfyUI", "Pictures with ComfyUI")}</a> · <a href="{GH}/tree/main/messen">{T("Messskripte und Rohdaten", "Benchmark scripts and raw data")}</a> · <a href="{anker("bauen", "build")}">{T("Strata selbst bauen", "Building Strata yourself")}</a>')
    zu()

    rumpf = "\n".join(teile)
    titel = T("Lokale KI auf dem NAS", "Local AI on a NAS")
    beschr = T("UGREEN iDX6011 Pro mit Radeon RX 7900 XTX im OCuLink-Dock: Messwerte zu Tempo, Strom, Wartezeit und Risiken eines lokalen 125B-Modells. Skripte und Rohdaten auf GitHub.",
               "UGREEN iDX6011 Pro with a Radeon RX 7900 XTX in the OCuLink dock: measurements of speed, power, waiting time and risks of a local 125B model. Scripts and raw data on GitHub.")
    basis = ""
    ordner = ORDNER[sp]
    kanon = f"https://faf.net/{ordner}/"
    nav = [("anlage", T("Aufbau", "Setup")), ("nas", "NAS"), ("dock", T("Dock", "Dock")), ("modell", T("Modell", "Model")), ("agent", "Agent"), ("vektor", T("Unzensiert", "Uncensored")), ("strom", T("Strom", "Power")),
           ("versionen", T("Versionen", "Releases")), ("nachbauen", T("Nachbauen", "Rebuild"))]
    return f'''<!DOCTYPE html>
<html lang="{sp}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)} · faf.net/{ordner}</title>
<meta name="description" content="{e(beschr)}">
<link rel="canonical" href="{kanon}">
<link rel="alternate" hreflang="de" href="https://faf.net/lokale-ki/">
<link rel="alternate" hreflang="en" href="https://faf.net/local-ai/">
<link rel="alternate" hreflang="x-default" href="https://faf.net/local-ai/">
<meta property="og:title" content="{e(titel)}">
<meta property="og:description" content="{e(beschr)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{kanon}">
<meta property="og:image" content="{kanon}og-{sp}.png">
<meta name="color-scheme" content="dark light">
<link rel="preload" href="{basis}fonts/atkinson-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{basis}idx.css">
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
  <figure class="szene"><span class="schild">{T("DIE ANLAGE · NAS, KABEL, DOCK MIT KARTE", "THE SETUP · NAS, CABLE, DOCK WITH CARD")}</span><img src="{basis}bilder/anlage.png" srcset="{basis}bilder/anlage.png 1x, {basis}bilder/anlage@2x.png 2x" width="1032" height="336" alt="{T("Textgrafik: links das NAS mit sechs Einschüben, rechts das Dock mit der Grafikkarte und drei Lüftern, dazwischen das leuchtende OCuLink-Kabel.", "Text graphic: the NAS with six drive bays on the left, the dock with the graphics card and three fans on the right, the glowing OCuLink cable between them.")}"></figure>
  <div class="kacheln">{kacheln}</div>
  <p class="status"><span class="konsole">[ {T("GEMESSEN", "MEASURED")} ]</span> {T("Stand 15.11.2026 · Strata 0.2.12 · UGOS Pro 1.21.1 · Schätzungen sind als solche bezeichnet", "as of 15 Nov 2026 · Strata 0.2.12 · UGOS Pro 1.21.1 · estimates are marked as such")}</p>
  <p class="status"><span class="konsole">[ {T("PARALLEL", "IN PARALLEL")} ]</span> {T("Fotos, Video, Dateifreigaben und USV-Überwachung von UGOS laufen weiter, auch bei geladenem Modell", "photos, video, file shares and UPS monitoring of UGOS keep running, even with the model loaded")}</p>
</section>
{rumpf}
</main>
<footer>
  <p><a href="{readme}">github.com/faf-net/ugreen-idx6011-egpu-llm</a> · MIT · {T("Stand", "build")} {time.strftime("%d.%m.%Y" if not en else "%d %b %Y")}{" · " + stand() if stand() else ""}</p>
  <p>{T("Keine Cookies, kein Tracking, keine Fremdserver. Schriften: Instrument Serif, Atkinson Hyperlegible Next, JetBrains Mono (SIL Open Font License), von hier ausgeliefert.", "No cookies, no tracking, no third-party servers. Fonts: Instrument Serif, Atkinson Hyperlegible Next, JetBrains Mono (SIL Open Font License), served from here.")} <a href="{'../../' if en else '../'}">faf.net</a></p>
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
