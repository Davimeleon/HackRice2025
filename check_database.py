import sqlite3

# Connect to the database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check all columns in clones table
cursor.execute('SELECT id, user_id, answers_json, text_path, persona, profile_pic_path, name FROM clones')
rows = cursor.fetchall()
for row in rows:
    print(f'Clone ID: {row[0]}, User ID: {row[1]}, Profile Pic Path: {row[5]}, Name: {row[6]}')
conn.close()
print('Database check complete.')