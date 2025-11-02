## My copy paste commands :p
```bash
docker cp Modelfile ollama:/root/Modelfile
docker exec -it ollama ollama rm kodzero-shorts || true 
docker exec -it ollama ollama create kodzero-shorts -f /root/Modelfile
```
# yt-shorts-automation — Ollama assistant

This short guide shows how to (re)deploy an Ollama model instance inside a running Docker container named `ollama`.

## Prerequisites

- Docker installed and running.
- A running container named `ollama` (adjust the container name in commands if yours differs).
- A `Modelfile` prepared locally (see the example below).

## Quick steps

1) Copy the `Modelfile` to the Ollama container

```bash
docker cp Modelfile ollama:/root/Modelfile
```

2) Remove any existing instance with the same name (safe to run even if it doesn't exist)

```bash
docker exec -it ollama ollama rm kodzero-shorts || true
```

3) Create a new instance from the Modelfile

```bash
docker exec -it ollama ollama create kodzero-shorts -f /root/Modelfile
```

## Example Modelfile

Below is an example `Modelfile`. Put this content in a local file named `Modelfile` and edit the placeholders for your model image, paths, and runtime options. This is a generic example to illustrate common fields — adapt it to your model packaging or Ollama requirements.

```text
FROM llama3.1:8b-instruct-q4_K_M

# Conservative decoding for consistent, structured output
PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.05
PARAMETER num_predict 800
PARAMETER num_ctx 8192

SYSTEM """
YouTube Assistant "Kod Zero" — SYSTEM PROMPT

You are the assistant for the YouTube channel "Kod Zero".
You will receive {TRANSKRYPT} (raw .txt content) and OPTIONAL {FILE_NAME} (filename context, e.g., "homelab_06_comfyui_cpu.txt").
Use both to infer topic, tools, episode number, brand/model names. Do not echo {FILE_NAME} verbatim.
Return ONLY the five sections below, in this exact order, and in Polish.
Do NOT add commentary or explanations. Do NOT wrap the output in code fences. Do NOT echo inputs.

Sections to output (exact order):
[Tytul]
[Opis]
[Tagi]
[Kiedy]
[Miniaturka]
"""
```

## Tips & troubleshooting

- If your container isn't named `ollama`, replace `ollama` in the commands with your container name or container id.
- Confirm the file arrived inside the container:

```bash
docker exec -it ollama ls -l /root/Modelfile
```

- If `ollama create` fails, inspect container logs and the Ollama CLI output for reasons (missing image, permission, or format issues).

## Short summary

1. Edit your `Modelfile` (use the example above as a starting point).
2. Copy it into the container.
3. Remove the old model instance (if present) and create the new one.