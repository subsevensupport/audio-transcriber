import logging
from tempfile import NamedTemporaryFile

import httpx
from beam import Image, Volume, env, task_queue

if env.is_remote():
    from faster_whisper import WhisperModel, download_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)

BEAM_VOLUME_PATH = "./cached_models"


def load_models():
    model_path = download_model("distil-large-v3", cache_dir=BEAM_VOLUME_PATH)
    model = WhisperModel(model_path, device="cuda", compute_type="float32")
    return model


@task_queue(
    on_start=load_models,
    name="audio-transcriber",
    cpu=2,
    memory="2Gi",
    gpu="T4",
    image=Image(
        base_image="nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04",
        python_version="python3.12",
    ).add_python_packages(["faster-whisper==1.1.1", "aiohttp==3.12.15"]),
    volumes=[
        Volume(
            name="cached_models",
            mount_path=BEAM_VOLUME_PATH,
        )
    ],
    callback_url="https://0700e66112a8.ngrok-free.app/transcribe-callback",
)
def transcribe(context, audio_file_url, callback_data):
    model = context.on_start_value

    try:
        response = httpx.get(audio_file_url)
        response.raise_for_status()
        logger.info("Audio file downloaded")
    except httpx.HTTPStatusError as e:
        logger.error(
            "Failed to download audio file."
            f"Status code: {e.response.status_code}. Response: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while downloading audio file: {e}")

    text = ""

    with NamedTemporaryFile() as temp:
        try:
            temp.write(response.content)
            temp.flush()

            segments, _ = model.transcribe(temp.name, beam_size=5, language="en")
            for segment in segments:
                text += segment.text + " "

            text = text.strip()

            logger.info("Audio file transcribed successfully.")
            return {"transcription_text": text, "callback_data": callback_data}
        except Exception as e:
            logger.error(f"Error transcribing audio file. Error: {e}")
            return {"error": {e}}
