"""ComfyUI auf der XTX als Bild-Anbieter für Hermes Agent (23.10.2026).

Der Aufruf geht an llama-swap (``/comfyui/``), das ComfyUI bei Bedarf startet und dafür das
gerade geladene Strata-Modell entlädt. Die Arbeitsabläufe liegen im API-Format unter
``workflows/<modell>.json`` neben dieser Datei; Platzhalter ``%%PROMPT%%``, ``%%SEED%%``,
``%%WIDTH%%`` und ``%%HEIGHT%%`` werden vor dem Absenden ersetzt.

Auswahl: ``image_gen.comfyui.model`` → ``image_gen.model`` → :data:`DEFAULT_MODEL`;
Adresse: ``image_gen.comfyui.base_url`` → :data:`DEFAULT_BASE_URL`.
"""

from __future__ import annotations

import base64
import json
import logging
import random
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Optional

from agent.image_gen_provider import DEFAULT_ASPECT_RATIO, resolve_aspect_ratio, success_response
from plugins.image_gen._common import (
    StaticImageGenProvider, error_factory, load_image_gen_config, materialize_image,
    prompt_required_error, resolve_static_model)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://llama-swap:8090/comfyui"  # anpassen oder image_gen.comfyui.base_url setzen
DEFAULT_MODEL = "z-image-turbo"
WORKFLOWS = Path(__file__).with_name("workflows")
START_TIMEOUT = 600   # s: Strata entladen, Container starten, Modell laden
RUN_TIMEOUT = 900     # s: ein Bild, auch im Vollmodell

MODELS: dict[str, dict[str, Any]] = {
    "z-image-turbo": {
        "display": "Z-Image Turbo (lokal, XTX)", "speed": "schnell, 8 Schritte",
        "strengths": "Fotorealismus, Text im Bild, keine Filter",
        "sizes": {"landscape": (1344, 768), "square": (1024, 1024), "portrait": (768, 1344)},
    },
    "qwen-image": {
        "display": "Qwen-Image 2.1 (lokal, XTX)", "speed": "langsam",
        "strengths": "beste Bildtreue, Schrift, Komposition",
        "sizes": {"landscape": (1664, 928), "square": (1328, 1328), "portrait": (928, 1664)},
    },
    "qwen-image-turbo": {
        "display": "Qwen-Image 2.1 Turbo (lokal, XTX)", "speed": "mittel",
        "strengths": "Qwen-Qualität mit wenigen Schritten",
        "sizes": {"landscape": (1664, 928), "square": (1328, 1328), "portrait": (928, 1664)},
    },
    "chroma": {
        "display": "Chroma1-HD (lokal, XTX)", "speed": "mittel",
        "strengths": "kräftige Farben, Malstil, Apache 2.0",
        "sizes": {"landscape": (1344, 768), "square": (1024, 1024), "portrait": (768, 1344)},
    },
}


def _base_url() -> str:
    cfg = load_image_gen_config("comfyui")
    return str(cfg.get("base_url") or DEFAULT_BASE_URL).rstrip("/")


def _request(url: str, data: Optional[dict] = None, timeout: float = 30) -> bytes:
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"} if body else {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _fill(node: Any, values: dict[str, Any]) -> Any:
    """Platzhalter ersetzen: ein Wert, der genau ``%%NAME%%`` ist, bekommt den Typ des Ersatzes."""
    if isinstance(node, dict):
        return {k: _fill(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v, values) for v in node]
    if isinstance(node, str) and node.startswith("%%") and node.endswith("%%") and node[2:-2] in values:
        return values[node[2:-2]]
    return node


class ComfyUIImageGenProvider(StaticImageGenProvider):
    """Text-zu-Bild über ComfyUI hinter llama-swap; lokal, ohne Schlüssel."""

    provider_id = "comfyui"
    label = "ComfyUI (iDX)"
    models = MODELS
    default_model_id = DEFAULT_MODEL
    price = "lokal"

    def is_available(self) -> bool:
        return WORKFLOWS.is_dir()

    def get_setup_schema(self) -> dict[str, Any]:
        return {"name": self.label, "badge": "local", "tag": "ComfyUI auf der XTX über llama-swap", "env_vars": []}

    def generate(
        self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, *,
        image_url: Optional[str] = None, reference_image_urls: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)
        if not prompt:
            return prompt_required_error("comfyui", aspect)
        model_id, meta = resolve_static_model(MODELS, DEFAULT_MODEL, env_var="COMFYUI_IMAGE_MODEL", config_key="comfyui")
        fail = error_factory("comfyui", aspect, model=model_id, prompt=prompt)
        if image_url or reference_image_urls:
            logger.info("comfyui: Bildvorlagen werden noch nicht unterstützt, erzeuge nur aus Text")
        try:
            workflow = json.loads((WORKFLOWS / f"{model_id}.json").read_text(encoding="utf-8"))
        except OSError as exc:
            return fail(f"Arbeitsablauf für {model_id} fehlt: {exc}", "config_error")
        width, height = meta["sizes"][aspect]
        seed = random.randint(1, 2**48)
        workflow = _fill(workflow, {"PROMPT": prompt, "SEED": seed, "WIDTH": width, "HEIGHT": height})

        base = _base_url()
        t0 = time.time()
        try:
            # Ein POST startet ComfyUI über llama-swap; die Antwort kommt erst, wenn es bereit ist.
            answer = json.loads(_request(f"{base}/api/prompt", {"prompt": workflow, "client_id": str(uuid.uuid4())},
                                         timeout=START_TIMEOUT))
        except Exception as exc:
            return fail(f"ComfyUI nimmt den Auftrag nicht an: {exc}", "api_error")
        prompt_id = answer.get("prompt_id")
        if not prompt_id:
            return fail(f"ComfyUI lehnt den Auftrag ab: {answer.get('error') or answer.get('node_errors')}", "api_error")

        deadline = time.time() + RUN_TIMEOUT
        images: list[dict[str, Any]] = []
        verloren = 0  # Abfragen, bei denen der Auftrag weder in der Warteschlange noch im Verlauf steht
        while time.time() < deadline:
            time.sleep(2)
            try:
                entry = json.loads(_request(f"{base}/api/history/{prompt_id}")).get(prompt_id)
                if not entry:
                    queue = json.loads(_request(f"{base}/api/queue"))
                    wartend = [q[1] for q in queue.get("queue_running", []) + queue.get("queue_pending", [])]
                    verloren = 0 if prompt_id in wartend else verloren + 1
            except Exception as exc:  # noqa: BLE001 — kurz weg, z. B. während llama-swap umlädt
                logger.debug("comfyui: history nicht erreichbar: %s", exc)
                verloren += 1
                entry = None
            if verloren >= 5:
                # 23.10.2026: Ein Absturz von ComfyUI (GPU-Fehler) verliert den Auftrag; llama-swap startet
                # ComfyUI neu, und ohne diese Prüfung wartete der Aufruf bis zum Zeitlimit.
                return fail("ComfyUI hat den Auftrag verloren, vermutlich abgestürzt und neu gestartet", "api_error")
            if not entry:
                continue
            status = entry.get("status") or {}
            if status.get("status_str") == "error":
                msgs = [m for m in status.get("messages", []) if m and m[0] == "execution_error"]
                detail = msgs[-1][1].get("exception_message", "") if msgs else ""
                return fail(f"ComfyUI meldet einen Fehler: {detail}".strip(), "api_error")
            images = [img for out in (entry.get("outputs") or {}).values() for img in out.get("images", [])
                      if img.get("type") == "output"]
            if images:
                break
        if not images:
            return fail(f"Kein Bild nach {RUN_TIMEOUT} s", "timeout")

        first = images[0]
        query = urllib.parse.urlencode({"filename": first["filename"], "subfolder": first.get("subfolder", ""),
                                        "type": "output"})
        try:
            raw = _request(f"{base}/api/view?{query}", timeout=60)
        except Exception as exc:
            return fail(f"Bild konnte nicht abgeholt werden: {exc}", "api_error")
        image_ref, err = materialize_image(
            base64.b64encode(raw).decode(), None, prefix=f"comfyui_{model_id}", label="ComfyUI",
            provider="comfyui", model=model_id, prompt=prompt, aspect=aspect, log=logger)
        if err:
            return err
        return success_response(
            image=image_ref, model=model_id, prompt=prompt, aspect_ratio=aspect, provider="comfyui",
            extra={"size": f"{width}x{height}", "seed": seed, "seconds": round(time.time() - t0, 1)})


def register(ctx) -> None:
    """Plugin-Einstieg: den Anbieter ``comfyui`` anmelden."""
    ctx.register_image_gen_provider(ComfyUIImageGenProvider())
