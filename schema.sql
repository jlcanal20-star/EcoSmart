DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS reservas;
DROP TABLE IF EXISTS estoque;

CREATE TABLE usuarios (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario                  TEXT NOT NULL UNIQUE,
    email                    TEXT NOT NULL UNIQUE,
    senha_hash               TEXT NOT NULL,
    codigo_recuperacao_hash  TEXT NOT NULL,
    criado_em                TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE reservas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    criado_em  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE estoque (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    total_unidades INTEGER NOT NULL
);

INSERT INTO estoque (id, total_unidades) VALUES (1, 3);
