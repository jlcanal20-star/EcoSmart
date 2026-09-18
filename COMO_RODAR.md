# Eco Smart — site com banco de dados

Seu site, agora com **cadastro e login** ligados a um banco de dados SQLite.

---

## ⚠️ PRIMEIRA COISA: copiar suas imagens

Consegui recuperar do `.rar` só três imagens. **Copie a sua pasta `img`
inteira** (a original, com `logo4.png` até `logo7.png`) para dentro de
`static/img/`, substituindo o que estiver lá.

Sem isso a logo do topo aparece quebrada. É só arrastar e soltar.

---

## Como rodar

Abra o **Prompt de Comando** dentro desta pasta e digite, um por vez:

```
pip install flask
python init_db.py
python app.py
```

Depois abra no navegador: **http://127.0.0.1:5000**

Para parar o servidor: `Ctrl + C` na janela preta.

Nas próximas vezes você só precisa de `python app.py`.
O `init_db.py` é só na primeira vez — **rodar de novo apaga todos os
cadastros** e cria o banco vazio.

---

## Onde fica cada coisa

```
EcoSmart/
├── app.py            ← o servidor: as páginas e o acesso ao banco
├── ecosmart.db       ← O BANCO DE DADOS (é este arquivo, só ele)
├── schema.sql        ← os comandos que criam a tabela
├── init_db.py        ← cria o ecosmart.db a partir do schema.sql
│
├── templates/        ← as páginas HTML
│   ├── base.html     ← cabeçalho, menu e rodapé (aparece em todas)
│   ├── index.html    ← sua página inicial
│   ├── login.html
│   ├── cadastro.html
│   └── painel.html   ← "Minha conta", área que só quem logou vê
│
└── static/           ← arquivos fixos
    ├── style.css     ← seu CSS + os acréscimos
    └── img/          ← suas imagens (COPIE A SUA PASTA AQUI)
```

O Flask exige essa divisão: página vai em `templates/`, arquivo fixo vai
em `static/`. Por isso, dentro do HTML, `src="img/logo7.png"` virou
`src="{{ url_for('static', filename='img/logo7.png') }}"`. É só o
endereço do arquivo — o visual não mudou.

---

## O banco de dados

Uma tabela só, chamada **`usuarios`**, com 5 colunas:

| Coluna       | O que guarda                                    |
|--------------|--------------------------------------------------|
| `id`         | número único de cada pessoa (chave primária)     |
| `usuario`    | nome de usuário — não pode repetir               |
| `email`      | e-mail — não pode repetir                        |
| `senha_hash` | o código embaralhado da senha                    |
| `criado_em`  | data e hora do cadastro                          |

O SQLite guarda tudo isso dentro do arquivo `ecosmart.db`. Não instala
servidor, não precisa de XAMPP nem MySQL. Copiou a pasta pro pendrive, o
banco foi junto com os dados dentro.

### Ver o banco por dentro

Baixe o **DB Browser for SQLite** (grátis) e abra o `ecosmart.db`. Dá pra
ver a tabela e os cadastros. Mostrar isso na apresentação costuma
impressionar a banca.

---

## O que mudei no seu código

**No HTML** — só os caminhos dos arquivos e a divisão em `templates/`.
O conteúdo, os textos e a estrutura continuam seus.

**No CSS** — mantive todas as suas cores (`#1a1a2e`, `#525180`,
`#2b2b4e`) e organizei em duas partes: a Parte 1 é o seu CSS original,
a Parte 2 são os acréscimos. Duas correções:

1. A regra `main section { display: flex }` estava fazendo o título
   "Por que escolher o Eco Smart?" ficar **do lado** dos cards em vez de
   em cima. Acrescentei `flex-direction: column` nessas seções.
2. O `.area-contato` tinha `margin-top: 300px`, o que deixava um buraco
   enorme na página. Baixei para `60px`.

**Animações que entraram** (todas discretas):

- a linha embaixo dos itens do menu cresce da esquerda pra direita
- os cards sobem e ganham borda verde quando o mouse passa
- a foto do protótipo sobe e ganha sombra
- as seções aparecem subindo conforme você rola a página
- as caixas de login e os avisos surgem de baixo
- os campos do formulário ganham brilho verde ao serem clicados

Todas respeitam `prefers-reduced-motion` — quem configurou o computador
para reduzir animações vê o site parado. Isso é acessibilidade, e é um
ponto bom pra citar na apresentação.

---

## Três coisas para falar na banca

**1. A senha nunca é guardada.**
O `generate_password_hash` transforma `senha123` em algo como
`scrypt:32768:8:1$DHxj...`. Esse processo é de mão única: não existe
como voltar do código para a senha. No login, o site embaralha a senha
digitada do mesmo jeito e compara os dois códigos. Se o banco vazar,
ninguém descobre as senhas.

**2. O SQL usa `?` em vez de juntar texto.**
Repare que está escrito `WHERE usuario = ?` e o valor vai separado. Se
fosse `WHERE usuario = " + digitado`, alguém poderia digitar um comando
SQL no campo e apagar sua tabela. Isso se chama **SQL Injection**, e o
`?` é o que impede.

**3. A área restrita é conferida no servidor.**
A função `painel()` checa se existe alguém logado antes de mostrar
qualquer coisa. Se você só escondesse o link no HTML, bastaria digitar
`/painel` na barra de endereço para entrar.

---

## Antes de entregar

- No `app.py`, troque o texto da `app.secret_key` por outro qualquer.
- Se for publicar de verdade, tire o `debug=True` da última linha.
