import time
import logging
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

# NLLB codes (kept for reference if upgrading to bigger server later)
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


def _google_translate(text: str, target_lang_code: str) -> str:
    """Translate text using free Google Translate API."""
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": target_lang_code, "dt": "t", "q": text},
            timeout=10
        )
        if r.status_code == 200:
            res = r.json()
            return "".join([part[0] for part in res[0] if part[0]])
    except Exception as ex:
        logger.warning(f"Google Translate error: {ex}")
    return text


class NLLBTranslatorService:
    """Lightweight translator that uses Google Translate (fast, no RAM).
    Falls back to NLLB only if explicitly requested via USE_NLLB=true env var.
    """
    def __init__(self):
        self.model_name = settings.NLLB_MODEL_NAME
        self.tokenizer = None
        self.model = None
        self.use_nllb = getattr(settings, 'USE_NLLB', False)

    def _load_model(self):
        """Lazy load NLLB model only if USE_NLLB is enabled."""
        if not self.use_nllb:
            logger.info("Using Google Translate (fast mode) — NLLB model not loaded to save RAM.")
            return

        if self.model is not None:
            return

        logger.info(f"Loading NLLB-200 model '{self.model_name}'...")
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        MAX_RETRIES = 3
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                from huggingface_hub import snapshot_download
                logger.info(f"Downloading/verifying model cache (attempt {attempt}/{MAX_RETRIES})...")
                local_dir = snapshot_download(
                    repo_id=self.model_name,
                    local_files_only=False,
                    ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"]
                )
                logger.info(f"Model files ready at: {local_dir}")

                self.tokenizer = AutoTokenizer.from_pretrained(local_dir)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    local_dir,
                    low_cpu_mem_usage=True
                )
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model.to(device)
                logger.info(f"NLLB-200 model loaded successfully on device: {device}")
                return

            except Exception as e:
                logger.error(f"Attempt {attempt}/{MAX_RETRIES} failed to load NLLB-200 model: {e}")
                if attempt < MAX_RETRIES:
                    wait_secs = 5 * attempt
                    logger.info(f"Retrying in {wait_secs} seconds...")
                    time.sleep(wait_secs)
                else:
                    raise RuntimeError(
                        f"Could not load NLLB-200 model after {MAX_RETRIES} attempts. "
                        f"Check your internet connection and re-run. Error: {e}"
                    )

    def translate_segments(self, segments: list[dict], source_lang_whisper: str, target_lang_name: str) -> list[dict]:
        """
        Translates a list of transcription segments into the target language.
        Uses Google Translate by default (fast, no RAM). Falls back to NLLB if enabled.
        """
        if not segments:
            return []

        tgt_lang_code = TARGET_LANG_MAPPING.get(target_lang_name, "en")
        logger.info(f"Translating {len(segments)} segments to {target_lang_name} ({tgt_lang_code})...")

        start_time = time.time()

        # ── Google Translate (Primary — fast, no RAM) ──
        if not self.use_nllb:
            translations = []
            for seg in segments:
                translated = _google_translate(seg["text"], tgt_lang_code)
                translations.append(translated)
            
            elapsed = time.time() - start_time
            logger.info(f"Google Translate completed {len(segments)} segments in {elapsed:.1f}s")

            translated_segments = []
            for i, seg in enumerate(segments):
                translated_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": translations[i].strip() or seg["text"],
                    "original_text": seg["text"]
                })
            logger.info(f"Successfully translated {len(translated_segments)} segments.")
            return translated_segments

        # ── NLLB Fallback (only if USE_NLLB=true) ──
        self._load_model()
        import torch
        
        src_lang = WHISPER_TO_NLLB.get(source_lang_whisper, "eng_Latn")
        nllb_tgt = NLLB_LANG_MAPPING.get(target_lang_name, "eng_Latn")

        texts_to_translate = [seg["text"] for seg in segments]
        translations = []

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                torch.set_num_threads(2)

            self.tokenizer.src_lang = src_lang
            
            if hasattr(self.tokenizer, "lang_code_to_id"):
                forced_bos_token_id = self.tokenizer.lang_code_to_id[nllb_tgt]
            else:
                forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(nllb_tgt)

            BATCH_SIZE = 8
            for i in range(0, len(texts_to_translate), BATCH_SIZE):
                batch_texts = texts_to_translate[i:i + BATCH_SIZE]
                inputs = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=128
                ).to(device)

                with torch.no_grad():
                    translated_tokens = self.model.generate(
                        **inputs,
                        forced_bos_token_id=forced_bos_token_id,
                        max_new_tokens=80,
                        num_beams=1,
                        do_sample=False,
                        early_stopping=True
                    )

                batch_translations = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
                translations.extend(batch_translations)

        except Exception as e:
            logger.warning(f"NLLB error ({e}) — falling back to Google Translate...")
            translations = [_google_translate(t, tgt_lang_code) for t in texts_to_translate]

        translated_segments = []
        for i, seg in enumerate(segments):
            translated_text = translations[i] if i < len(translations) else seg["text"]
            translated_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": translated_text.strip() or seg["text"],
                "original_text": seg["text"]
            })
            
        logger.info(f"Successfully translated {len(translated_segments)} segments.")
        return translated_segments

# Singleton instance
translator_service = NLLBTranslatorService()
