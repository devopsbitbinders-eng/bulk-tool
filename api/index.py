import sys
import os
from fastapi import Request

# Point to root to import main.py logic
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from main import app

# This ensures Vercel sees the FastAPI instance
# and handles all routes defined in main.py
