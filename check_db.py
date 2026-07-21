import sqlite3, os

path = os.path.join(os.path.dirname(__file__), 'bot_data.db')
if not os.path.exists(path):
    print(f'Database file NOT FOUND at: {path}')
    exit()

conn = sqlite3.connect(path)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Database found!')
print('Tables:', [t[0] for t in tables])
for t in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
    print(f'  {t[0]}: {count} rows')
conn.close()
