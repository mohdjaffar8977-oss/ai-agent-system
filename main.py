import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException
from google import genai
from google.genai import types
import uvicorn
from db import get_client_by_id, get_client_by_phone_number_id, get_connection, save_message, is_ai_paused, pause_client_ai, is_client_ai_paused, get_recent_messages, add_to_human_queue, message_already_seen
from safety import is_sensitive_message, reply_problem

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
if not VERIFY_TOKEN:
    raise RuntimeError("WEBHOOK_VERIFY_TOKEN missing in .env file")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

def send_whatsapp_message(phone_number_id: str, whatsapp_token: str, to_number: str, message_text: str):
    if not whatsapp_token or not phone_number_id:
        print("[LOG] Token or Phone Number ID missing. Skipping live WhatsApp send.")
        return False

    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"WhatsApp API Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"WhatsApp API Send Error: {e}")
        return False

def generate_ai_reply(client_data: dict, user_message: str, history=None) -> str:
    if not ai_client:
        return "माफ़ कीजिए, हमारी AI सेवा अभी उपलब्ध नहीं है।"

    system_prompt = client_data.get("system_prompt", "You are a helpful customer support AI agent for a business. Respond politely and concisely in Hindi/Hinglish.")
    contents = user_message
    if history:
        turns = list(history)
        while turns and turns[0][0] != "user":
            turns.pop(0)
        if turns:
            contents = [types.Content(role="user" if r == "user" else "model", parts=[types.Part(text=t)]) for r, t in turns]
    
    try:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3
        )
        response = ai_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

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
        
        if "statuses" in value:
            return {"status": "success", "note": "Status update received"}

        messages = value.get("messages", [])
        if not messages:
            return {"status": "success", "note": "No message payload"}

        msg_obj = messages[0]
        
        if msg_obj.get("type") != "text":
            return {"status": "success", "note": "Non-text message ignored"}

        user_message = msg_obj.get("text", {}).get("body", "").strip()
        customer_number = msg_obj.get("from", "")
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")

        if not user_message or not customer_number or not phone_number_id:
            return {"status": "error", "message": "Incomplete payload details"}

        client_data = get_client_by_phone_number_id(phone_number_id)
        if not client_data:
            print(f"[LOG] Client not found for phone_number_id: {phone_number_id}")
            return {"status": "error", "message": "Client not registered"}

        client_id = client_data["client_id"]

        wa_message_id = msg_obj.get("id")
        if message_already_seen(client_id, wa_message_id):
            print(f"[LOG] Duplicate message ignored: {wa_message_id}")
            return {"status": "success", "note": "Duplicate message ignored"}

        save_message(client_id, customer_number, "user", user_message, wa_message_id)
        if is_ai_paused(client_id, customer_number):
            print(f"[LOG] AI is currently paused for customer {customer_number}.")
            add_to_human_queue(client_id, customer_number, "customer_paused")
            return {"status": "success", "note": "AI is paused for this customer"}
        if is_client_ai_paused(client_id):
            print(f"[LOG] AI paused for client {client_id} due to Gemini error.")
            add_to_human_queue(client_id, customer_number, "client_paused")
            return {"status": "success", "note": "AI paused for client due to error"}
        if is_sensitive_message(user_message):
            print(f"[LOG] Sensitive message from {customer_number}. AI silent, needs human.")
            add_to_human_queue(client_id, customer_number, "sensitive")
            return {"status": "success", "note": "Sensitive message, needs human"}


        ai_reply = generate_ai_reply(client_data, user_message, get_recent_messages(client_id, customer_number))
        if ai_reply is None:
            print(f"[LOG] Gemini failed for client {client_id}. AI paused for 5 minutes.")
            add_to_human_queue(client_id, customer_number, "gemini_error")
            pause_client_ai(client_id, 5)
            return {"status": "success", "note": "AI error, no reply sent"}
        problem = reply_problem(ai_reply, client_data["system_prompt"])
        if problem:
            print(f"[LOG] Reply blocked ({problem}) for {customer_number}. Needs human.")
            add_to_human_queue(client_id, customer_number, problem)
            return {"status": "success", "note": "Reply blocked, needs human"}

        save_message(client_id, customer_number, "assistant", ai_reply)

        whatsapp_token = client_data.get("whatsapp_token") or WHATSAPP_TOKEN
        send_whatsapp_message(phone_number_id, whatsapp_token, customer_number, ai_reply)

        return {
            "status": "success",
            "client_id": client_id,
            "sender": customer_number,
            "ai_reply": ai_reply
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": "Internal error processing payload"}

@app.post("/test-webhook")
async def test_webhook_handler(request: Request):
    if not DEBUG_MODE:
        raise HTTPException(status_code=404, detail="Test endpoint disabled in production")

    data = await request.json()
    client_id = data.get("client_id")
    customer_number = data.get("customer_number")
    user_message = data.get("message")
    
    if not client_id or not customer_number or not user_message:
        return {"status": "error", "message": "Missing fields"}
    
    client_data = get_client_by_id(client_id)
    if not client_data:
        return {"status": "error", "message": "Client not found"}
    
    ai_reply = generate_ai_reply(client_data, user_message)
    save_message(client_id, customer_number, "user", user_message)
    save_message(client_id, customer_number, "assistant", ai_reply)
    
    return {
        "status": "success",
        "client_name": client_data.get("name"),
        "ai_reply": ai_reply
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
