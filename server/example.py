import requests
import threading
import sys
import time
import itertools

url = "http://localhost:8000/v1/tts"

# The keys must perfectly match the Pydantic schema in your server (text and description)
payload = {
    "text": "जातः कंसवधार्थाय भूभारोत्तरणाय च",
    # "text": "जातः कंसवधार्थाय भूभारोत्तरणाय च। कौरवाणां विनाशाय दैत्यानां निधनाय च॥ पाण्डवानां हितार्थाय धर्मसंस्थापनाय च। गृहाणार्घ्यं मया दत्तं देवक्या सहितो हरे॥",
    "description": "anushtubh"
}

import math

done = False

def animate_spinner():
    start_time = time.time()
    # Rough estimate for CPU generation (~0.5s per character for 16 NFE steps)
    estimated_total_seconds = len(payload["text"]) * 0.5
    if estimated_total_seconds < 5:
        estimated_total_seconds = 5
        
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if done:
            break
        elapsed = time.time() - start_time
        # Asymptotic progress curve that approaches 99.9% based on the estimated time
        progress = 100 * (1 - math.exp(-elapsed / (estimated_total_seconds * 0.6)))
        if progress > 99.9:
            progress = 99.9
            
        sys.stdout.write(f'\rGenerating audio on CPU... {progress:.1f}% {c} ')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * 75 + '\r') # Clear the line

print("Sending request to TTS server...")

# Start the spinner in a separate thread
spinner_thread = threading.Thread(target=animate_spinner)
spinner_thread.start()

try:
    # CRITICAL: Use json=payload to properly format it as an application/json request body
    response = requests.post(url, json=payload)
    done = True
    spinner_thread.join()

    if response.status_code == 200:
        with open("output.mp3", "wb") as f:
            f.write(response.content)
        print("Audio successfully saved to output.mp3")
    else:
        print(f"Error {response.status_code}: {response.text}")
except Exception as e:
    done = True
    spinner_thread.join()
    print(f"\nRequest failed: {e}")
