import sqlite3

BANCO = "ecosmart.db"

conexao = sqlite3.connect(BANCO)

with open("schema.sql", encoding="utf-8") as arquivo:
    conexao.executescript(arquivo.read())

conexao.commit()
conexao.close()

print("Banco de dados 'ecosmart.db' criado com sucesso.")
print("Agora rode:  python app.py")
