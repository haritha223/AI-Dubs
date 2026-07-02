import asyncio
import os
import sys

# Ensure project root is on sys.path so we can import the package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.tts import generate_chunk_audio
from backend.config import settings

# Make sure azure keys are set in environment or .env before running this test
print('Azure configured:', settings.is_azure_configured)

async def main():
    out = os.path.join(os.getcwd(), 'temp','test_run','azure_tts_test.mp3')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        path = await generate_chunk_audio('வணக்கம், இது மைக்ரோசாஃப்ட் ஆடியோ சோதனை.', out, 'Tamil')
        print('Wrote:', path)
        print('Size:', os.path.getsize(path))
    except Exception as e:
        print('ERROR', repr(e))

if __name__ == '__main__':
    asyncio.run(main())
