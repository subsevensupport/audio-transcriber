# Audio Transcriber

## Overview

This project implements an audio transcription service using FastAPI and Faster-Whisper. It receives audio attachments via webhook, processes them asynchronously, and saves transcription results to the data directory.

## Features

- Webhook endpoint for receiving audio attachments
- Asynchronous processing with background tasks
- Local transcription using Faster-Whisper (small model, CPU with int8 quantization)
- JSON transcription results saved to data directory
- Comprehensive error handling and logging

## Implementation Details

### Transcription

The transcription uses Faster-Whisper following best practices:

- **Model**: `small` with CPU and int8 quantization for efficiency
- **Parameters**: `beam_size=5` as recommended
- **Output**: JSON files containing:
  - Full transcription text
  - Individual segments with timestamps
  - Detected language and probability
  - Language code

### File Structure

- `main.py`: FastAPI application with webhook and transcription logic
- `requirements.txt`: Project dependencies including faster-whisper
- `data/`: Directory where audio files and transcriptions are saved

### Transcription Results

Each transcription saves a JSON file with the following structure:

```json
{
  "segments": [
    {
      "text": "Transcribed text for this segment",
      "start": 0.0,
      "end": 5.0
    }
  ],
  "full_text": "Complete transcription text",
  "language": "english",
  "language_probability": 0.99,
  "language_code": "en"
}
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

## Future Improvements

- Add GPU support with larger models
- Implement batched transcription for better performance
- Add VAD filtering for noise reduction
- Extend API to return transcription results