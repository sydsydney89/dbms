"""
init_db.py - creates and seeds the SQLite database from schema.sql
run once before starting the app: python init_db.py
"""
import sqlite3
import os

DB_PATH = "concert.db"

def init():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        with open("schema.sql", "r") as f:
            conn.executescript(f.read())
        print("Database initialized and seeded successfully.")

if __name__ == "__main__":
    init()
