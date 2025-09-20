import sqlite3

# Connect to the database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Add the text_path column (if not already added)
#cursor.execute('ALTER TABLE clones ADD COLUMN text_path TEXT')

# Add the persona column
#cursor.execute('ALTER TABLE clones ADD COLUMN persona TEXT')
cursor.execute('ALTER TABLE clones ADD COLUMN profile_pic_path TEXT')
# Commit and close
conn.commit()
conn.close()