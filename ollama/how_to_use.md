# How to use these examples

Quick checklist to make the scripts inside this folder work.

## 1. Install and start Ollama
- Make sure you have ollama running if you don't check [THIS](../GPT/docker-compose.yaml) docker compose with ollama image in it 

## 2. Install Python dependencies
```bash
pip install requests ollama
```
Both scripts were tested with Python 3.10+, but any modern Python 3 version should be fine.

## 3. Run the examples
- `python test_raw_requests.py` — shows the raw HTTP call using the `requests` package.
- `python test_ollama_library.py` — same prompt sent through the official `ollama` Python client.

Each script prints the JSON string returned by your model and then tries to read the `title` field. Edit the `prompt_text` or `prompt` variable to send whatever text you want.

## 4. Troubleshooting tips
- **Connection error**: Ensure `ollama serve` is still running. The server must be on `localhost:11434` unless you change the URL in `test_raw_requests.py`.
- **Model not found**: Pull or create the model name you set in `model_name`/`model` (for example, `ollama pull llama3` or use your custom Modelfile and `ollama create`).
- **Invalid JSON**: Adjust your prompt or model so it returns valid JSON. Until then, wrap the parsing logic in a `try/except` block (already done in both scripts).
