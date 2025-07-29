from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.post('/webhook')
async def receive_webhook(request: Request):
    """
    Receives webhook from Missive.
    """
    payload = await request.json()

    print("--- Webhook Received ---")
    print("Saving payload for inspection...")
    with open("sample_payload.json", mode="w") as file:
        json.dump(payload, file, indent=4)    
    print("----------------------")

    return {"status": "success", "message": "webhook received"}