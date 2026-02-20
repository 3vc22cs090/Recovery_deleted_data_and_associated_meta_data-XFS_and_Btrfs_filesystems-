# models.py
import sqlite3
from sqlite3 import Connection
from config import DB_PATH

def get_conn() -> Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        uploaded_by TEXT NOT NULL
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS deleted_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_path TEXT,
        deleted_at TEXT,
        filesystem TEXT,
        recovery_blob BLOB,
        recovered INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('DB initialized at', DB_PATH)
