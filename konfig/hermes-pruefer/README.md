# pruefer — rule-based output checker for Hermes Agent

*Deutsch weiter unten.*

A small plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that reads every final answer of the
agent and checks it with fixed rules, **without a language model**, against what really happened in the session
(user messages, tool results). It is written for German answers.

| Rule | Flags |
|---|---|
| `zahl` | a number ≥ 100 (or with a thousands separator) that appears in no message or tool result of the session; years and sums/differences of evidenced numbers count as evidenced |
| `ankuendigung` | announced steps the agent usually has no tool for: „ich pausiere“, „pausiere ich“, „ich wiederhole in 4 Stunden“, „Retry“, „Backoff“, „längerer Timeout“, „ich überwache“ … |
| `gemessen` | the word „gemessen“ (measured) although no tool ran in this turn |
| `werkzeug` | a tool name with prefix `PRUEFER_PRAEFIX` that is neither in `PRUEFER_WERKZEUGE` nor was called in the session |

What it does **not** see: made-up facts in plain words („liegt in Bayern“). Against those, rules in the system prompt
help far more, see the README section of 14/15 Nov 2026.

## Install

```
cp -r konfig/hermes-pruefer  <hermes data>/plugins/pruefer
# config.yaml → plugins.enabled: [..., pruefer]
mkdir -p /opt/data/pruefer && echo beobachten > /opt/data/pruefer/modus
```

Environment (optional): `PRUEFER_DIR` (default `/opt/data/pruefer`), `PRUEFER_PRAEFIX` (e.g. `katalog_`; empty = rule
`werkzeug` off), `PRUEFER_WERKZEUGE` (comma list of real tool names with that prefix).

Mode in `$PRUEFER_DIR/modus`: `beobachten` (log only, default) · `hinweis` (adds a line „⚠ Prüfer: …“ under the
answer) · `aus`. Findings go to `$PRUEFER_DIR/befunde.jsonl`. The plugin only uses the hooks `pre_llm_call`,
`post_tool_call` and `transform_llm_output`, never blocks an answer and swallows its own errors.

---

## Deutsch

Ein kleines Plugin für Hermes Agent, das jede fertige Antwort mit festen Regeln prüft, ohne Sprachmodell, gegen das,
was in der Sitzung wirklich vorlag (Nachrichten, Werkzeugergebnisse). Es meldet unbelegte Zahlen, angekündigte
Schritte ohne Werkzeug, „gemessen“ ohne Messung und unbekannte Werkzeugnamen. Erfundene Fakten in Worten sieht es
nicht; dagegen helfen Regeln im Systemprompt deutlich mehr (Nachtrag 14./15.11.2026 im README).

Einbau wie oben. Modus in `$PRUEFER_DIR/modus`: `beobachten` (nur protokollieren, Vorgabe), `hinweis` (Zeile
„⚠ Prüfer: …“ unter der Antwort), `aus`. Befunde in `$PRUEFER_DIR/befunde.jsonl`.

Gemessen auf 90 Agentenantworten (faber, 9 Aufgaben × 10 Runden): Alle sechs nachgelesenen Antworten, die in einer
Abbruchlage Fähigkeiten erfanden („…, pausiere ich die Sammlung …“), wurden gemeldet, in den übrigen
Aufgaben gab es keinen Fehlalarm. Die Gegenprobe auf den Antworten von velox, Qwen3.8-27B und Gemma 4 31B ergab ebenfalls keine
Fehlalarme außerhalb von Berichten und Abbruchlagen.
