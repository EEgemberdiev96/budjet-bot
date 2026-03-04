import io
from groq import AsyncGroq
from app.config import GROQ_API_KEY

client = AsyncGroq(api_key=GROQ_API_KEY)


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    transcription = await client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-large-v3",
        language="ru",
    )
    return transcription.text
