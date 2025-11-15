# --- File 1: test_raw_requests.py ---
# Shows what happens under the hood.
# Requires: pip install requests

import json
import requests

print("--- Method 1: Raw HTTP request (requests library) ---")

# Make sure the Ollama server is running at this address
url = "http://localhost:11434/api/generate"

# This is the payload we send to the server
payload = {
    "model": "kodzero-shorts-json:latest",  # Your assistant from the Modelfile or any other model you have installed (can be checked with `ollama list`)
    "prompt": 
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
    """,
    "stream": False,  # Ask for the whole answer in one go
    "format": "json"  # Important: ask the model to return JSON-formatted output
}

response_string = None

try:
    # Send a POST request with JSON data
    raw_response = requests.post(url, json=payload, timeout=60)

    # Raise an error for HTTP problems (404, 500, etc.)
    raw_response.raise_for_status()

    # 1. Parse the JSON response from the server
    response_data = raw_response.json()

    # 2. The key 'response' contains another JSON string from your model
    response_string = response_data.get("response")

    if response_string:
        print(f"Received raw string from the assistant:\n{response_string}")

        # 3. Convert that string to a regular Python object
        parsed_payload = json.loads(response_string)

        # 4. Use the parsed data
        print("\n--- Success! Extracted title: ---")
        print(
            parsed_payload.get("title")
            or parsed_payload.get("tytul")
            or parsed_payload.get("Tytul", "No title provided")
        )

    else:
        print("Error: The 'response' key is missing in:", response_data)

except requests.exceptions.ConnectionError:
    print(f"\nERROR: Cannot reach Ollama at {url}. Is `ollama serve` running?")
except json.JSONDecodeError:
    print(f"\nERROR: Model did not return valid JSON. Received:\n{response_string}")
except Exception as e:
    print(f"Unexpected error: {e}")
