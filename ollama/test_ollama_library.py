# --- File 2: test_ollama_library.py ---
# Shows the same request with the official Python client.
# Requires: pip install "ollama>=0.6.1"

import json
import ollama

print("--- Method 2: Direct ollama library call (ollama>=0.6.1) ---")

model_name = "kodzero-shorts"
prompt_text = \
"""
zobaczyć wyniki czasowe pomiędzy tymi workflow'ami, jak i wyniki promptowe.
Co sądzicie?
Który według was jest lepszy i czy widać różnicę?
No bo moim zdaniem widać i to dużą.
Czy czekanie 7 minut na tę grafikę jest bardziej opłacalne niż czekanie 2-3 minuty na tę grafikę?
Dajcie znać co sądzicie w komentarzu.
Ja jestem mega ciekaw i mega zajarany tym, co te modele potrafią.
I faktycznie wygląda to realistycznie.
Ja byłem zaskoczony.
"""

response_string = None

try:
    # 1. One line to get the answer. The client handles the HTTP details for us.
    #    ollama.generate() now returns a typed GenerateResponse object that also
    #    behaves like a dict.
    result = ollama.generate(model=model_name, prompt=prompt_text, format="json")

    # 2. The 'response' field contains the model's text (here: JSON string).
    #    In 0.6.x you can access it both as an attribute and like a dict.
    response_string = result.response  # or: result["response"]

    if response_string:
        print(f"Received raw string from the assistant:\n{response_string}")

        # 3. Parse the JSON string into a Python dictionary.
        parsed_payload = json.loads(response_string)

        # 4. Use the data.
        print("\n--- Success! Extracted title: ---")
        print(
            parsed_payload.get("title")
            or parsed_payload.get("tytul")
            or parsed_payload.get("Tytul", "No title provided")
        )

    else:
        print("Error: 'response' field was empty in:", result)

except ollama.ResponseError as e:
    # Newer ollama versions expose both `e.error` and `e.status_code`.
    print(f"\nERROR from Ollama server: {e.error} (status code: {e.status_code})")

    # 404 is the idiomatic "model not found" signal now.
    if e.status_code == 404:
        print(f"Double-check that the model '{model_name}' is installed.")
        print(f"Example:  ollama pull {model_name}")

except json.JSONDecodeError:
    print(f"\nERROR: Model did not return valid JSON. Received:\n{response_string}")

except Exception as e:
    # Helpful when the local server is down or other unexpected issues occur.
    print(f"Unexpected error (is Ollama running?): {e}")