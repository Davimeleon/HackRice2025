import sqlite3

# Connect to the database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Update profile_pic_path to use lowercase 'uploads'
cursor.execute('SELECT id, profile_pic_path FROM clones WHERE profile_pic_path LIKE "Uploads%" OR profile_pic_path LIKE "uploads%"')
rows = cursor.fetchall()
for row in rows:
    old_path = row[1]
    if old_path:
        new_path = old_path.replace('Uploads', 'uploads').replace('uploads', 'uploads')
        cursor.execute('UPDATE clones SET profile_pic_path = ? WHERE id = ?', (new_path, row[0]))
        print(f'Updated path: {old_path} -> {new_path}')

# Commit and close
conn.commit()
conn.close()
print('Image paths updated.')