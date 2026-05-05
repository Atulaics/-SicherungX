import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('database/sicherungx.db')
cur = conn.cursor()

username = 'tarun'
password = '123456'
email = 'tarun@example.com'
role = 'employee'
full_name = 'Tarun'

hashed = generate_password_hash(password)

try:
    cur.execute('''
        INSERT INTO users (username, email, password_hash, role, full_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, email, hashed, role, full_name))
    conn.commit()
    print("User 'tarun' created successfully.")
except sqlite3.IntegrityError:
    print("User already exists or integrity error.")
finally:
    conn.close()
