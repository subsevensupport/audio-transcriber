from fastapi import FastAPI, Request

app = FastAPI()

@app.post('/webhook')
async def receive_webhook(request: Request):
    """
    Receives webhook from Missive.
    """
    payload = await request.json()

    print("--- Webhook Received ---")
    print(payload)
    print("----------------------")

    return {"status": "success", "message": "webhook received"}