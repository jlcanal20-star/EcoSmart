import sqlite3
import time
import unicodedata
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


def garantir_tabela_usuarios():
    # só cria se o banco ainda não tiver a tabela (banco novo, sem init_db.py)
    conexao = sqlite3.connect(BANCO)
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario              TEXT NOT NULL UNIQUE,
            email                TEXT NOT NULL UNIQUE,
            senha_hash           TEXT NOT NULL,
            palavra_secreta_hash TEXT NOT NULL,
            criado_em            TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conexao.commit()
    conexao.close()


def nomes_das_colunas(conexao):
    return [linha[1] for linha in conexao.execute("PRAGMA table_info(usuarios)")]


def garantir_colunas_usuarios():
    conexao = sqlite3.connect(BANCO)
    colunas = nomes_das_colunas(conexao)

    try:
        if "palavra_secreta_hash" not in colunas:
            if "codigo_recuperacao_hash" in colunas:
                # banco antigo: a coluna do código de recuperação vira a da palavra
                # secreta (quem já tem conta continua conseguindo recuperar a senha
                # com o código que guardou)
                conexao.execute(
                    "ALTER TABLE usuarios RENAME COLUMN "
                    "codigo_recuperacao_hash TO palavra_secreta_hash"
                )
            else:
                conexao.execute("ALTER TABLE usuarios ADD COLUMN palavra_secreta_hash TEXT")
        if "pergunta_seguranca" in colunas:
            conexao.execute("ALTER TABLE usuarios DROP COLUMN pergunta_seguranca")
        if "resposta_hash" in colunas:
            conexao.execute("ALTER TABLE usuarios DROP COLUMN resposta_hash")
        if "senha_texto" in colunas:
            conexao.execute("ALTER TABLE usuarios DROP COLUMN senha_texto")
        conexao.commit()
    except sqlite3.OperationalError:
        # se dois processos do servidor ligarem juntos, o outro pode ter feito a
        # mudança primeiro; só é erro de verdade se a coluna continuar faltando
        conexao.rollback()
        if "palavra_secreta_hash" not in nomes_das_colunas(conexao):
            raise
    finally:
        conexao.close()


garantir_tabela_usuarios()
garantir_tabela_estoque()
garantir_tabela_reservas()
garantir_colunas_usuarios()


# ---------- palavra secreta (recuperação de senha) ----------

def normalizar_palavra(texto):
    """Ignora maiúsculas, acentos e espaços extras: 'Girassol ' = 'girassol'."""
    sem_acento = "".join(
        letra for letra in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(letra)
    )
    return " ".join(sem_acento.lower().split())


def palavra_confere(hash_guardado, digitada):
    if not hash_guardado:
        return False
    if check_password_hash(hash_guardado, normalizar_palavra(digitada)):
        return True
    # contas antigas: o código de recuperação era guardado em letras maiúsculas
    return check_password_hash(hash_guardado, digitada.strip().upper())


# limite de tentativas erradas na recuperação (fica na memória do servidor)
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 10 * 60
falhas_recuperacao = {}


def recuperacao_bloqueada(chave):
    registro = falhas_recuperacao.get(chave)
    if registro is None:
        return False
    quantidade, momento = registro
    if time.time() - momento > BLOQUEIO_SEGUNDOS:
        falhas_recuperacao.pop(chave, None)
        return False
    return quantidade >= MAX_TENTATIVAS


def registrar_falha_recuperacao(chave):
    quantidade, _ = falhas_recuperacao.get(chave, (0, 0))
    falhas_recuperacao[chave] = (quantidade + 1, time.time())


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
        palavra = normalizar_palavra(request.form.get("palavra_secreta", ""))
        confirmar_palavra = normalizar_palavra(request.form.get("confirmar_palavra", ""))

        db = get_db()

        if not nome_usuario or not email or not senha or not palavra:
            flash("Preencha todos os campos.", "erro")

        elif len(nome_usuario) < 3:
            flash("O nome de usuário precisa ter pelo menos 3 caracteres.", "erro")

        elif len(senha) < 6:
            flash("A senha precisa ter pelo menos 6 caracteres.", "erro")

        elif senha != confirmar:
            flash("As duas senhas digitadas são diferentes.", "erro")

        elif len(palavra) < 4:
            flash("A palavra secreta precisa ter pelo menos 4 caracteres.", "erro")

        elif palavra != confirmar_palavra:
            flash("As duas palavras secretas digitadas são diferentes.", "erro")

        elif palavra == normalizar_palavra(senha):
            flash("A palavra secreta não pode ser igual à senha.", "erro")

        elif db.execute("SELECT id FROM usuarios WHERE usuario = ?",
                        (nome_usuario,)).fetchone():
            flash("Esse nome de usuário já está em uso.", "erro")

        elif db.execute("SELECT id FROM usuarios WHERE email = ?",
                        (email,)).fetchone():
            flash("Esse e-mail já está cadastrado.", "erro")

        else:
            db.execute(
                """INSERT INTO usuarios
                   (usuario, email, senha_hash, palavra_secreta_hash)
                   VALUES (?, ?, ?, ?)""",
                (
                    nome_usuario,
                    email,
                    generate_password_hash(senha),
                    generate_password_hash(palavra),
                ),
            )
            db.commit()
            return render_template("cadastro_sucesso.html")

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
        palavra = request.form.get("palavra_secreta", "")
        chave = alvo.lower()

        if recuperacao_bloqueada(chave):
            flash("Muitas tentativas erradas. Aguarde 10 minutos e tente de novo.", "erro")
            return render_template("recuperar.html")

        usuario = get_db().execute(
            "SELECT * FROM usuarios WHERE usuario = ? OR email = ?",
            (alvo, alvo.lower()),
        ).fetchone()

        palavra_valida = (
            usuario is not None
            and palavra_confere(usuario["palavra_secreta_hash"], palavra)
        )

        if palavra_valida:
            falhas_recuperacao.pop(chave, None)
            session["recuperar_id"] = usuario["id"]
            return redirect(url_for("redefinir"))

        registrar_falha_recuperacao(chave)
        flash("Usuário/e-mail ou palavra secreta incorretos.", "erro")

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
