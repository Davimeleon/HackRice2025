import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check if clones table exists and needs updates
cursor.execute('PRAGMA table_info(clones)')
columns = [col[1] for col in cursor.fetchall()]

# Add name column if missing
if 'name' not in columns:
    cursor.execute('ALTER TABLE clones ADD COLUMN name TEXT')

# Remove llm_conversation if present
if 'llm_conversation' in columns:
    cursor.execute('''
        CREATE TABLE clones_backup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            answers_json TEXT NOT NULL,
            text_path TEXT,
            persona TEXT,
            profile_pic_path TEXT,
            name TEXT
        )
    ''')
    cursor.execute('''
        INSERT INTO clones_backup (id, user_id, answers_json, text_path, persona, profile_pic_path, name)
        SELECT id, user_id, answers_json, text_path, persona, profile_pic_path, name FROM clones
    ''')
    cursor.execute('DROP TABLE clones')
    cursor.execute('''
        CREATE TABLE clones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            answers_json TEXT NOT NULL,
            text_path TEXT,
            persona TEXT,
            profile_pic_path TEXT,
            name TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        INSERT INTO clones (id, user_id, answers_json, text_path, persona, profile_pic_path, name)
        SELECT id, user_id, answers_json, text_path, persona, profile_pic_path, name FROM clones_backup
    ''')
    cursor.execute('DROP TABLE clones_backup')

# Commit and close
conn.commit()
conn.close()
print('Database updated: llm_conversation removed, name column added.')