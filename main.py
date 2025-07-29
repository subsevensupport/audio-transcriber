from fastapi import FastAPI, Request
import json
from pydantic import BaseModel
from typing import List, Optional

class Attachment(BaseModel):
    id: str
    filename: str
    extension: str
    url: str
    media_type: str
    sub_type: str
    size: int

class LatestMessage(BaseModel):
    type: str
    attachments: List[Attachment]

class Conversation(BaseModel):
    id: str
    messages_count: int
    attachments_count: int

class MissiveWebhook(BaseModel):
    conversation: Conversation
    latest_message: LatestMessage

app = FastAPI()

@app.post('/webhook')
async def receive_webhook(payload: MissiveWebhook):
    """
    Receives webhook from Missive and validates the data with Pydantic models.
    """

    print("--- Webhook Received and Validated ---")
    print(f"attachment type is: {payload.latest_message.attachments[0].media_type}")    
    print("----------------------")

    return {"status": "success", "message": "webhook received"}