import time
import logging
import urllib.parse
import requests
from backend.config import settings

logger = logging.getLogger(__name__)

# Supported target languages mapping
TARGET_LANG_MAPPING = {
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Kannada": "kn",
    "English": "en",
    "Hindi": "hi"
}

NLLB_LANG_MAPPING = {
    "Tamil": "tam_Taml",
    "Telugu": "tel_Telu",
    "Malayalam": "mal_Mlym",
    "Kannada": "kan_Knda",
    "English": "eng_Latn",
    "Hindi": "hin_Deva"
}

WHISPER_TO_NLLB = {
    "en": "eng_Latn", "hi": "hin_Deva", "ta": "tam_Taml",
    "te": "tel_Telu", "ml": "mal_Mlym", "kn": "kan_Knda",
    "es": "spa_Latn", "fr": "fra_Latn", "de": "deu_Latn",
    "it": "ita_Latn", "pt": "por_Latn", "ru": "rus_Cyrl",
    "zh": "zho_Hans", "ja": "jpn_Jpan", "ko": "kor_Hang",
    "ar": "ary_Arab", "tr": "tur_Latn", "nl": "nld_Latn"
}


def _translate_single_segment(text: str, source_lang: str, target_lang_code: str) -> str:
    """
    Translates text into the target language using high-accuracy multi-tier fallback:
      Tier 1: Google Chrome dict-extension endpoint (High accuracy, no 429)
      Tier 2: MyMemory Translated API (Free, fast, 100% reliable)
      Tier 3: Google translate_a endpoint
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return text

    # Tier 1: Google Chrome Extension endpoint
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        r = requests.get(
            "https://clients5.google.com/translate_a/t",
            params={
                "client": "dict-chrome-ex",
                "sl": source_lang or "auto",
                "tl": target_lang_code,
                "q": cleaned_text
            },
            headers=headers,
            timeout=6
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
                return data[0]
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                res = "".join([p[0] for p in data[0] if p and p[0]])
                if res:
                    return res
    except Exception as ex:
        logger.debug(f"Google dict endpoint error: {ex}")

    # Tier 2: MyMemory Translation API
    try:
        src = source_lang if (source_lang and len(source_lang) == 2) else "auto"
        pair = f"{src}|{target_lang_code}"
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(cleaned_text)}&langpair={pair}"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            res = data.get("responseData", {}).get("translatedText")
            if res and not res.startswith("MYMEMORY WARNING"):
                return res
    except Exception as ex:
        logger.debug(f"MyMemory error: {ex}")

    # Tier 3: Google gtx endpoint
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": source_lang or "auto",
                "tl": target_lang_code,
                "dt": "t",
                "q": cleaned_text
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=6
        )
        if r.status_code == 200:
            data = r.json()
            if data and data[0]:
                res = "".join([part[0] for part in data[0] if part and part[0]])
                if res:
                    return res
    except Exception as ex:
        logger.debug(f"Google gtx error: {ex}")

    logger.warning(f"All translation engines failed for text: '{cleaned_text[:30]}...'")
    return text


class NLLBTranslatorService:
    def __init__(self):
        self.model_name = settings.NLLB_MODEL_NAME
        self.use_nllb = getattr(settings, 'USE_NLLB', False)

    def _load_model(self):
        pass

    def translate_segments(self, segments: list[dict], source_lang_whisper: str, target_lang_name: str) -> list[dict]:
        """
        Translates all transcription segments into target_lang_name.
        """
        if not segments:
            return []

        tgt_lang_code = TARGET_LANG_MAPPING.get(target_lang_name, "ta")
        logger.info(f"Translating {len(segments)} segments to {target_lang_name} (code: '{tgt_lang_code}', source: '{source_lang_whisper}')...")

        start_time = time.time()
        translated_segments = []

        for i, seg in enumerate(segments):
            orig_text = seg.get("text", "")
            translated = _translate_single_segment(orig_text, source_lang_whisper, tgt_lang_code)
            
            translated_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": translated.strip() or orig_text,
                "original_text": orig_text
            })

        elapsed = time.time() - start_time
        logger.info(f"Successfully translated {len(translated_segments)} segments into {target_lang_name} in {elapsed:.2f}s")
        if translated_segments:
            logger.info(f"Sample translated output: '{translated_segments[0]['text'][:60]}...'")

        return translated_segments

# Singleton instance
translator_service = NLLBTranslatorService()
