# models.py
import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            answers_json TEXT NOT NULL, -- JSON of question answers
            text_path TEXT, -- Path to uploaded text file
            llm_conversation TEXT, -- Stored LLM interaction
            persona TEXT, -- LLM-generated persona summary for bot
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

class User:
    pass

class Clone:
    pass

class Question:
    pass

class Answer:
    pass