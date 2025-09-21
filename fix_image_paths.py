import sqlite3
import os

# Connect to the database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check profile_pic_path entries
cursor.execute('SELECT id, profile_pic_path FROM clones')
rows = cursor.fetchall()
for row in rows:
    old_path = row[1]
    if old_path:
        new_path = old_path.replace('Uploads', 'uploads')
        cursor.execute('UPDATE clones SET profile_pic_path = ? WHERE id = ?', (new_path, row[0]))
        print(f'Updated path: {old_path} -> {new_path}')
    else:
        print(f'NULL profile_pic_path for clone ID {row[0]}')

# Commit and close
conn.commit()
conn.close()
print('Image paths checked.')