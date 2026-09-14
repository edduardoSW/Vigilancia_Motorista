"""Banco local do RotaGuard Painel (specs 014, 015 e 016): SQLite na pasta de dados do usuário, com trava para threads.

Módulo puro (sem pywebview): as regras podem ir para o servidor depois. Todo registro nasce com `uid` (uuid4 em hex),
`criado_em` e `alterado_em` (ISO 8601 em UTC). O esquema sobe por migrações numeradas (`PRAGMA user_version`).
"""
from __future__ import annotations

import os
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

NOME_BANCO = "painel.db"
VARIAVEL_PASTA = "ROTAGUARD_PAINEL_DADOS"


class ErroPainel(Exception):
    """Erro com frase simples para a tela. `codigo`: invalido, sem_permissao, sem_sessao, bloqueado, espera,
    nao_encontrado ou conflito."""

    def __init__(self, erro: str, codigo: str = "invalido", campo: str | None = None, esperar_s: int | None = None):
        super().__init__(erro)
        self.erro, self.codigo, self.campo, self.esperar_s = erro, codigo, campo, esperar_s

    def resposta(self) -> dict:
        resposta = {"ok": False, "erro": self.erro, "codigo": self.codigo}
        if self.campo:
            resposta["campo"] = self.campo
        if self.esperar_s is not None:
            resposta["esperar_s"] = self.esperar_s
        return resposta


def pasta_dados() -> Path:
    """%LOCALAPPDATA%\\RotaGuard\\Painel no Windows, ~/.local/share/rotaguard-painel no Linux; ROTAGUARD_PAINEL_DADOS troca."""
    especial = os.environ.get(VARIAVEL_PASTA)
    if especial:
        return Path(especial)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "RotaGuard" / "Painel"
    return Path.home() / ".local" / "share" / "rotaguard-painel"


def iso_utc(instante: float) -> str:
    return datetime.fromtimestamp(instante, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def novo_uid() -> str:
    return uuid.uuid4().hex


_COMUNS = "uid TEXT NOT NULL UNIQUE, criado_em TEXT NOT NULL, alterado_em TEXT NOT NULL"

MIGRACOES = (
    f"""
    CREATE TABLE meta (chave TEXT PRIMARY KEY, {_COMUNS}, valor TEXT);
    CREATE TABLE usuarios (id INTEGER PRIMARY KEY, {_COMUNS}, nome TEXT NOT NULL,
        usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
        funcao TEXT NOT NULL CHECK (funcao IN ('administrador', 'supervisor', 'consulta')),
        ativo INTEGER NOT NULL DEFAULT 1, senha_hash TEXT NOT NULL, trocar_senha INTEGER NOT NULL DEFAULT 0,
        ultimo_acesso TEXT);
    CREATE TABLE atividades (id INTEGER PRIMARY KEY, {_COMUNS}, em TEXT NOT NULL, usuario_id INTEGER, usuario TEXT,
        acao TEXT NOT NULL, alvo TEXT, detalhe TEXT, hash_anterior TEXT NOT NULL, hash TEXT NOT NULL);
    CREATE TRIGGER atividades_sem_alterar BEFORE UPDATE ON atividades
        BEGIN SELECT RAISE(ABORT, 'o registro de atividades só acrescenta'); END;
    CREATE TRIGGER atividades_sem_apagar BEFORE DELETE ON atividades
        BEGIN SELECT RAISE(ABORT, 'o registro de atividades só acrescenta'); END;
    CREATE TABLE motoristas (id INTEGER PRIMARY KEY, {_COMUNS}, ref TEXT UNIQUE, nome TEXT NOT NULL,
        nome_curto TEXT NOT NULL, matricula TEXT NOT NULL UNIQUE, cpf TEXT, telefone TEXT,
        cnh_numero TEXT NOT NULL UNIQUE, cnh_categoria TEXT NOT NULL, cnh_validade TEXT NOT NULL,
        situacao TEXT NOT NULL, observacoes TEXT);
    CREATE TABLE termos (id INTEGER PRIMARY KEY, {_COMUNS}, motorista_id INTEGER NOT NULL REFERENCES motoristas(id),
        assinado INTEGER NOT NULL, data TEXT, versao TEXT, registrado_por TEXT);
    CREATE TRIGGER termos_sem_alterar BEFORE UPDATE ON termos
        BEGIN SELECT RAISE(ABORT, 'termo nunca é alterado: registre um novo'); END;
    CREATE TRIGGER termos_sem_apagar BEFORE DELETE ON termos
        BEGIN SELECT RAISE(ABORT, 'termo nunca é apagado'); END;
    CREATE TABLE veiculos (id INTEGER PRIMARY KEY, {_COMUNS}, numero TEXT NOT NULL UNIQUE, placa TEXT NOT NULL,
        tipo TEXT NOT NULL, transporta TEXT NOT NULL, modelo TEXT, ano INTEGER, situacao TEXT NOT NULL);
    CREATE TABLE caixas (id INTEGER PRIMARY KEY, {_COMUNS}, codigo TEXT NOT NULL UNIQUE,
        veiculo_id INTEGER UNIQUE REFERENCES veiculos(id), situacao TEXT NOT NULL, detalhe TEXT, ultima_coleta TEXT,
        versao TEXT, dispositivo_id INTEGER, geracao INTEGER, revogada_em TEXT);
    CREATE TABLE caixa_vinculos (id INTEGER PRIMARY KEY, {_COMUNS}, caixa_id INTEGER NOT NULL REFERENCES caixas(id),
        veiculo_id INTEGER NOT NULL REFERENCES veiculos(id), de TEXT NOT NULL, ate TEXT, por TEXT);
    CREATE TABLE configuracoes (secao TEXT PRIMARY KEY, {_COMUNS}, valores TEXT NOT NULL);
    CREATE TABLE decisoes (id INTEGER PRIMARY KEY, {_COMUNS}, momento_id TEXT NOT NULL, resultado TEXT NOT NULL,
        orientado INTEGER NOT NULL DEFAULT 0, por TEXT NOT NULL, funcao TEXT NOT NULL, em TEXT NOT NULL,
        ativa INTEGER NOT NULL DEFAULT 1);
    CREATE INDEX decisoes_momento ON decisoes (momento_id, ativa);
    """,
)


class Banco:
    """Uma conexão só, protegida por trava: a ponte do pywebview chama de threads diferentes."""

    def __init__(self, pasta: Path | str | None = None, relogio=time.time):
        self.pasta = Path(pasta) if pasta is not None else pasta_dados()
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.caminho = self.pasta / NOME_BANCO
        self.relogio = relogio
        self.trava = threading.RLock()
        self._con = sqlite3.connect(self.caminho, check_same_thread=False, isolation_level=None)
        self._con.row_factory = sqlite3.Row
        self._con.execute("PRAGMA foreign_keys = ON")
        self.migrar()

    # Esquema -----------------------------------------------------------------------------------------------------
    def versao_esquema(self) -> int:
        with self.trava:
            return self._con.execute("PRAGMA user_version").fetchone()[0]

    def migrar(self) -> None:
        with self.trava:
            atual = self.versao_esquema()
            for numero, script in enumerate(MIGRACOES[atual:], start=atual + 1):
                self._con.executescript(f"BEGIN IMMEDIATE; {script}; PRAGMA user_version = {numero}; COMMIT;")

    # Consultas ---------------------------------------------------------------------------------------------------
    @contextmanager
    def transacao(self):
        with self.trava:
            if self._con.in_transaction:
                yield self._con
                return
            self._con.execute("BEGIN IMMEDIATE")
            try:
                yield self._con
            except BaseException:
                self._con.execute("ROLLBACK")
                raise
            self._con.execute("COMMIT")

    def executar(self, sql: str, parametros=()) -> sqlite3.Cursor:
        with self.trava:
            return self._con.execute(sql, parametros)

    def um(self, sql: str, parametros=()) -> sqlite3.Row | None:
        with self.trava:
            return self._con.execute(sql, parametros).fetchone()

    def todos(self, sql: str, parametros=()) -> list[sqlite3.Row]:
        with self.trava:
            return self._con.execute(sql, parametros).fetchall()

    def agora(self) -> str:
        return iso_utc(self.relogio())

    def inserir(self, tabela: str, valores: dict) -> int:
        """Tabela e colunas vêm sempre do código, nunca da tela."""
        agora = self.agora()
        dados = {"uid": novo_uid(), "criado_em": agora, "alterado_em": agora, **valores}
        colunas = ", ".join(dados)
        marcas = ", ".join("?" for _ in dados)
        return self.executar(f"INSERT INTO {tabela} ({colunas}) VALUES ({marcas})", tuple(dados.values())).lastrowid

    def atualizar(self, tabela: str, chave: str, valor_chave, valores: dict) -> None:
        dados = {**valores, "alterado_em": self.agora()}
        trechos = ", ".join(f"{coluna} = ?" for coluna in dados)
        self.executar(f"UPDATE {tabela} SET {trechos} WHERE {chave} = ?", (*dados.values(), valor_chave))

    def meta_ler(self, chave: str, padrao: str | None = None) -> str | None:
        linha = self.um("SELECT valor FROM meta WHERE chave = ?", (chave,))
        return padrao if linha is None or linha["valor"] is None else linha["valor"]

    def meta_gravar(self, chave: str, valor: str | None) -> None:
        with self.transacao():
            if self.um("SELECT 1 FROM meta WHERE chave = ?", (chave,)):
                self.atualizar("meta", "chave", chave, {"valor": valor})
            else:
                self.inserir("meta", {"chave": chave, "valor": valor})

    # Cópia -------------------------------------------------------------------------------------------------------
    def serializar(self) -> bytes:
        with self.trava:
            return self._con.serialize()

    def fechar(self) -> None:
        with self.trava:
            self._con.close()
