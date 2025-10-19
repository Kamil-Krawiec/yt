## Ollama Model Reference

You can fetch models into Ollama either through the HTTP API (great for scripts and CI) or via the CLI (quick and human friendly). Both methods use the same local model store inside the `ollama` volume.

### Pull via HTTP API (curl)

- Endpoint: `POST http://localhost:11434/api/pull`
- Body JSON: `{ "model": "<name>:<tag>", "stream": false }`
- Tip: set `"stream": false` to receive a single JSON response when the pull completes.

#### Example requests

DeepSeek-R1 7B (English reasoning, compact quant around 4.7-5.2 GB):

```bash
curl -s http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-r1:7b", "stream": false}'
```

OpenEuroLLM (Polish, Gemma-based):

```bash
curl -s http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"model":"jobautomation/OpenEuroLLM-Polish:latest", "stream": false}'
```

Bielik 7B Instruct (Polish). Works only if the model is published in the Ollama Library under this exact name; otherwise use a Modelfile (see below):

```bash
curl -s http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"model":"SpeakLeash/bielik-7b-instruct-v0.1-gguf:Q4_K_S", "stream": false}'
```

Qwen 2.5 7B Instruct (general assistant):

```bash
curl -s http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:7b-instruct-q4_K_M", "stream": false}'
```

Llama 3.1 8B Instruct (Q4_K_M):

```bash
curl -s http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.1:8b-instruct-q4_K_M", "stream": false}'
```

Gemma 2 9B Instruct (Q4_K_M):

```bash
curl -s http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma2:9b-instruct-q4_K_M", "stream": false}'
```

### Pull via CLI (`ollama pull`)

```bash
ollama pull deepseek-r1:7b
ollama pull jobautomation/OpenEuroLLM-Polish:latest
ollama pull SpeakLeash/bielik-7b-instruct-v0.1-gguf:Q4_K_S
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull llama3.1:8b-instruct-q4_K_M
ollama pull gemma2:9b-instruct-q4_K_M
```

### Day-to-day commands

- List installed models:

  ```bash
  ollama list
  ```

- Show model details (size, template, system prompt, etc.):

  ```bash
  ollama show <model>
  ```

- Stop a running model and free RAM:

  ```bash
  ollama stop <model>
  ```

### Notes and tips

- Suffixes like `q4_K_M` refer to K-quants, which usually beat legacy `q4_0` and `q4_1` quantizations at the same size.
- `instruct` tags indicate models tuned for chat and instruction following.
- On 16 GB RAM, start with 7B `q4_K_M`. If quality is lacking, try Q5; if memory is tight, reduce `num_ctx` first.
- Control model lifetime with the `KEEP_ALIVE` setting (global `OLLAMA_KEEP_ALIVE` env variable or per-request `keep_alive`):
  - Accepts duration strings such as `"10m"` or `"24h"`, or integers in seconds.
  - `0` unloads the model immediately after the request.
  - Negative values (for example `-1`) keep the model loaded until you stop it manually.

### Handy links

- Model search: https://ollama.com/search
- API reference: `POST /api/pull` (default Docker mapping: `127.0.0.1:11434`)
