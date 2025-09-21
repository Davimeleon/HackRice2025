import sqlite3
from models import init_db  # Assumes models.py is in the same directory

# Connect to the database and drop tables
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS clones')
cursor.execute('DROP TABLE IF EXISTS users')
conn.commit()
conn.close()

# Recreate tables via init_db
init_db()

print('Database reset: All users and clones deleted. Tables recreated.')