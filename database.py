# database.py

import sqlite3
from typing import Optional, List, Tuple
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connected_integration_id TEXT UNIQUE NOT NULL,
            bot_token TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_integration(connected_integration_id: str, bot_token: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO integrations 
        (connected_integration_id, bot_token) 
        VALUES (?, ?)
    """, (connected_integration_id, bot_token))
    conn.commit()
    conn.close()

def get_bot_token(connected_integration_id: str) -> Optional[str]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bot_token FROM integrations 
        WHERE connected_integration_id = ?
    """, (connected_integration_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_integrations() -> List[Tuple[str, str]]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT connected_integration_id, bot_token FROM integrations
    """)
    result = cursor.fetchall()
    conn.close()
    return result
