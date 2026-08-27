from pathlib import Path

from decouple import AutoConfig

BASE_DIR = Path(__file__).resolve().parents[3]
config = AutoConfig(search_path=BASE_DIR)
