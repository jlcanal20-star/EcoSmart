import secrets
import sqlite3
from urllib.parse import quote
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "eco-smart-tcc-troque-este-texto"

BANCO = "ecosmart.db"
UNIDADES_PADRAO = 3  # usado só para popular a tabela estoque na primeira vez
WHATSAPP_NUMERO = "5561999999999"


def garantir_tabela_estoque():
    conexao = sqlite3.connect(BANCO)
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS estoque (
            id             INTEGER PRIMARY KEY CHECK (id = 1),
            total_unidades INTEGER NOT NULL
        )
        """
    )
    ja_tem_linha = conexao.execute("SELECT 1 FROM estoque WHERE id = 1").fetchone()
    if ja_tem_linha is None:
        conexao.execute(
            "INSERT INTO estoque (id, total_unidades) VALUES (1, ?)", (UNIDADES_PADRAO,)
        )
    conexao.commit()
    conexao.close()


def garantir_tabela_reservas():
    conexao = sqlite3.connect(BANCO)
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS reservas (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
            criado_em  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conexao.commit()
    conexao.close()


def garantir_colunas_usuarios():
    conexao = sqlite3.connect(BANCO)
    colunas = [linha[1] for linha in conexao.execute("PRAGMA table_info(usuarios)")]

    if "codigo_recuperacao_hash" not in colunas:
        conexao.execute("ALTER TABLE usuarios ADD COLUMN codigo_recuperacao_hash TEXT")
    if "pergunta_seguranca" in colunas:
        conexao.execute("ALTER TABLE usuarios DROP COLUMN pergunta_seguranca")
    if "resposta_hash" in colunas:
        conexao.execute("ALTER TABLE usuarios DROP COLUMN resposta_hash")
    if "senha_texto" in colunas:
        conexao.execute("ALTER TABLE usuarios DROP COLUMN senha_texto")

    conexao.commit()
    conexao.close()


garantir_tabela_estoque()
garantir_tabela_reservas()
garantir_colunas_usuarios()

# sem O/0 e I/1, pra não confundir na hora de digitar o código de volta
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def gerar_codigo_recuperacao():
    grupos = ["".join(secrets.choice(ALFABETO_CODIGO) for _ in range(4)) for _ in range(3)]
    return "-".join(grupos)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(BANCO)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def fecha_db(erro):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def total_unidades():
    linha = get_db().execute("SELECT total_unidades FROM estoque WHERE id = 1").fetchone()
    return linha["total_unidades"]


def usuario_logado():
    if "usuario_id" not in session:
        return None
    return get_db().execute(
        "SELECT * FROM usuarios WHERE id = ?", (session["usuario_id"],)
    ).fetchone()


@app.context_processor
def injeta_usuario():
    return {"usuario": usuario_logado()}


@app.context_processor
def injeta_estoque():
    total_reservado = get_db().execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
    restantes = max(total_unidades() - total_reservado, 0)

    minha_reserva = None
    usuario = usuario_logado()
    if usuario:
        minha_reserva = get_db().execute(
            "SELECT * FROM reservas WHERE usuario_id = ?", (usuario["id"],)
        ).fetchone()

    return {"restantes": restantes, "minha_reserva": minha_reserva}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome_usuario = request.form["usuario"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]
        confirmar = request.form["confirmar"]

        db = get_db()

        if not nome_usuario or not email or not senha:
            flash("Preencha todos os campos.", "erro")

        elif len(nome_usuario) < 3:
            flash("O nome de usuário precisa ter pelo menos 3 caracteres.", "erro")

        elif len(senha) < 6:
            flash("A senha precisa ter pelo menos 6 caracteres.", "erro")

        elif senha != confirmar:
            flash("As duas senhas digitadas são diferentes.", "erro")

        elif db.execute("SELECT id FROM usuarios WHERE usuario = ?",
                        (nome_usuario,)).fetchone():
            flash("Esse nome de usuário já está em uso.", "erro")

        elif db.execute("SELECT id FROM usuarios WHERE email = ?",
                        (email,)).fetchone():
            flash("Esse e-mail já está cadastrado.", "erro")

        else:
            codigo_recuperacao = gerar_codigo_recuperacao()
            db.execute(
                """INSERT INTO usuarios
                   (usuario, email, senha_hash, codigo_recuperacao_hash)
                   VALUES (?, ?, ?, ?)""",
                (
                    nome_usuario,
                    email,
                    generate_password_hash(senha),
                    generate_password_hash(codigo_recuperacao),
                ),
            )
            db.commit()
            return render_template("cadastro_sucesso.html", codigo=codigo_recuperacao)

    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_digitado = request.form["login"].strip()
        senha = request.form["senha"]

        linha = get_db().execute(
            "SELECT * FROM usuarios WHERE usuario = ? OR email = ?",
            (login_digitado, login_digitado.lower()),
        ).fetchone()

        if linha is not None and check_password_hash(linha["senha_hash"], senha):
            session["usuario_id"] = linha["id"]
            return redirect(url_for("painel"))

        flash("Usuário ou senha incorretos.", "erro")

    return render_template("login.html")


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        alvo = request.form["usuario_ou_email"].strip()
        codigo = request.form["codigo"].strip().upper()

        usuario = get_db().execute(
            "SELECT * FROM usuarios WHERE usuario = ? OR email = ?",
            (alvo, alvo.lower()),
        ).fetchone()

        codigo_valido = (
            usuario is not None
            and usuario["codigo_recuperacao_hash"] is not None
            and check_password_hash(usuario["codigo_recuperacao_hash"], codigo)
        )

        if codigo_valido:
            session["recuperar_id"] = usuario["id"]
            return redirect(url_for("redefinir"))

        flash("Usuário/e-mail ou código de recuperação incorretos.", "erro")

    return render_template("recuperar.html")


@app.route("/redefinir", methods=["GET", "POST"])
def redefinir():
    usuario_id = session.get("recuperar_id")
    if usuario_id is None:
        flash("Informe seu usuário ou e-mail primeiro.", "erro")
        return redirect(url_for("recuperar"))

    db = get_db()
    usuario = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    if usuario is None:
        session.pop("recuperar_id", None)
        return redirect(url_for("recuperar"))

    if request.method == "POST":
        nova_senha = request.form["nova_senha"]
        confirmar = request.form["confirmar_nova_senha"]

        if len(nova_senha) < 6:
            flash("A nova senha precisa ter pelo menos 6 caracteres.", "erro")
        elif nova_senha != confirmar:
            flash("As duas senhas digitadas são diferentes.", "erro")
        else:
            db.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                (generate_password_hash(nova_senha), usuario_id),
            )
            db.commit()
            session.pop("recuperar_id", None)
            flash("Senha redefinida com sucesso! Agora é só entrar.", "ok")
            return redirect(url_for("login"))

    return render_template("redefinir.html", usuario=usuario)


@app.route("/painel")
def painel():
    usuario = usuario_logado()

    if usuario is None:
        flash("Faça login para acessar sua conta.", "erro")
        return redirect(url_for("login"))

    return render_template("painel.html")


@app.route("/garantir", methods=["GET", "POST"])
def garantir():
    usuario = usuario_logado()
    if usuario is None:
        flash("Faça login para garantir a sua unidade.", "erro")
        return redirect(url_for("login"))

    db = get_db()

    ja_reservou = db.execute(
        "SELECT 1 FROM reservas WHERE usuario_id = ?", (usuario["id"],)
    ).fetchone()
    if ja_reservou:
        flash("Você já garantiu a sua unidade.", "ok")
        return redirect(url_for("painel"))

    total_reservado = db.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
    restantes = total_unidades() - total_reservado

    if restantes <= 0:
        flash("Poxa, as unidades acabaram por enquanto.", "erro")
        return redirect(url_for("index"))

    if request.method == "POST":
        db.execute(
            "INSERT INTO reservas (usuario_id) VALUES (?)", (usuario["id"],)
        )
        db.commit()
        flash("Unidade garantida! Vamos entrar em contato com você.", "ok")
        return redirect(url_for("painel"))

    mensagem = quote(
        f"Olá! Sou {usuario['usuario']} e acabei de garantir minha unidade Eco Smart."
    )
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMERO}?text={mensagem}"
    return render_template("garantir.html", restantes=restantes, whatsapp_url=whatsapp_url)


@app.route("/cancelar-reserva")
def cancelar_reserva():
    usuario = usuario_logado()
    if usuario is None:
        return redirect(url_for("login"))

    db = get_db()
    db.execute("DELETE FROM reservas WHERE usuario_id = ?", (usuario["id"],))
    db.commit()
    flash("Reserva cancelada.", "ok")
    return redirect(url_for("painel"))


@app.route("/sair")
def sair():
    session.clear()
    flash("Você saiu da sua conta.", "ok")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
