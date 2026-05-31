from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


class LLMConfigError(RuntimeError):
    pass


# Reasoning models (MiniMax-M2, DeepSeek-R1, some Kimi variants) prepend an
# internal <think>...</think> block even in JSON mode; strip it before parsing.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def _strip_thinking(content: str) -> str:
    return _THINK_BLOCK_RE.sub("", content).strip() if content else content


def _request_timeout() -> float:
    """Per-request read timeout. Reasoning models (e.g. Kimi) over a long
    transcript can run for minutes, so allow override via LLM_REQUEST_TIMEOUT."""
    try:
        return float(os.environ.get("LLM_REQUEST_TIMEOUT", "180"))
    except ValueError:
        return 180.0


def _provider_config(name: str) -> dict[str, Any] | None:
    """Resolve one OpenAI-compatible provider from env, using the same key
    names as the knowledge_ingest pipeline so a single shared .env serves both."""
    if name == "minimax":
        return {
            "name": "minimax",
            "api_key": os.environ.get("MINIMAX_API_KEY"),
            "base_url": os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1").rstrip("/"),
            "model": os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7"),
            "headers": {},
        }
    if name == "kimi":
        return {
            "name": "kimi",
            "api_key": os.environ.get("KIMI_API_KEY"),
            "base_url": os.environ.get("KIMI_BASE_URL", "https://api.kimi.com/coding/v1").rstrip("/"),
            "model": os.environ.get("KIMI_MODEL", "kimi-for-coding"),
            # Kimi-for-coding endpoint sniffs client identity; mimic Claude Code.
            "headers": {"User-Agent": "claude-cli/2.0.0 (external, darwin)", "X-Client-Type": "claude-code"},
        }
    if name == "openai":
        return {
            "name": "openai",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "base_url": (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
            "model": os.environ.get("VIDEO_SLICER_MODEL") or os.environ.get("OPENAI_MODEL"),
            "headers": {},
        }
    return None


def _provider_chain() -> list[dict[str, Any]]:
    """Ordered [primary, fallback, openai] chain, keeping only providers that
    have both a key and a model. Selection mirrors knowledge_ingest's .env:
    LLM_PROVIDER (default minimax) then LLM_FALLBACK (default kimi)."""
    primary = os.environ.get("LLM_PROVIDER", "minimax").strip().lower()
    fallback = os.environ.get("LLM_FALLBACK", "kimi").strip().lower()
    order: list[str] = []
    for name in (primary, fallback, "openai"):
        if name and name not in order:
            order.append(name)
    chain = []
    for name in order:
        cfg = _provider_config(name)
        if cfg and cfg.get("api_key") and cfg.get("model"):
            chain.append(cfg)
    return chain


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        if api_key:
            model = model or os.environ.get("VIDEO_SLICER_MODEL") or os.environ.get("OPENAI_MODEL")
            if not model:
                raise LLMConfigError("Missing model (set VIDEO_SLICER_MODEL).")
            self.providers = [{
                "name": "custom",
                "api_key": api_key,
                "base_url": (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
                "model": model,
                "headers": {},
            }]
        else:
            self.providers = _provider_chain()
            if not self.providers:
                raise LLMConfigError(
                    "No LLM provider configured. Set LLM_PROVIDER + MINIMAX_API_KEY/KIMI_API_KEY "
                    "(or OPENAI_API_KEY + VIDEO_SLICER_MODEL) in the .env."
                )

    @classmethod
    def available(cls) -> bool:
        return bool(_provider_chain())

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, json_mode: bool = False) -> str:
        last_error: Exception | None = None
        for provider in self.providers:
            payload: dict[str, Any] = {"model": provider["model"], "messages": messages, "temperature": temperature}
            if json_mode:
                # Honored by MiniMax/Kimi/OpenAI; forces well-formed JSON output.
                payload["response_format"] = {"type": "json_object"}
            request = urllib.request.Request(
                f"{provider['base_url']}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {provider['api_key']}",
                    **provider.get("headers", {}),
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=_request_timeout()) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return _strip_thinking(str(data["choices"][0]["message"]["content"]))
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"{provider['name']} HTTP {error.code}: {body}")
            except urllib.error.URLError as error:
                last_error = RuntimeError(f"{provider['name']} unreachable: {error}")
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    def chat_json(self, messages: list[dict[str, str]], temperature: float = 0.2) -> dict[str, Any]:
        content = self.chat(messages, temperature=temperature, json_mode=True)
        return parse_json_response(content)

    def translate_texts(self, texts: list[str], target_language: str = "zh") -> list[str]:
        if not texts:
            return []
        data = self.chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Translate subtitle cues. Return strict JSON only, with key "
                        '"translations" as an array of strings. Preserve count and order.'
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"target_language": target_language, "texts": texts},
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.1,
        )
        translations = data.get("translations")
        if not isinstance(translations, list) or len(translations) != len(texts):
            raise ValueError("LLM translation response did not preserve cue count.")
        return [str(item) for item in translations]


def parse_json_response(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object.")
    return data

