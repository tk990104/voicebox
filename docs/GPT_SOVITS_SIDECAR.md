# GPT-SoVITS Sidecar Setup

T-Rexx Voice Studio integrates GPT-SoVITS as a **local sidecar process**. Voicebox stays in its own Python/runtime environment and sends synthesis requests to GPT-SoVITS over its local API v2 endpoint.

This design avoids mixing the two projects' PyTorch, CUDA, audio, and model dependencies.

## 1. Prepare GPT-SoVITS

Use the separate GPT-SoVITS checkout/fork and follow that project's installation instructions for your operating system and GPU.

The Voicebox integration expects GPT-SoVITS's `api_v2.py` entry point to be available.

## 2. Start the sidecar

From the GPT-SoVITS repository root:

```bash
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

The default Voicebox endpoint is:

```text
http://127.0.0.1:9880
```

Keep the GPT-SoVITS process running while using that engine in Voicebox.

## 3. Connect Voicebox

In Voicebox:

1. Open **Settings → Generation**.
2. Find **GPT-SoVITS sidecar**.
3. Leave the default URL at `http://127.0.0.1:9880`, or enter the address where your sidecar is listening.
4. Click **Check**.
5. Confirm the status shows **Connected**.

The URL is persisted in Voicebox's SQLite settings and is applied to standard generation, streaming generation, saved profile defaults, and agent/MCP engine bindings.

## 4. Create or choose a cloned voice

GPT-SoVITS is a sample-based engine in Voicebox.

Create a cloned voice profile with a clean reference recording and matching transcript, or edit an existing cloned profile and select **GPT-SoVITS (Local)** as its default engine.

For the first acceptance test, use one short, clean reference clip and a short synthesis sentence. This keeps failures easy to diagnose.

## 5. First acceptance test

A successful end-to-end test must prove all of the following:

- Settings health check reports **Connected**.
- GPT-SoVITS appears in the generation engine selector.
- A cloned Voicebox profile can be selected.
- Voicebox sends the profile's reference audio path and transcript to the sidecar.
- GPT-SoVITS returns WAV audio.
- Voicebox decodes, saves, and plays the generated audio.
- Generation history records engine `gpt_sovits` and model `external`.
- Retry/regenerate works for the completed/failed generation flow.
- `POST /generate/stream` works with the same configured sidecar.
- An MCP client binding can select GPT-SoVITS and use the same voice profile.

## Troubleshooting

### Status shows Offline

Confirm the GPT-SoVITS process is still running and that its host/port match the URL in **Settings → Generation**.

If you changed the port when launching `api_v2.py`, update the Voicebox URL and click **Check** again.

### Voicebox connects but synthesis fails

The connection check only proves the API process is reachable. Model/configuration problems inside GPT-SoVITS can still cause `POST /tts` to fail. Read the GPT-SoVITS process output first; Voicebox also surfaces the HTTP error returned by the sidecar.

### Reference voice sounds wrong

Use a clean reference recording with minimal background noise and a transcript that exactly matches the spoken reference. Start with one sample before testing multi-sample profiles.

## Architecture

```text
Voicebox / T-Rexx Voice Studio
        |
        | HTTP POST /tts
        v
GPT-SoVITS API v2
127.0.0.1:9880
        |
        v
GPT + SoVITS inference/model stack
```

The sidecar process owns GPT-SoVITS model loading and GPU dependencies. Voicebox owns profiles, engine routing, generation history, effects, Stories, REST/MCP integration, and the desktop UI.
