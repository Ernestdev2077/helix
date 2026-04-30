"""AI image generation. Uses OpenAI directly via httpx — clean separation
from OpenRouter (which is text-only)."""

from __future__ import annotations

import base64
import logging
import os
from io import BytesIO
from typing import TYPE_CHECKING

import httpx
from django.core.files.base import ContentFile
from PIL import Image

from .models import MediaAsset

if TYPE_CHECKING:  # pragma: no cover
    from apps.accounts.models import User
    from apps.brands.models import Brand
    from apps.content.models import PostVariant
    from apps.workspaces.models import Workspace

log = logging.getLogger(__name__)

OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"


class ImageGenerationError(Exception):
    pass


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _image_prompt_for(*, variant: "PostVariant", brand: "Brand") -> str:
    """Turn a written post into an image prompt — keeps it short, on-brand."""
    base_voice = (brand.voice_description or "").strip()
    palette = f"accent color {brand.accent_color}" if brand.accent_color else ""
    text_excerpt = variant.content[:280].strip()

    bits = [
        "Editorial social media illustration for a SaaS product launch.",
        "Clean modern visual style, minimalist composition, high contrast,",
        "no logo, no real text on the image, no watermark.",
    ]
    if base_voice:
        bits.append(f"Brand voice: {base_voice}.")
    if palette:
        bits.append(palette + ".")
    bits.append(f'Inspired by this post: "{text_excerpt}"')
    return " ".join(bits)


def generate_image_for_variant(
    *,
    variant: "PostVariant",
    brand: "Brand",
    workspace: "Workspace",
    user: "User",
    size: str = "1024x1024",
    quality: str = "standard",
) -> MediaAsset:
    """Synchronous OpenAI image generation. Returns a saved MediaAsset.

    Pricing reference (DALL-E 3, 2024-2025):
      - 1024x1024 standard: $0.040
      - 1024x1024 hd:       $0.080
      - 1792x1024:          $0.080
    """
    if not has_openai_key():
        raise ImageGenerationError(
            "OPENAI_API_KEY not configured. Add it to .env to enable AI image generation."
        )

    prompt = _image_prompt_for(variant=variant, brand=brand)
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "response_format": "b64_json",
    }
    log.info("Generating image for variant %s (size=%s, quality=%s)", variant.id, size, quality)

    try:
        response = httpx.post(OPENAI_IMAGE_ENDPOINT, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.exception("OpenAI image gen failed")
        body = ""
        try:
            body = response.text[:300]  # type: ignore[name-defined]
        except Exception:  # noqa: BLE001
            pass
        raise ImageGenerationError(f"OpenAI request failed: {exc} {body}") from exc

    data = response.json()
    if not data.get("data"):
        raise ImageGenerationError(f"OpenAI returned no images: {data}")
    b64 = data["data"][0].get("b64_json")
    if not b64:
        raise ImageGenerationError("OpenAI response missing b64_json")
    raw = base64.b64decode(b64)

    width, height = 0, 0
    try:
        with Image.open(BytesIO(raw)) as img:
            width, height = img.size
    except Exception:  # noqa: BLE001
        pass

    cost = {
        ("1024x1024", "standard"): 0.040,
        ("1024x1024", "hd"): 0.080,
        ("1792x1024", "standard"): 0.080,
        ("1792x1024", "hd"): 0.120,
    }.get((size, quality), 0.040)

    asset = MediaAsset(
        workspace=workspace,
        brand=brand,
        uploaded_by=user,
        source=MediaAsset.Source.AI,
        mime_type="image/png",
        width=width,
        height=height,
        size_bytes=len(raw),
        ai_prompt=prompt,
        ai_model="dall-e-3",
        cost_usd=cost,
    )
    asset.file.save(f"{asset.id}.png", ContentFile(raw), save=False)
    asset.save()
    return asset
