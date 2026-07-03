import time
import logging
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from backend.config import settings

logger = logging.getLogger(__name__)

# Supported target languages mapping
TARGET_LANG_MAPPING = {
    "Tamil": "tam_Taml",
    "Telugu": "tel_Telu",
    "Malayalam": "mal_Mlym",
    "Kannada": "kan_Knda",
    "English": "eng_Latn",
    "Hindi": "hin_Deva"
}

# Whisper to NLLB source language mapping
WHISPER_TO_NLLB = {
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "ml": "mal_Mlym",
    "kn": "kan_Knda",
    # Common fallback codes
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "it": "ita_Latn",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
    "zh": "zho_Hans",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "ar": "ary_Arab",
    "tr": "tur_Latn",
    "nl": "nld_Latn"
}

class NLLBTranslatorService:
    def __init__(self):
        self.model_name = settings.NLLB_MODEL_NAME
        self.tokenizer = None
        self.model = None

    def _load_model(self):
        """Lazy load tokenizer and model to conserve memory.
        Uses snapshot_download with up to 3 retries to handle network drops
        during the large (~2.4GB) NLLB-200 model download.
        """
        if self.model is not None:
            return

        logger.info(f"Loading NLLB-200 model '{self.model_name}'...")

        MAX_RETRIES = 3
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                from huggingface_hub import snapshot_download
                logger.info(f"Downloading/verifying model cache (attempt {attempt}/{MAX_RETRIES})...")
                # snapshot_download resumes partial downloads automatically
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
                return  # success — exit retry loop

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
        
        Args:
            segments (list[dict]): List of segments with keys "start", "end", "text".
            source_lang_whisper (str): The Whisper detected source language (e.g. "en").
            target_lang_name (str): The target language name (e.g. "Tamil").
            
        Returns:
            list[dict]: Translated segments with keys "start", "end", "text", "original_text".
        """
        if not segments:
            return []

        self._load_model()
        
        # Determine source and target NLLB language codes
        src_lang = WHISPER_TO_NLLB.get(source_lang_whisper, "eng_Latn")
        tgt_lang = TARGET_LANG_MAPPING.get(target_lang_name)
        
        if not tgt_lang:
            logger.warning(f"Unsupported target language: {target_lang_name}. Defaulting to English (eng_Latn).")
            tgt_lang = "eng_Latn"

        logger.info(f"Translating from {src_lang} to {tgt_lang} using NLLB-200 (directly)")
        
        # Extract text list for batch translation
        texts_to_translate = [seg["text"] for seg in segments]
        
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Set source language on tokenizer
            self.tokenizer.src_lang = src_lang
            
            # Tokenize batch
            inputs = self.tokenizer(
                texts_to_translate,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(device)
            
            # Generate translations
            with torch.no_grad():
                translated_tokens = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_lang],
                    max_length=512
                )
                
            # Decode batch
            translations = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
            
        except Exception as e:
            logger.error(f"NLLB batch translation failed: {e}")
            raise RuntimeError(f"Translation service failed: {e}")

        # Construct translated segments preserving original index & timestamps
        translated_segments = []
        for i, seg in enumerate(segments):
            translated_text = translations[i] if i < len(translations) else ""
            translated_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": translated_text.strip(),
                "original_text": seg["text"]
            })
            
        logger.info(f"Successfully translated {len(translated_segments)} segments.")
        return translated_segments

# Singleton instance
translator_service = NLLBTranslatorService()
