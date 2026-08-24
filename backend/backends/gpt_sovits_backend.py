"""GPT-SoVITS sidecar backend for Voicebox.

This adapter intentionally talks to GPT-SoVITS through its local ``api_v2.py``
HTTP API instead of importing the GPT-SoVITS inference stack into the Voicebox
Python process. Keeping the model in a sidecar avoids dependency conflicts and
lets the two projects manage their own CUDA/PyTorch requirements independently.

The sidecar is expected to run on the same machine by default:

    python api_v2.py -a 127.0.0.1 -p 9880 \
        -c GPT_SoVITS/configs/tts_infer.yaml

Set ``VOICEBOX_GPT_SOVITS_URL`` to override the default endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import soundfile as sf

from .base import combine_voice_prompts as _combine_voice_prompts

logger = logging.getLogger(__name__)

DEFAULT_GPT_SOVITS_URL = "http://127.0.0.1:9880"
DEFAULT_PROMPT_LANGUAGE = "en"


class GPTSoVITSBackend:
    """Voicebox adapter for a locally running GPT-SoVITS API v2 sidecar."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("VOICEBOX_GPT_SOVITS_URL") or DEFAULT_GPT_SOVITS_URL).rstrip("/")
        self.model_size = "external"
        self._loaded = False

    def is_loaded(self) -> bool:
        """Return whether the sidecar has passed a reachability check."""
        return self._loaded

    def _get_model_path(self, model_size: str = "external") -> str:
        """Return the external sidecar URL in place of a Hugging Face model path."""
        return self.base_url

    def _is_model_cached(self, model_size: str = "external") -> bool:
        """External GPT-SoVITS models are managed by the sidecar, not Voicebox."""
        return self._loaded

    async def load_model(self, model_size: str = "external") -> None:
        """Verify that the GPT-SoVITS sidecar is reachable.

        GPT-SoVITS owns model loading internally. Voicebox only verifies that an
        HTTP server is listening before generation starts.
        """
        if self._loaded:
            return
        await asyncio.to_thread(self._check_sidecar_sync)
        self._loaded = True

    def _check_sidecar_sync(self) -> None:
        request = urllib.request.Request(f"{self.base_url}/docs", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=3):
                return
        except urllib.error.HTTPError as exc:
            # Any non-5xx HTTP response proves the local API process is alive.
            if exc.code < 500:
                return
            raise RuntimeError(f"GPT-SoVITS sidecar returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                "GPT-SoVITS sidecar is not reachable. Start api_v2.py on "
                f"{self.base_url} or set VOICEBOX_GPT_SOVITS_URL."
            ) from exc

    def unload_model(self) -> None:
        """Forget sidecar state without terminating the external process."""
        self._loaded = False

    async def create_voice_prompt(
        self,
        audio_path: str,
        reference_text: str,
        use_cache: bool = True,
    ) -> Tuple[dict, bool]:
        """Create the lightweight prompt descriptor expected by GPT-SoVITS.

        GPT-SoVITS consumes the reference audio path at generation time, so no
        expensive prompt encoding is required in the Voicebox process.
        """
        prompt_language = os.getenv("VOICEBOX_GPT_SOVITS_PROMPT_LANG", DEFAULT_PROMPT_LANGUAGE)
        prompt = {
            "ref_audio_path": str(Path(audio_path).expanduser().resolve()),
            "prompt_text": reference_text or "",
            "prompt_lang": prompt_language,
        }
        return prompt, False

    async def combine_voice_prompts(self, audio_paths, reference_texts):
        """Preserve the shared Voicebox multi-sample prompt contract."""
        return await _combine_voice_prompts(audio_paths, reference_texts, sample_rate=24000)

    async def generate(
        self,
        text: str,
        voice_prompt: dict,
        language: str = "en",
        seed: Optional[int] = None,
        instruct: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """Generate speech through GPT-SoVITS ``POST /tts`` and return mono audio."""
        await self.load_model()

        payload = {
            "text": text,
            "text_lang": language or "auto",
            "ref_audio_path": voice_prompt["ref_audio_path"],
            "aux_ref_audio_paths": voice_prompt.get("aux_ref_audio_paths", []),
            "prompt_text": voice_prompt.get("prompt_text", ""),
            "prompt_lang": voice_prompt.get("prompt_lang", DEFAULT_PROMPT_LANGUAGE),
            "top_k": 15,
            "top_p": 1.0,
            "temperature": 1.0,
            "text_split_method": "cut5",
            "batch_size": 1,
            "speed_factor": 1.0,
            "seed": -1 if seed is None else seed,
            "media_type": "wav",
            "streaming_mode": False,
            "parallel_infer": True,
            "repetition_penalty": 1.35,
        }

        # GPT-SoVITS currently has no direct equivalent of Voicebox's generic
        # natural-language ``instruct`` field. Keep the parameter in the
        # protocol and ignore it until a mapped control is defined.
        _ = instruct

        wav_bytes = await asyncio.to_thread(self._post_tts_sync, payload)
        audio, sample_rate = sf.read(BytesIO(wav_bytes), dtype="float32", always_2d=False)
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1, dtype=np.float32)
        return audio, int(sample_rate)

    def _post_tts_sync(self, payload: dict) -> bytes:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/tts",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GPT-SoVITS generation failed (HTTP {exc.code}): {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"GPT-SoVITS generation request failed: {exc}") from exc