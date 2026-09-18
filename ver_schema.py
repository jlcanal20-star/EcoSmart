import sqlite3

conn = sqlite3.connect('ecosmart.db')
resultado = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall()

for linha in resultado:
    print(linha[0])
    print('---')