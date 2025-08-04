import logging
import os
from typing import List, Optional

import aiohttp
from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from faster_whisper import WhisperModel
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)


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


async def download_audio_file(attachment: Attachment) -> str:
    """
    Downloads an audio file from a URL and saves it to the data directory.

    Args:
        attachment: The audio attachment containing the URL

    Returns:
        str: Path to the saved audio file

    Raises:
        HTTPException: If the download fails
    """
    try:
        local_filename = os.path.join("data", f"{attachment.id}_{attachment.filename}")

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(attachment.url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to download audio file: HTTP {response.status}",
                    )
                    # TODO: troubleshoot 403 errors on some attachments

                with open(local_filename, "wb") as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)

        logger.info(f"Successfully downloaded audio file: {local_filename}")
        return local_filename

    except Exception as e:
        logger.error(f"Failed to download audio file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download audio file: {str(e)}",
        )


async def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribes an audio file using Faster-Whisper following best practices.

    Args:
        audio_path: Path to the audio file to transcribe

    Returns:
        dict: Transcription results with segments and text

    Raises:
        HTTPException: If transcription fails
    """
    try:
        model = WhisperModel("distil-large-v3", device="cpu", compute_type="float32")

        logger.info(f"Starting transcription for: {audio_path}")

        segments, info = model.transcribe(audio_path, beam_size=5)

        segments_list = list(
            segments
        )  # converts generator to list, which runs the transcription

        full_text_list = [segment.text for segment in segments_list]

        transcription = {
            "segments": segments_list,
            "info": info,
            "full_text": " ".join(full_text_list).strip(),
        }

        logger.info(f"Transcription completed for: {audio_path}")
        return transcription

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


async def process_audio_attachment(attachment: Attachment):
    """
    Background task to process an audio attachment.

    Args:
        attachment: The audio attachment to process
    """
    logger.info(f"Processing audio attachment: {attachment.filename}")

    try:
        audio_path = await download_audio_file(attachment)
        logger.info(f"Audio file saved to: {audio_path}")

        transcription = await transcribe_audio(audio_path)

        transcription_filename = os.path.join(
            "data",
            f"{attachment.id}_{os.path.splitext(attachment.filename)[0]}_transcription.txt",
        )

        with open(transcription_filename, "w", encoding="utf-8") as f:
            f.write(transcription["full_text"])

        logger.info(f"Transcription saved to: {transcription_filename}")

    except HTTPException as e:
        logger.error(f"Error processing audio attachment: {e.detail}")

    logger.info(f"Finished processing audio attachment: {attachment.filename}")

    os.remove(audio_path)

    return transcription["full_text"]


@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(
    payload: MissiveWebhook, background_tasks: BackgroundTasks
) -> dict:
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
        logger.error("No latest message found in payload")
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="No message found. Nothing to process.",
        )
        # TODO: send an error message back to missive for these 204 codes

    attachments = payload.latest_message.attachments
    if not attachments:
        logger.error("No attachments found on latest message")
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="No attachments found on latest message. Nothing to process.",
        )

    audio_attachments = [a for a in attachments if a.media_type == "audio"]

    if not audio_attachments:
        logger.error("No audio attachments found in the message")
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="No audio attachments found. Nothing to transcribe.",
        )

    logger.info(
        f"{len(audio_attachments)} audio attachment(s) found. Sending for transcription..."
    )

    for attachment in audio_attachments:
        background_tasks.add_task(process_audio_attachment, attachment)

    return {
        "status": "success",
        "message": f"Found {len(audio_attachments)} audio attachments. Sent for transcription.",
    }
