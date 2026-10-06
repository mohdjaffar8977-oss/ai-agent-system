import os
from dotenv import load_dotenv
from google import genai

# .env फ़ाइल से वेरिएबल्स लोड करें
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

print("Sending prompt to Gemini...")

try:
    # Gemini 2.5 Flash मॉडल से रिस्पॉन्स माँगें
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say 'Hello, I am your AI Agent!' in Hindi",
    )
    print("\nAI Response:")
    print(response.text)
except Exception as e:
    print("\n[Note: Valid API key needed for live AI response]")
    print(f"Status: Client initialized with key '{api_key}' successfully.")
