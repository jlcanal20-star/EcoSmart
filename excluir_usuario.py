import sqlite3

BANCO = "ecosmart.db"


def listar(db):
    usuarios = db.execute(
        "SELECT id, usuario, email FROM usuarios ORDER BY id"
    ).fetchall()

    if not usuarios:
        print("\nNao ha nenhum usuario cadastrado no banco.\n")
        return None

    print("\nUsuarios cadastrados:")
    print("-" * 50)
    for u in usuarios:
        print(f"  {u[0]:>3}  |  {u[1]:<20}  |  {u[2]}")
    print("-" * 50)
    return usuarios


def main():
    db = sqlite3.connect(BANCO)

    while True:
        usuarios = listar(db)
        if usuarios is None:
            break

        escolha = input(
            "\nDigite o NUMERO (id) do usuario para excluir "
            "(ou 0 para sair): "
        ).strip()

        if escolha == "0" or escolha == "":
            break

        if not escolha.isdigit():
            print("Digite apenas o numero do id.")
            continue

        alvo = next((u for u in usuarios if str(u[0]) == escolha), None)
        if alvo is None:
            print("Nao existe usuario com esse id.")
            continue

        confirmar = input(
            f"Tem certeza que quer excluir '{alvo[1]}' ({alvo[2]})? (s/n): "
        ).strip().lower()

        if confirmar == "s":
            db.execute("DELETE FROM usuarios WHERE id = ?", (alvo[0],))
            db.commit()
            print(f"Usuario '{alvo[1]}' excluido.\n")
        else:
            print("Cancelado.\n")

    db.close()
    print("Ate mais!")


if __name__ == "__main__":
    main()
