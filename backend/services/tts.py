import os
import re
import logging
import asyncio
import subprocess

logger = logging.getLogger(__name__)

# Map target languages to Microsoft Edge TTS neural voices
# These are high-quality, human-sounding neural voices
EDGE_TTS_VOICES = {
    "Tamil":     "ta-IN-ValluvarNeural",
    "Telugu":    "te-IN-ShrutiNeural",
    "Malayalam": "ml-IN-SobhanaNeural",
    "Kannada":   "kn-IN-GaganNeural",
    "Hindi":     "hi-IN-SwaraNeural",
    "English":   "en-US-AriaNeural",
}

DEFAULT_VOICE = "en-US-AriaNeural"

# Tamil number words (0-19 + tens)
TAMIL_ONES = [
    "சுழியம்", "ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து",
    "ஆறு", "ஏழு", "எட்டு", "ஒன்பது", "பத்து", "பதினொன்று",
    "பன்னிரண்டு", "பதிமூன்று", "பதினான்கு", "பதினைந்து",
    "பதினாறு", "பதினேழு", "பதினெட்டு", "பத்தொன்பது"
]
TAMIL_TENS = ["", "", "இருபது", "முப்பது", "நாற்பது", "ஐம்பது",
              "அறுபது", "எழுபது", "எண்பது", "தொண்ணூறு"]


def _int_to_tamil(n: int) -> str:
    """Convert an integer (0–9999) to Tamil words."""
    if n < 0:
        return "கழித்தல் " + _int_to_tamil(-n)
    if n < 20:
        return TAMIL_ONES[n]
    if n < 100:
        tens = TAMIL_TENS[n // 10]
        ones = ("" if n % 10 == 0 else " " + TAMIL_ONES[n % 10])
        return tens + ones
    if n < 1000:
        hundreds = TAMIL_ONES[n // 100] + " நூறு"
        rest = ("" if n % 100 == 0 else " " + _int_to_tamil(n % 100))
        return hundreds + rest
    if n < 10000:
        thousands = TAMIL_ONES[n // 1000] + " ஆயிரம்"
        rest = ("" if n % 1000 == 0 else " " + _int_to_tamil(n % 1000))
        return thousands + rest
    return str(n)


def _preprocess_text(text: str, target_language: str) -> str:
    """
    Clean up text before sending to Edge TTS:
    - Convert numbers to words for Tamil/Hindi
    - Remove symbols that TTS reads awkwardly
    - Normalize whitespace
    """
    text = text.replace("%", " சதவீதம் " if target_language == "Tamil" else " percent ")
    text = text.replace("$", " டாலர் " if target_language == "Tamil" else " dollar ")
    text = text.replace("&", " மற்றும் " if target_language == "Tamil" else " and ")
    text = text.replace("#", "")
    text = text.replace("@", "")

    # Replace ellipsis / dashes with a natural pause
    text = re.sub(r"\.{2,}", ",", text)
    text = re.sub(r"[-–—]+", ", ", text)

    # Convert numerals for Tamil
    if target_language == "Tamil":
        def replace_number(m):
            try:
                return _int_to_tamil(int(m.group(0).replace(",", "")))
            except ValueError:
                return m.group(0)
        text = re.sub(r"\d[\d,]*", replace_number, text)
    elif target_language == "Hindi":
        devanagari_digits = "०१२३४५६७८९"
        text = re.sub(r"\d", lambda m: devanagari_digits[int(m.group(0))], text)

    # Remove stray punctuation
    text = re.sub(r"[|\\^`~<>{}[\]()_]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _generate_silence(output_path: str, duration: float = 0.1) -> None:
    """Generate a short silent MP3 file using FFmpeg."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration), "-c:a", "libmp3lame", output_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def generate_chunk_audio(text: str, output_path: str, target_language: str) -> str:
    """
    Generates a single speech audio file using Microsoft Azure Speech (if configured),
    falling back to Microsoft Edge TTS, and finally gTTS.
    """
    if not text.strip():
        logger.info(f"Empty segment — generating silence: {output_path}")
        await asyncio.to_thread(_generate_silence, output_path)
        return output_path

    clean_text = _preprocess_text(text, target_language)
    if not clean_text.strip():
        logger.info(f"Text empty after cleaning — generating silence: {output_path}")
        await asyncio.to_thread(_generate_silence, output_path)
        return output_path

    voice = EDGE_TTS_VOICES.get(target_language, DEFAULT_VOICE)

    # 1. Try Azure Speech if configured
    from backend.config import settings
    if settings.is_azure_configured:
        logger.info(f"Azure TTS: voice='{voice}', text preview: {clean_text[:60]!r}")
        try:
            import urllib.request
            import urllib.error
            import xml.sax.saxutils

            voice_parts = voice.split("-")
            lang_code = "-".join(voice_parts[:2]) if len(voice_parts) >= 2 else "en-US"
            escaped_text = xml.sax.saxutils.escape(clean_text)
            ssml = f"<speak version='1.0' xml:lang='{lang_code}'><voice xml:lang='{lang_code}' name='{voice}'>{escaped_text}</voice></speak>"

            url = f"https://{settings.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
            headers = {
                "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "AIDubber"
            }

            def _call_azure():
                req = urllib.request.Request(url, data=ssml.encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req) as response:
                    with open(output_path, "wb") as f:
                        f.write(response.read())

            await asyncio.to_thread(_call_azure)
            logger.info(f"Azure TTS succeeded: {output_path}")
            return output_path
        except Exception as azure_err:
            logger.warning(f"Azure TTS failed ({azure_err}). Falling back to Edge TTS...")

    # 2. Try Edge TTS
    logger.info(f"Edge TTS: voice='{voice}', text preview: {clean_text[:60]!r}")
    try:
        import edge_tts
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(output_path)
        logger.info(f"Edge TTS succeeded: {output_path}")
        return output_path
    except Exception as e:
        logger.warning(f"Edge TTS failed ({e}), falling back to gTTS...")
        try:
            from gtts import gTTS
            # gTTS lang code is the 2-letter prefix (e.g. "ta" from "ta-IN")
            lang_code = voice.split("-")[0]
            tts = gTTS(text=clean_text, lang=lang_code)
            await asyncio.to_thread(tts.save, output_path)
            logger.info(f"gTTS fallback succeeded: {output_path}")
            return output_path
        except Exception as fallback_err:
            logger.error(f"Both Edge TTS and gTTS failed: {fallback_err}")
            # Generate silence rather than crashing the whole pipeline
            await asyncio.to_thread(_generate_silence, output_path, 0.5)
            return output_path


async def generate_all_tts_chunks(
    translated_segments: list[dict],
    output_dir: str,
    target_language: str
) -> list[str]:
    """
    Generates audio files for all translated segments concurrently using Edge TTS.

    Args:
        translated_segments: List of segments with keys 'start', 'end', 'text'.
        output_dir: Directory where chunk files will be saved.
        target_language: Target language name (e.g. 'Tamil').

    Returns:
        List of paths to the generated chunk audio files.
    """
    os.makedirs(output_dir, exist_ok=True)
    chunk_paths = []
    tasks = []

    logger.info(f"Generating Edge TTS audio for {len(translated_segments)} segments concurrently...")

    for i, seg in enumerate(translated_segments):
        chunk_file = os.path.join(output_dir, f"chunk_{i}.mp3")
        chunk_paths.append(chunk_file)
        tasks.append(generate_chunk_audio(seg["text"], chunk_file, target_language))

    await asyncio.gather(*tasks)
    logger.info("All TTS chunks generated successfully.")
    return chunk_paths
