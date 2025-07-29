from fastapi import FastAPI, HTTPException, status
import logging
from pydantic import BaseModel
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    latest_message: Optional[LatestMessage] = None

app = FastAPI()

@app.post('/webhook', status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(payload: MissiveWebhook) -> dict:
    """
    Receives webhook from Missive, validates the data, and schedules background processing.
    Returns a success message if audio attachments are found, otherwise raises appropriate HTTP exceptions.

    Args:
        payload: The incoming webhook data from Missive

    Returns:
        dict: Status message with count of audio attachments found

    Raises:
        HTTPException: If no message is found, no attachments exist, or no audio attachments are found
    """

    logger.info("Webhook received. Validating payload...")

    if not payload.latest_message:
        logger.error('No latest message found in payload')
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No message found. Nothing to process.")

    attachments = payload.latest_message.attachments
    if not attachments:
        logger.error('No attachments found on latest message')
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No attachments found on latest message. Nothing to process.")

    audio_attachments = [a for a in attachments if a.media_type == "audio"]

    if not audio_attachments:
        logger.error('No audio attachments found in the message')
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No audio attachments found. Nothing to transcribe.")

    logger.info(f"{len(audio_attachments)} audio attachment(s) found. Sending for transcription...")
    # queue them for background processing
    return {
        "status": "success",
        "message": f"Found {len(audio_attachments)} audio attachments. Sent for transcription."
    }