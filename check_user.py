import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('database/sicherungx.db')
cur = conn.cursor()
cur.execute("SELECT * FROM users WHERE username='tarun'")
user = cur.fetchone()

if user:
    print(f"User found: ID={user[0]}, Username={user[1]}, Email={user[2]}, Role={user[4]}, Full Name={user[5]}")
    # index 3 is password_hash
    match = check_password_hash(user[3], '123456')
    print(f"Password '123456' matches: {match}")
else:
    print("User 'tarun' not found.")
conn.close()
