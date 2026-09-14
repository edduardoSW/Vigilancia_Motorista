"""Script local no painel (spec 018): reconhece que o script da caixa está aberto neste computador e captura os eventos.

"Aberto" = anúncio `em_execucao.json` com sinal de menos de 15 s e processo vivo, ou (plano B, para o pacote já
instalado que ainda não anuncia) processo achado pelo nome. Os eventos saem da fila do script (`eventos.db`, tabela
`events`), aberta só para leitura (`mode=ro`), e são copiados para `capturas.db` na pasta de dados do painel, sem
duplicar (chave: `event_uid` do script) e separados por sessão (cada vez que o script abriu).

Python puro, sem pywebview, para poder ir para o servidor depois. Todo registro novo nasce com `uid`, `criado_em` e
`alterado_em`.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

logger = logging.getLogger("rotaguard.painel.script_local")

ARQUIVO_ANUNCIO = "em_execucao.json"
ARQUIVO_EVENTOS = "eventos.db"
ARQUIVO_CAPTURAS = "capturas.db"
SINAL_MAX_S = 15.0
INTERVALO_VIGIA_S = 2.0
LOTE = 500
EXECUTAVEIS = ("rotaguardteste.exe", "rotaguardteste")
MARCAS_NA_LINHA = ("app_teste.py", "run_monitor.py", "rotaguardteste")
CHAVES_ESTADO = ("aberto", "programa", "desde", "pid", "camera", "ultimo_sinal", "eventos", "pasta")


@dataclass(frozen=True)
class Processo:
    pid: int
    nome: str
    linha: str = ""  # linha de comando (ps no Linux); o tasklist do Windows não informa


# ---------- datas ----------

def _iso(instante: datetime) -> str:
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def _ler_iso(texto) -> datetime | None:
    if not isinstance(texto, str) or not texto:
        return None
    try:
        instante = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return instante if instante.tzinfo else instante.replace(tzinfo=timezone.utc)


# ---------- onde o script grava ----------

def pastas_padrao_do_script(sistema: str | None = None, ambiente: Mapping[str, str] | None = None,
                            home: Path | None = None) -> list[Path]:
    """Pasta do RotaGuard Teste (spec 010, decisão 4) e a padrão do run_monitor.py (~/.drivesafe ou DRIVESAFE_DATA_DIR)."""
    sistema = sys.platform if sistema is None else sistema
    ambiente = os.environ if ambiente is None else ambiente
    home = Path.home() if home is None else home
    if sistema.startswith("win"):
        base = Path(ambiente["LOCALAPPDATA"]) if ambiente.get("LOCALAPPDATA") else home / "AppData" / "Local"
        teste = base / "RotaGuard" / "Teste"
    else:
        base = Path(ambiente["XDG_DATA_HOME"]) if ambiente.get("XDG_DATA_HOME") else home / ".local" / "share"
        teste = base / "rotaguard" / "teste"
    pastas = []
    if (ambiente.get("DRIVESAFE_DATA_DIR") or "").strip():
        pastas.append(Path(ambiente["DRIVESAFE_DATA_DIR"].strip()).expanduser())
    for pasta in (teste, home / ".drivesafe"):
        if pasta not in pastas:
            pastas.append(pasta)
    return pastas


# ---------- processos (sem psutil) ----------

def ler_tasklist_csv(texto: str) -> list[Processo]:
    processos = []
    for campos in csv.reader(io.StringIO(texto)):
        if len(campos) >= 2 and campos[1].strip().isdigit():
            processos.append(Processo(int(campos[1].strip()), campos[0].strip()))
    return processos


def ler_ps(texto: str) -> list[Processo]:
    processos = []
    for linha in texto.splitlines():
        partes = linha.strip().split(None, 1)
        if not partes or not partes[0].isdigit():
            continue
        argumentos = partes[1] if len(partes) > 1 else ""
        nome = Path(argumentos.split(" ", 1)[0]).name if argumentos else ""
        processos.append(Processo(int(partes[0]), nome, argumentos))
    return processos


def listar_processos_do_sistema() -> list[Processo]:
    try:
        if sys.platform.startswith("win"):
            saida = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, timeout=10,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return ler_tasklist_csv(saida.stdout.decode("utf-8", errors="replace"))
        saida = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, timeout=10)
        return [p for p in ler_ps(saida.stdout.decode("utf-8", errors="replace")) if p.pid != os.getpid()]
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("Lista de processos indisponível: %s", exc)
        return []


def eh_processo_do_script(processo: Processo) -> bool:
    if processo.nome.lower() in EXECUTAVEIS:
        return True
    linha = processo.linha.lower()
    return any(marca in linha for marca in MARCAS_NA_LINHA)


def pid_vivo_do_sistema(pid: int) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform.startswith("win"):
        # Nunca os.kill(pid, 0) no Windows: o sinal 0 é CTRL_C_EVENT e encerraria o script do Matheus.
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        alca = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION, só consulta
        if not alca:
            return ctypes.get_last_error() == 5  # acesso negado: o processo existe
        try:
            codigo = wintypes.DWORD()
            return bool(kernel32.GetExitCodeProcess(alca, ctypes.byref(codigo))) and codigo.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(alca)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


# ---------- leitura do script (só leitura) ----------

def ler_anuncio(pasta: Path) -> dict | None:
    try:
        dados = json.loads((Path(pasta) / ARQUIVO_ANUNCIO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dados if isinstance(dados, dict) else None


def abrir_so_leitura(banco: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{Path(banco).resolve().as_uri()}?mode=ro", uri=True, timeout=2)


ESQUEMA = """
CREATE TABLE IF NOT EXISTS sessoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL UNIQUE,
    chave TEXT NOT NULL UNIQUE,
    origem TEXT NOT NULL CHECK (origem IN ('anuncio', 'processo')),
    programa TEXT,
    pid INTEGER,
    camera TEXT,
    pasta TEXT,
    iniciado_em TEXT NOT NULL,
    ultimo_sinal TEXT,
    encerrado_em TEXT,
    criado_em TEXT NOT NULL,
    alterado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL UNIQUE,
    evento_uid TEXT NOT NULL UNIQUE,
    sessao_uid TEXT,
    tipo TEXT NOT NULL,
    risco INTEGER NOT NULL,
    duracao_s REAL,
    detalhes TEXT,
    ocorrido_em TEXT NOT NULL,
    origem TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    alterado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_eventos_sessao ON eventos (sessao_uid);
CREATE TABLE IF NOT EXISTS fontes (
    caminho TEXT PRIMARY KEY,
    uid TEXT NOT NULL UNIQUE,
    ultimo_rowid INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL,
    alterado_em TEXT NOT NULL
);
"""


class ScriptLocal:
    def __init__(self, pasta_dados_painel: Path, pastas_do_script: list[Path] | None = None,
                 relogio: Callable[[], datetime] | None = None,
                 listar_processos: Callable[[], list[Processo]] | None = None,
                 pid_vivo: Callable[[int], bool] | None = None,
                 intervalo_s: float = INTERVALO_VIGIA_S, cache_processos_s: float = 2.5):
        self._pasta_painel = Path(pasta_dados_painel)
        self._pastas = [Path(p) for p in (pastas_do_script if pastas_do_script is not None else pastas_padrao_do_script())]
        self._relogio = relogio or (lambda: datetime.now(timezone.utc))
        self._listar = listar_processos or listar_processos_do_sistema
        self._pid_vivo = pid_vivo or pid_vivo_do_sistema
        self._intervalo = intervalo_s
        self._cache_s = cache_processos_s
        self._cache: tuple[float, list[Processo]] | None = None
        self._vistos: dict[int, str] = {}
        self._trava = threading.RLock()
        self._parar = threading.Event()
        self._linha: threading.Thread | None = None
        self._conexao: sqlite3.Connection | None = None

    # ----- banco do painel -----

    def _db(self) -> sqlite3.Connection:
        if self._conexao is None:
            self._pasta_painel.mkdir(parents=True, exist_ok=True)
            conexao = sqlite3.connect(str(self._pasta_painel / ARQUIVO_CAPTURAS), timeout=10, check_same_thread=False,
                                      isolation_level=None)
            conexao.row_factory = sqlite3.Row
            conexao.execute("PRAGMA journal_mode=WAL")
            conexao.executescript(ESQUEMA)
            self._conexao = conexao
        return self._conexao

    def _agora(self) -> datetime:
        agora = self._relogio()
        return agora if agora.tzinfo else agora.replace(tzinfo=timezone.utc)

    # ----- aberto? -----

    def _processos(self) -> list[Processo]:
        if self._cache is not None and time.monotonic() - self._cache[0] < self._cache_s:
            return self._cache[1]
        lista = [p for p in self._listar() if eh_processo_do_script(p)]
        self._cache = (time.monotonic(), lista)
        return lista

    def _pasta_com_eventos(self) -> Path | None:
        existentes = [p for p in self._pastas if (p / ARQUIVO_EVENTOS).is_file()]
        if not existentes:
            return None
        return max(existentes, key=lambda p: (p / ARQUIVO_EVENTOS).stat().st_mtime)

    def _detectar(self) -> dict:
        agora = self._agora()
        melhor = None
        for pasta in self._pastas:
            anuncio = ler_anuncio(pasta)
            if anuncio is None:
                continue
            sinal = _ler_iso(anuncio.get("ultimo_sinal"))
            pid = anuncio.get("pid")
            if sinal is None or not isinstance(pid, int):
                continue
            idade = (agora - sinal).total_seconds()
            if not -SINAL_MAX_S < idade < SINAL_MAX_S or not self._pid_vivo(pid):
                continue
            if melhor is None or sinal > _ler_iso(melhor[1]["ultimo_sinal"]):
                melhor = (pasta, anuncio)
        if melhor is not None:
            pasta, anuncio = melhor
            iniciado = _ler_iso(anuncio.get("iniciado_em")) or _ler_iso(anuncio["ultimo_sinal"])
            self._vistos.clear()
            return {"aberto": True, "origem": "anuncio",
                    "chave": f"anuncio:{anuncio.get('sessao') or anuncio['pid']}:{_iso(iniciado)}",
                    "programa": anuncio.get("programa") or "RotaGuard", "pid": anuncio["pid"], "desde": _iso(iniciado),
                    "camera": anuncio.get("camera"), "ultimo_sinal": _iso(_ler_iso(anuncio["ultimo_sinal"])),
                    "pasta": str(pasta)}
        processos = self._processos()
        if processos:
            processo = processos[0]
            self._vistos = {p.pid: self._vistos.get(p.pid, _iso(agora)) for p in processos}
            desde = self._vistos[processo.pid]
            pasta = self._pasta_com_eventos() or (self._pastas[0] if self._pastas else None)
            programa = "RotaGuard Teste" if processo.nome.lower() in EXECUTAVEIS else "RotaGuard (Python)"
            return {"aberto": True, "origem": "processo", "chave": f"processo:{processo.pid}:{desde}",
                    "programa": programa, "pid": processo.pid, "desde": desde, "camera": None,
                    "ultimo_sinal": _iso(agora), "pasta": str(pasta) if pasta else None}
        self._vistos.clear()
        pasta = self._pasta_com_eventos()
        return {"aberto": False, "origem": None, "chave": None, "programa": None, "pid": None, "desde": None,
                "camera": None, "ultimo_sinal": None, "pasta": str(pasta) if pasta else None}

    def _atualizar_sessao(self, achado: dict) -> str | None:
        db = self._db()
        agora = _iso(self._agora())
        if not achado["aberto"]:
            db.execute("UPDATE sessoes SET encerrado_em = COALESCE(ultimo_sinal, ?), alterado_em = ? "
                       "WHERE encerrado_em IS NULL", (agora, agora))
            return None
        chave = achado["chave"]
        db.execute("UPDATE sessoes SET encerrado_em = COALESCE(ultimo_sinal, ?), alterado_em = ? "
                   "WHERE encerrado_em IS NULL AND chave != ?", (agora, agora, chave))
        linha = db.execute("SELECT uid FROM sessoes WHERE chave = ?", (chave,)).fetchone()
        if linha is None:
            uid = uuid.uuid4().hex
            db.execute(
                "INSERT INTO sessoes (uid, chave, origem, programa, pid, camera, pasta, iniciado_em, ultimo_sinal,"
                " criado_em, alterado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, chave, achado["origem"], achado["programa"], achado["pid"], achado["camera"], achado["pasta"],
                 achado["desde"], achado["ultimo_sinal"], agora, agora))
            return uid
        db.execute("UPDATE sessoes SET camera = ?, ultimo_sinal = ?, encerrado_em = NULL, alterado_em = ? WHERE chave = ?",
                   (achado["camera"], achado["ultimo_sinal"], agora, chave))
        return linha["uid"]

    def estado(self) -> dict:
        """ScriptEstado do contrato: aberto, programa, desde, pid, camera, ultimo_sinal, eventos, pasta."""
        with self._trava:
            achado = self._detectar()
            sessao = self._atualizar_sessao(achado)
            db = self._db()
            if sessao is None:
                ultima = db.execute("SELECT uid, ultimo_sinal FROM sessoes ORDER BY iniciado_em DESC LIMIT 1").fetchone()
                sessao = ultima["uid"] if ultima else None
                if ultima is not None:
                    achado["ultimo_sinal"] = ultima["ultimo_sinal"]
            eventos = db.execute("SELECT COUNT(*) FROM eventos WHERE sessao_uid = ?", (sessao,)).fetchone()[0] if sessao else 0
            achado["eventos"] = int(eventos)
            return {chave: achado[chave] for chave in CHAVES_ESTADO}

    # ----- captura -----

    def _sessao_do_evento(self, ocorrido_em: str) -> str | None:
        instante = _ler_iso(ocorrido_em)
        if instante is None:
            return None
        linha = self._db().execute(
            "SELECT uid FROM sessoes WHERE iniciado_em <= ? AND (encerrado_em IS NULL OR encerrado_em >= ?) "
            "ORDER BY iniciado_em DESC LIMIT 1",
            (_iso(instante + timedelta(seconds=2)), _iso(instante - timedelta(seconds=SINAL_MAX_S)))).fetchone()
        return linha["uid"] if linha else None

    def _capturar_de(self, banco: Path) -> int:
        db = self._db()
        caminho = str(banco.resolve())
        agora = _iso(self._agora())
        fonte = db.execute("SELECT ultimo_rowid FROM fontes WHERE caminho = ?", (caminho,)).fetchone()
        if fonte is None:
            db.execute("INSERT INTO fontes (caminho, uid, ultimo_rowid, criado_em, alterado_em) VALUES (?, ?, 0, ?, ?)",
                       (caminho, uuid.uuid4().hex, agora, agora))
            ultimo = 0
        else:
            ultimo = int(fonte["ultimo_rowid"])
        novos = 0
        while True:
            try:
                origem = abrir_so_leitura(banco)
            except sqlite3.Error as exc:
                logger.debug("Fila do script indisponível (%s): %s", banco, exc)
                return novos
            try:
                maximo = origem.execute("SELECT COALESCE(MAX(rowid), 0) FROM events").fetchone()[0]
                if maximo < ultimo:  # fila recriada (dados apagados no app de teste): a chave pelo uid evita duplicar
                    ultimo = 0
                linhas = origem.execute(
                    "SELECT rowid, event_uid, alert_type, risk_level, duration, details, occurred_at FROM events "
                    "WHERE rowid > ? ORDER BY rowid LIMIT ?", (ultimo, LOTE)).fetchall()
            except sqlite3.Error as exc:  # tabela ainda não criada ou banco ocupado: tenta de novo na próxima volta
                logger.debug("Leitura da fila do script falhou (%s): %s", banco, exc)
                return novos
            finally:
                origem.close()
            if not linhas:
                if maximo < int(fonte["ultimo_rowid"] if fonte is not None else 0):
                    db.execute("UPDATE fontes SET ultimo_rowid = ?, alterado_em = ? WHERE caminho = ?", (ultimo, agora, caminho))
                return novos
            for rowid, evento_uid, tipo, risco, duracao, detalhes, ocorrido_em in linhas:
                cursor = db.execute(
                    "INSERT OR IGNORE INTO eventos (uid, evento_uid, sessao_uid, tipo, risco, duracao_s, detalhes,"
                    " ocorrido_em, origem, criado_em, alterado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (uuid.uuid4().hex, evento_uid, self._sessao_do_evento(ocorrido_em), tipo, int(risco),
                     None if duracao is None else float(duracao), detalhes, _iso(_ler_iso(ocorrido_em) or self._agora()),
                     caminho, agora, agora))
                novos += max(cursor.rowcount, 0)
                ultimo = rowid
            db.execute("UPDATE fontes SET ultimo_rowid = ?, alterado_em = ? WHERE caminho = ?", (ultimo, agora, caminho))
            fonte = {"ultimo_rowid": ultimo}
            if len(linhas) < LOTE:
                return novos

    def capturar(self) -> int:
        """Copia os eventos novos do script para capturas.db. Devolve quantos entraram."""
        with self._trava:
            self._atualizar_sessao(self._detectar())
            novos = 0
            for pasta in self._pastas:
                banco = pasta / ARQUIVO_EVENTOS
                if banco.is_file():
                    novos += self._capturar_de(banco)
            return novos

    def eventos(self, desde_id: int = 0) -> list[dict]:
        """EventoScript[] com id maior que desde_id, na ordem em que foram capturados."""
        with self._trava:
            if self._linha is None or not self._linha.is_alive():
                self.capturar()
            linhas = self._db().execute(
                "SELECT id, ocorrido_em, tipo, risco, duracao_s, sessao_uid FROM eventos WHERE id > ? ORDER BY id LIMIT ?",
                (int(desde_id or 0), LOTE)).fetchall()
        return [{"id": linha["id"], "em": linha["ocorrido_em"], "tipo": linha["tipo"], "risco": linha["risco"],
                 "duracao_s": linha["duracao_s"], "sessao": linha["sessao_uid"]} for linha in linhas]

    # ----- vigia -----

    def iniciar(self) -> None:
        if self._linha is not None and self._linha.is_alive():
            return
        self._parar.clear()
        self._linha = threading.Thread(target=self._vigiar, name="rotaguard-script-local", daemon=True)
        self._linha.start()

    def _vigiar(self) -> None:
        while not self._parar.is_set():
            try:
                self.capturar()
            except Exception:  # a vigia nunca derruba o painel
                logger.exception("Falha ao capturar os eventos do script local.")
            self._parar.wait(self._intervalo)

    def parar(self) -> None:
        self._parar.set()
        if self._linha is not None:
            self._linha.join(timeout=5)
        with self._trava:
            if self._conexao is not None:
                self._conexao.close()
                self._conexao = None
