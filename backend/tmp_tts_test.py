import asyncio
import os
import sys

# Ensure project root is on sys.path so we can import the package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.tts import generate_chunk_audio

test_text = 'வணக்கம், இது ஒரு சோதனை உரை. ஒரு சில சொற்கள் தமிழில் பேசப்பட வேண்டும்.'
out = os.path.join(os.getcwd(), 'temp','test_run','tts_test_chunk.mp3')

async def main():
    os.makedirs(os.path.dirname(out), exist_ok=True)
    path = await generate_chunk_audio(test_text, out, 'Tamil')
    print('Wrote:', path)
    print('Size:', os.path.getsize(path))

if __name__ == '__main__':
    asyncio.run(main())
