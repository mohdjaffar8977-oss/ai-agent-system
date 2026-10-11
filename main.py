import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from google import genai
import uvicorn

load_dotenv()

app = FastAPI()

# Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "my_secret_token_123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Gemini AI Client
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

def send_whatsapp_message(to_number: str, message_text: str):
    """WhatsApp Graph API का उपयोग करके यूज़र को मैसेज भेजने का फ़ंक्शन"""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Error: WHATSAPP_TOKEN or PHONE_NUMBER_ID is missing in .env")
        return False

    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text}
    }

    response = requests.post(url, headers=headers, json=payload)
    print(f"WhatsApp API Status: {response.status_code}, Response: {response.text}")
    return response.status_code == 200

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
        
        # स्टेटस अपडेट्स (delivered, read) को संभालना
        if "statuses" in value:
            return {"status": "success", "note": "Status update received"}

        messages = value.get("messages", [])
        if messages:
            msg_obj = messages[0]
            
            if msg_obj.get("type") == "text":
                user_message = msg_obj.get("text", {}).get("body", "")
                sender_id = msg_obj.get("from", "")
                
                if ai_client and user_message:
                    # 1. Gemini AI से जवाब जनरेट कराना
                    ai_response = ai_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=f"You are a helpful customer support AI agent for a business. Respond politely and concisely in Hindi/Hinglish: {user_message}"
                    )
                    reply_text = ai_response.text
                    
                    # 2. WhatsApp पर असली जवाब भेजना
                    send_whatsapp_message(sender_id, reply_text)
                    
                    return {
                        "status": "success",
                        "sender": sender_id,
                        "user_msg": user_message,
                        "ai_reply": reply_text
                    }
    except Exception as e:
        print(f"Error: {e}")

    return {"status": "success", "note": "Non-text message or unhandled payload"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
