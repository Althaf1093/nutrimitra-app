"""Food-photo recognition providers.

A provider takes a base64 image and returns the model's raw text; analyze_image() tries the providers
selected by VISION_PROVIDER in order and returns the first reply that parses as nutrition JSON.

    gemini  Google Gemini Flash (default)
    groq    Groq's vision model (optional secondary)
    auto    Gemini first, then Groq

To add another provider, subclass VisionProvider and list it in build_providers(). Image bytes are never
logged, and API keys are sent in headers, never in URLs.
"""
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("nutrimitra.vision")

# Model ids come from the providers' docs (ai.google.dev/gemini-api/docs/models, console.groq.com/docs/vision)
# and can be changed with GEMINI_MODEL / GROQ_VISION_MODEL when they retire a model.
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"
DEFAULT_GROQ_VISION_MODEL = "qwen/qwen3.8-27b"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
PROVIDER_CHOICES = ("gemini", "groq", "auto")
RETRY_STATUSES = {429, 500, 503}
RETRY_DELAYS = (1.0, 2.0)  # at most 2 retries after the first attempt

VISION_PROMPT = (
    "Identify the food in this photo for an Indian wellness app. Respond with ONLY compact JSON, no markdown: "
    '{"name": str, "portion": str, "calories": int, "protein_g": number, "carbs_g": number, "fat_g": number, '
    '"confidence": "low|medium|high", "alternatives": [str, str]}. '
    "Estimate for a typical home serving. Prefer Indian dish names when relevant."
)


class VisionNotConfigured(Exception):
    """No selected provider has the settings (API key) it needs."""


class VisionUnavailable(Exception):
    """Providers are configured, but none gave a usable answer."""


class ProviderError(Exception):
    """One provider failed; the reason is safe to log (never contains image data or keys)."""


@dataclass
class VisionResult:
    data: Dict[str, Any]
    provider: str
    model: str


def sniff_mime(image_base64: str) -> str:
    """Image type from the first base64 characters (the app sends JPEG; PNG and WebP are accepted too)."""
    if image_base64.startswith("iVBOR"):
        return "image/png"
    if image_base64.startswith("UklG"):
        return "image/webp"
    return "image/jpeg"


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """The first JSON object in a model reply, ignoring reasoning blocks and code fences."""
    cleaned = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) and parsed else None


def error_reason(response: httpx.Response) -> str:
    """The provider's own error message (never the request, so no image or key), for the log line."""
    try:
        error = response.json().get("error")
    except (ValueError, AttributeError):
        return ""
    message = error.get("message") if isinstance(error, dict) else error
    return f": {str(message)[:200]}" if message else ""


def retry_delay(response: httpx.Response, attempt: int) -> float:
    try:
        suggested = float(response.headers.get("retry-after", ""))
    except ValueError:
        suggested = 0.0
    return min(max(RETRY_DELAYS[attempt], suggested), 10.0)


class VisionProvider:
    name = ""
    model = ""

    def configured(self) -> bool:
        raise NotImplementedError

    async def analyze(self, image_base64: str, mime_type: str) -> str:
        """Raw model text for the image; raises ProviderError."""
        raise NotImplementedError

    async def post(self, url: str, headers: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
        """POST with backoff on 429/500/503; returns the JSON body or raises ProviderError."""
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                async with httpx.AsyncClient(timeout=60) as http:
                    response = await http.post(url, headers=headers, json=body)
            except httpx.HTTPError as exc:
                raise ProviderError(f"{self.name} request failed: {type(exc).__name__}") from exc
            if response.status_code in RETRY_STATUSES and attempt < len(RETRY_DELAYS):
                delay = retry_delay(response, attempt)
                logger.info("%s returned %s; retrying in %.1fs", self.name, response.status_code, delay)
                await asyncio.sleep(delay)
                continue
            if response.status_code != 200:
                raise ProviderError(f"{self.name} returned HTTP {response.status_code}{error_reason(response)}")
            try:
                return response.json()
            except ValueError as exc:
                raise ProviderError(f"{self.name} returned a non-JSON response") from exc
        raise ProviderError(f"{self.name} did not answer")


class GeminiProvider(VisionProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def configured(self) -> bool:
        return bool(self.api_key)

    async def analyze(self, image_base64: str, mime_type: str) -> str:
        body = {
            "contents": [{"parts": [{"text": VISION_PROMPT}, {"inline_data": {"mime_type": mime_type, "data": image_base64}}]}],
            # Room for thinking tokens, which count against the output limit on Gemini 3 models.
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2, "maxOutputTokens": 2048},
        }
        data = await self.post(f"{self.base_url}/v1beta/models/{self.model}:generateContent", {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}, body)
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise ProviderError(f"gemini returned no answer ({reason})")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(str(part.get("text", "")) for part in parts if not part.get("thought"))
        if not text.strip():
            raise ProviderError(f"gemini returned an empty answer (finish: {candidates[0].get('finishReason', 'unknown')})")
        return text


class GroqVisionProvider(VisionProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def analyze(self, image_base64: str, mime_type: str) -> str:
        body = {
            "model": self.model,
            "temperature": 0.2,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": [{"type": "text", "text": VISION_PROMPT}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}]}],
        }
        data = await self.post(f"{self.base_url}/chat/completions", {"Authorization": f"Bearer {self.api_key}"}, body)
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("groq returned an unreadable response") from exc
        if not text.strip():
            raise ProviderError("groq returned an empty answer")
        return text


def provider_setting() -> str:
    value = (os.getenv("VISION_PROVIDER") or "gemini").strip().lower()
    if value not in PROVIDER_CHOICES:
        logger.warning("Unknown VISION_PROVIDER %r; using gemini", value)
        return "gemini"
    return value


def build_providers(setting: Optional[str] = None) -> List[VisionProvider]:
    """The selected providers, in the order they are tried. Settings are read from the environment on each call."""
    setting = setting or provider_setting()
    gemini = GeminiProvider(os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL, os.getenv("GEMINI_BASE_URL") or DEFAULT_GEMINI_BASE_URL)
    groq = GroqVisionProvider(os.getenv("GROQ_API_KEY", ""), os.getenv("GROQ_VISION_MODEL") or DEFAULT_GROQ_VISION_MODEL, (os.getenv("GROQ_BASE_URL") or DEFAULT_GROQ_BASE_URL))
    return {"gemini": [gemini], "groq": [groq], "auto": [gemini, groq]}[setting]


def status() -> Dict[str, Any]:
    """Which providers would be used and whether each is ready (no keys or secrets)."""
    providers = build_providers()
    return {"setting": provider_setting(), "providers": [{"name": p.name, "model": p.model, "configured": p.configured()} for p in providers]}


async def analyze_image(image_base64: str, user_id: str) -> VisionResult:
    """Try each configured provider in order; the first reply that parses as nutrition JSON wins."""
    providers = [p for p in build_providers() if p.configured()]
    if not providers:
        raise VisionNotConfigured("No vision provider is configured")
    mime_type = sniff_mime(image_base64)
    for provider in providers:
        try:
            text = await provider.analyze(image_base64, mime_type)
        except ProviderError as exc:
            logger.warning("Vision provider failed for %s: %s", user_id, exc)
            continue
        parsed = extract_json(text)
        if parsed:
            return VisionResult(parsed, provider.name, provider.model)
        logger.warning("Vision provider %s returned text that is not nutrition JSON for %s (%d chars)", provider.name, user_id, len(text))
    raise VisionUnavailable("No vision provider returned a usable answer")
