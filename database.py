"""
CertPilot AI — Database Connection
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "certpilot.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # return dict-like rows
    return conn
