import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
import uvicorn

load_dotenv()

app = FastAPI()

# Meta Webhook का Secret Token (इसे .env में भी रख सकते हैं)
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "my_secret_token_123")

@app.get("/")
def home():
    return {"status": "AI Agent Webhook Server is Running"}

# Meta Verification (GET)
@app.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return Response(content=challenge, media_type="text/plain")
        else:
            return Response(status_code=403)
    return {"message": "Webhook Endpoint Ready"}

# Incoming Messages (POST)
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    print("Received Message:", data)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
