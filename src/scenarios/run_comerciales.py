import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.utils.sector_runner import run_sector_pipeline

if __name__ == "__main__":
    run_sector_pipeline("comerciales")
