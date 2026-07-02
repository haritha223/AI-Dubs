import os
import shutil

OUTPUT_DIR = "outputs"

def save_file(file_path: str, output_name: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    final_path = os.path.join(OUTPUT_DIR, output_name)
    shutil.copy(file_path, final_path)
    return final_path
