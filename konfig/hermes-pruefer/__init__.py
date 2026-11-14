"""pruefer — rule-based output checker for Hermes Agent · regelbasierter Prüfer für Hermes Agent (14.11.2026).

Prüft jede fertige Antwort mit festen Regeln, ohne Sprachmodell, gegen das, was in dieser Sitzung wirklich vorlag
(Nachrichten des Nutzers, Werkzeugergebnisse). Die Regeln sind auf deutschsprachige Antworten zugeschnitten.

  zahl         eine Zahl ab 100 (oder mit Tausenderpunkt), die in keinem Beleg der Sitzung vorkommt
               (Jahreszahlen sowie Summen und Differenzen von Belegzahlen gelten als belegt)
  ankuendigung „ich pausiere“, „pausiere ich“, „ich wiederhole in 4 Stunden“, „Retry“, „längerer Timeout“ …
               – angekündigte Schritte, für die der Agent meist kein Werkzeug hat
  gemessen     „gemessen“, obwohl in diesem Zug kein Werkzeug lief
  werkzeug     ein Werkzeugname mit dem Präfix PRUEFER_PRAEFIX, der weder in PRUEFER_WERKZEUGE steht noch in dieser
               Sitzung aufgerufen wurde (ohne PRUEFER_PRAEFIX ist diese Regel aus)

Modus steht in $PRUEFER_DIR/modus (Vorgabe „beobachten“), PRUEFER_DIR ist /opt/data/pruefer, wenn nicht gesetzt:
  beobachten  Antwort bleibt unverändert, Befunde nur nach $PRUEFER_DIR/befunde.jsonl
  hinweis     zusätzlich eine Zeile „⚠ Prüfer: …“ unter der Antwort
  aus         nichts tun
Hängt sich nur an Plugin-Haken (pre_llm_call, post_tool_call, transform_llm_output), ändert nichts am Kern.
Fehler im Prüfer dürfen nie eine Antwort verhindern: alles ist in try/except gefasst.
"""
import json
import logging
import os
import re
import threading
import time

_DIR = os.environ.get("PRUEFER_DIR", "/opt/data/pruefer")
_LOG = os.path.join(_DIR, "befunde.jsonl")
_MODUS_DATEI = os.path.join(_DIR, "modus")
_log = logging.getLogger("plugins.pruefer")

_PRAEFIX = os.environ.get("PRUEFER_PRAEFIX", "").strip()
_BEKANNT = {w.strip() for w in os.environ.get("PRUEFER_WERKZEUGE", "").split(",") if w.strip()}

ZAHL = re.compile(r"(?<![\d.,:/-])(\d{1,3}(?:\.\d{3})+|\d{3,})(?:,\d+)?(?![\d:/-])")
ANKUENDIGUNG = re.compile(
    r"\bich\s+(?:pausiere|unterbreche|sperre|markiere|plane|wiederhole\b[^.]{0,40}\b(?:später|in\s+\d+|morgen|nachher)"
    r"|werde\b[^.]{0,50}\b(?:pausieren|unterbrechen|sperren|markieren|erneut versuchen|später wiederholen|"
    r"in\s+\d+\s+(?:Stunden|Minuten)))"
    r"|\bin\s+\d+\s+(?:Stunden|Minuten)\s+(?:erneut|nochmal|noch einmal|wieder)\b"
    r"|\b(?:Backoff|automatisch(?:e|en)? Wiederholung)\b"
    # umgestellte Wortstellung, Retry, Timeout, Überwachen, Deaktivieren
    r"|\b(?:pausiere|unterbreche|sperre|markiere|deaktiviere|überwache)\s+ich\b"
    r"|\bich\s+(?:überwache|deaktiviere|erhöhe\b[^.]{0,30}\bTimeout)"
    r"|\b(?:Retry|Retries)\b"
    r"|\b(?:längere[mn]?|erhöhte[mn]?)\s+Timeout\b|\bTimeout\s+(?:erhöhen|verlängern)\b", re.I)
GEMESSEN = re.compile(r"\bgemessen\b", re.I)
WERKZEUGNAME = re.compile(r"\b" + re.escape(_PRAEFIX) + r"[a-z_]+\b") if _PRAEFIX else None

_sitzungen: dict = {}
_sperre = threading.Lock()


def _modus() -> str:
    try:
        with open(_MODUS_DATEI, encoding="utf-8") as fh:
            m = fh.read().strip()
        return m if m in ("beobachten", "hinweis", "aus") else "beobachten"
    except OSError:
        return "beobachten"


def _text(inhalt) -> str:
    if isinstance(inhalt, str):
        return inhalt
    if isinstance(inhalt, list):
        return " ".join(_text(t.get("text", "") if isinstance(t, dict) else t) for t in inhalt)
    try:
        return json.dumps(inhalt, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return str(inhalt)


def _zahlen(text: str) -> set:
    """Alle Ziffernfolgen, Tausenderpunkte entfernt (227.970 → 227970)."""
    t = re.sub(r"(?<=\d)[.,'\u202f](?=\d{3}\b)", "", text)
    return set(re.findall(r"\d+", t))


def _sitzung(sid: str) -> dict:
    with _sperre:
        s = _sitzungen.get(sid)
        if s is None:
            if len(_sitzungen) > 50:
                for alt in sorted(_sitzungen, key=lambda k: _sitzungen[k]["zeit"])[:10]:
                    _sitzungen.pop(alt, None)
            s = _sitzungen[sid] = {"zahlen": set(), "namen": set(), "zuege": {}, "zeit": time.time()}
        s["zeit"] = time.time()
        return s


def _pre_llm_call(session_id="", turn_id="", user_message="", conversation_history=None, **_):
    try:
        if _modus() == "aus":
            return None
        s = _sitzung(session_id or "-")
        teile = [_text(user_message)]
        for m in conversation_history or []:
            if not isinstance(m, dict):
                continue
            if m.get("role") in ("user", "tool", "system"):
                teile.append(_text(m.get("content")))
            for tc in m.get("tool_calls") or []:
                f = (tc or {}).get("function") or {}
                if f.get("name"):
                    s["namen"].add(f["name"])
        s["zahlen"] |= _zahlen(" ".join(teile))
        s["zuege"].setdefault(turn_id, 0)
    except Exception:  # noqa: BLE001
        _log.debug("pruefer pre_llm_call", exc_info=True)
    return None


def _post_tool_call(tool_name="", args=None, result=None, session_id="", turn_id="", **_):
    try:
        if _modus() == "aus":
            return None
        s = _sitzung(session_id or "-")
        s["namen"].add(tool_name)
        s["zahlen"] |= _zahlen(_text(args) + " " + _text(result)[:400000])
        s["zuege"][turn_id] = s["zuege"].get(turn_id, 0) + 1
    except Exception:  # noqa: BLE001
        _log.debug("pruefer post_tool_call", exc_info=True)
    return None


def _abgeleitet(z: int, belege: set) -> bool:
    """Summe oder Differenz von zwei bzw. Summe von drei Belegzahlen (227.917 + 34 + 19 = 227.970)."""
    werte = sorted({int(b) for b in belege if b.isdigit() and len(b) < 13})[:400]
    ws = set(werte)
    for i, a in enumerate(werte):
        if (z - a) in ws or (a - z) in ws:
            return True
        if len(werte) <= 400:
            for b in werte[i:]:
                if (z - a - b) in ws:
                    return True
    return False


def pruefen(antwort: str, belegzahlen: set, namen: set, werkzeuge_im_zug: int) -> list:
    befunde = []
    for m in ZAHL.finditer(antwort):
        roh = m.group(1)
        z = roh.replace(".", "")
        if len(z) == 4 and 1900 <= int(z) <= 2099:  # Jahreszahl
            continue
        if z not in belegzahlen and not _abgeleitet(int(z), belegzahlen):
            befunde.append({"art": "zahl", "text": roh})
    for m in ANKUENDIGUNG.finditer(antwort):
        befunde.append({"art": "ankuendigung", "text": m.group(0)[:80]})
    if werkzeuge_im_zug == 0 and GEMESSEN.search(antwort):
        befunde.append({"art": "gemessen", "text": "„gemessen“ ohne Werkzeugaufruf in diesem Zug"})
    for m in set(WERKZEUGNAME.findall(antwort)) if WERKZEUGNAME else ():
        if m not in _BEKANNT and m not in namen:
            befunde.append({"art": "werkzeug", "text": m})
    return befunde


_WORT = {"zahl": "Zahl ohne Beleg", "ankuendigung": "Schritt ohne Werkzeug", "gemessen": "„gemessen“ ohne Messung",
         "werkzeug": "unbekanntes Werkzeug"}


def _transform_llm_output(response_text="", session_id="", turn_id="", platform="", model="", **_):
    try:
        modus = _modus()
        if modus == "aus" or not response_text:
            return None
        s = _sitzung(session_id or "-")
        befunde = pruefen(response_text, s["zahlen"], s["namen"], s["zuege"].get(turn_id, 0))
        os.makedirs(_DIR, exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"zeit": time.strftime("%Y-%m-%d %H:%M:%S"), "sitzung": session_id, "zug": turn_id,
                                 "plattform": platform, "modell": model, "modus": modus,
                                 "werkzeuge_im_zug": s["zuege"].get(turn_id, 0), "befunde": befunde,
                                 "antwort": response_text[:2000]}, ensure_ascii=False) + "\n")
        if modus == "hinweis" and befunde:
            kurz = "; ".join(f"{_WORT[b['art']]}: {b['text']}" for b in befunde[:6])
            return response_text.rstrip() + f"\n\n⚠ Prüfer: {kurz}"
    except Exception:  # noqa: BLE001
        _log.debug("pruefer transform_llm_output", exc_info=True)
    return None


def register(ctx):
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("transform_llm_output", _transform_llm_output)
