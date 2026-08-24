from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from backend.backends.gpt_sovits_backend import GPTSoVITSBackend


@pytest.mark.asyncio
async def test_create_voice_prompt_uses_absolute_path(tmp_path):
    sample = tmp_path / "voice.wav"
    sample.write_bytes(b"test")

    backend = GPTSoVITSBackend("http://127.0.0.1:9880")
    prompt, was_cached = await backend.create_voice_prompt(str(sample), "reference words")

    assert prompt["ref_audio_path"] == str(sample.resolve())
    assert prompt["prompt_text"] == "reference words"
    assert prompt["prompt_lang"] == "en"
    assert was_cached is False


@pytest.mark.asyncio
async def test_load_model_marks_sidecar_loaded_after_health_check():
    backend = GPTSoVITSBackend("http://127.0.0.1:9880")

    with patch.object(backend, "_check_sidecar_sync", return_value=None):
        await backend.load_model()

    assert backend.is_loaded() is True


def test_unload_model_does_not_terminate_sidecar():
    backend = GPTSoVITSBackend("http://127.0.0.1:9880")
    backend._loaded = True

    backend.unload_model()

    assert backend.is_loaded() is False


def test_set_base_url_invalidates_previous_health_state():
    backend = GPTSoVITSBackend("http://127.0.0.1:9880")
    backend._loaded = True

    backend.set_base_url("http://localhost:9881/")

    assert backend.base_url == "http://localhost:9881"
    assert backend.is_loaded() is False


@pytest.mark.asyncio
async def test_generate_decodes_wav_response(monkeypatch):
    import io
    import soundfile as sf

    backend = GPTSoVITSBackend("http://127.0.0.1:9880")
    backend._loaded = True

    source = np.array([0.0, 0.25, -0.25, 0.0], dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, source, 32000, format="WAV")

    with patch.object(backend, "_post_tts_sync", return_value=buf.getvalue()):
        audio, sample_rate = await backend.generate(
            "hello",
            {
                "ref_audio_path": "/tmp/ref.wav",
                "prompt_text": "hello there",
                "prompt_lang": "en",
            },
            language="en",
            seed=42,
        )

    assert sample_rate == 32000
    assert audio.dtype == np.float32
    assert audio.ndim == 1
    assert len(audio) == len(source)
