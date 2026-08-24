# T-Rexx Voice Studio roadmap

This branch starts a multi-engine expansion of Voicebox while preserving upstream compatibility.

## Goal

Turn the existing local-first Voicebox studio into a broader engine-router platform that can choose among specialized TTS backends instead of forcing one model to handle every job.

## Current engine roles

| Engine | Intended role |
| --- | --- |
| Qwen3-TTS | General multilingual cloning and delivery control |
| Chatterbox | Expressive and emotional speech |
| GPT-SoVITS | Few-shot / trained custom voices |
| Fish Speech | High-quality alternative generative TTS |
| F5-TTS | Experimental and research-oriented synthesis |
| OmniVoice | Extreme multilingual coverage |
| Kokoro / LuxTTS | Lightweight / fast local generation |

## Phase 1 — GPT-SoVITS proof of concept

- [x] Create isolated development branch.
- [x] Add a Voicebox `TTSBackend` adapter for GPT-SoVITS.
- [x] Use the official GPT-SoVITS `api_v2.py` interface as a local sidecar.
- [x] Add backend contract tests.
- [ ] Register `gpt_sovits` in `TTS_ENGINES` and the backend factory.
- [ ] Add an external-model config that does not pretend the sidecar is a Hugging Face download.
- [ ] Add Settings fields for sidecar URL and prompt language.
- [ ] Add UI engine selector entry.
- [ ] Add a health/status indicator for the GPT-SoVITS sidecar.
- [ ] Run a real local generation test using a cloned voice profile.

### Why a sidecar first?

GPT-SoVITS has a substantial Python/PyTorch dependency stack. Running it as its own local API process avoids dependency conflicts with Voicebox, lets each project manage CUDA independently, and gives us a reusable pattern for future engines.

Default endpoint: `http://127.0.0.1:9880`

Override with:

```bash
VOICEBOX_GPT_SOVITS_URL=http://127.0.0.1:9880
```

Start GPT-SoVITS from its repository with:

```bash
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

## Phase 2 — Auto Engine router

Add a higher-level mode that chooses the backend based on user intent.

Candidate presets:

- `Auto`
- `DJ Drop`
- `Audiobook`
- `Emotional`
- `Voice Clone`
- `Multilingual`
- `Fast / CPU`
- `Experimental`

The router should initially be deterministic and explain its choice. Example: `DJ Drop` can prioritize Chatterbox Turbo for expressive tags, while `Voice Clone` can prioritize GPT-SoVITS when a trained/custom profile is available.

## Phase 3 — Fish Speech

Use the same adapter boundary established for GPT-SoVITS. Prefer an API/sidecar integration first so model dependencies stay isolated.

## Phase 4 — F5-TTS

Add F5-TTS as an experimental engine, with explicit model/license metadata surfaced in the UI so users understand the difference between code licensing and model-weight/data licensing.

## Phase 5 — OmniVoice and production workflows

Evaluate integration of OmniVoice capabilities that complement Voicebox, especially:

- very broad multilingual synthesis
- dubbing workflows
- speaker diarization
- vocal isolation
- batch processing

Any code reuse must be reviewed against the upstream license before incorporation.

## Product direction

The long-term UI should feel like one voice studio, not a collection of model demos. Users should be able to pick a task and let the engine router handle technical details, while advanced users retain manual engine selection.

Potential workflows include DJ drops, event/promotional narration, character voices, podcasts, audiobooks, multilingual dubbing, agent voice output, and avatar/video pipelines.
