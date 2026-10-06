import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from google import genai
import uvicorn

load_dotenv()

app = FastAPI()

# Gemini AI Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "my_secret_token_123")

@app.get("/")
def home():
    return {"status": "AI Agent Webhook Server is Running"}

@app.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return Response(content=challenge, media_type="text/plain")
        else:
            return Response(status_code=403)
    return {"message": "Webhook Endpoint Ready"}

@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    
    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if messages:
            user_message = messages[0].get("text", {}).get("body", "")
            sender_id = messages[0].get("from", "")
            
            if ai_client and user_message:
                ai_response = ai_client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=f"You are a helpful customer support AI agent for a business. Respond politely and concisely in Hindi/Hinglish: {user_message}"
                )
                reply_text = ai_response.text
                
                return {
                    "status": "success",
                    "sender": sender_id,
                    "user_msg": user_message,
                    "ai_reply": reply_text
                }
    except Exception as e:
        print(f"Error: {e}")

    return {"status": "success", "note": "No direct message found or error handled"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
