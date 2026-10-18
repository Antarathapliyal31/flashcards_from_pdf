#!/usr/bin/env python3
"""Print a UTC timestamp in YYYYMMDD_HHMMSS.
Used by the make-flashcards skill so Claude never has to invent one.
"""
from datetime import datetime, timezone

print(datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
