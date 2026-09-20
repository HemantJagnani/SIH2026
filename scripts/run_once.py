"""run_once.py – run the full pipeline for today from the command line."""
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project src to path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytz
from apix.pipeline import run

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

if __name__ == "__main__":
    IST = pytz.timezone("Asia/Kolkata")
    today = datetime.now(IST).date()
    print(f"Running pipeline for {today} ...")
    result = run(today)
    print(f"Done: {result}")
    sys.exit(0 if result["status"] in ("ok", "partial") else 1)
