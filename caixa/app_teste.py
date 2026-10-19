"""RotaGuard Script (antes RotaGuard Teste, spec 031): o script da caixa num app, para testar a detecção com a câmera de qualquer computador (spec 010).

Sem argumentos abre a tela nova (spec 023): uma janela HTML do pywebview (sem ele, o navegador padrão) servida por um
servidor só em 127.0.0.1, com o monitoramento numa thread deste processo e a malha do rosto desenhada no vídeo.
Com "--monitor" (ou com qualquer argumento) roda o monitoramento direto, no mesmo formato do run_monitor.py.
"--janela-opencv" sozinho roda o teste na janela antiga do OpenCV, com as opções padrão do app.

Exemplos fora do pacote:
  python caixa/app_teste.py
  python caixa/app_teste.py --janela-opencv
  python caixa/app_teste.py --monitor --camera 0 --window --sem-servidor
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

NOME_APP = "RotaGuard Script"
ROTULO_LEGAL = "Privacidade, LGPD e termos"
ARQUIVO_REGISTRO = "registro-teste.log"
CAMERAS = ("Automática (recomendado)", "Câmera 1", "Câmera 2", "Câmera 3", "Câmera 4")
# Sem imagem por 15 s o teste termina com aviso, em vez de ficar esperando sem janela.
ESPERA_CAMERA_S = 15
SAIDA_SEM_CAMERA = 3  # o mesmo de run_monitor.SAIDA_SEM_CAMERA; este arquivo não importa o monitor no início
FASES = {
    "camera": "Câmera encontrada. Abrindo a janela do teste…",
    "rodando": "Teste em andamento. Na janela da câmera: Q ou Esc encerra, C recalibra.",
}


@dataclass
class OpcoesTeste:
    camera: str = "auto"
    celular: bool = True
    som: bool = True
    calibracao_rapida: bool = True
    camera_ir: str = "auto"
    # Frequência cardíaca pela câmera (spec 022): ligada no app de teste, desligada na caixa.
    cardio: bool = True


def pasta_dados(sistema: str | None = None, ambiente: Mapping[str, str] | None = None, home: Path | None = None) -> Path:
    """Pasta do usuário para fila de eventos, perfis e registro. Nunca ao lado do programa (pode ser só leitura)."""
    sistema = sys.platform if sistema is None else sistema
    ambiente = os.environ if ambiente is None else ambiente
    home = Path.home() if home is None else home
    if sistema.startswith("win"):
        base = Path(ambiente["LOCALAPPDATA"]) if ambiente.get("LOCALAPPDATA") else home / "AppData" / "Local"
        return base / "RotaGuard" / "Script"
    if sistema == "darwin":
        return home / "Library" / "Application Support" / "RotaGuard" / "Script"
    base = Path(ambiente["XDG_DATA_HOME"]) if ambiente.get("XDG_DATA_HOME") else home / ".local" / "share"
    return base / "rotaguard" / "script"


def argumentos_monitor(opcoes: OpcoesTeste, pasta: Path, janela: bool = True) -> list[str]:
    """Linha do run_monitor para as opções do app. janela=False: a tela nova mostra o vídeo, sem janela do OpenCV."""
    argumentos = [
        "--camera", str(opcoes.camera),
        "--window" if janela else "--no-window",
        "--sem-servidor",
        "--data-dir", str(pasta),
        "--driver-key", "teste",
        "--camera-ir", opcoes.camera_ir,
        "--espera-camera", str(ESPERA_CAMERA_S),
        "--cardio" if opcoes.cardio else "--sem-cardio",
    ]
    if not opcoes.celular:
        argumentos.append("--sem-celular")
    if not opcoes.som:
        argumentos.append("--mute")
    if opcoes.calibracao_rapida:
        # No teste, 1 a 2 min de calibração bastam para ver os níveis de sonolência; o microssono vale desde o início.
        argumentos += ["--calibration-min", "60", "--calibration-max", "120"]
    return argumentos


def camera_escolhida(texto: str) -> str:
    """Texto da lista de câmeras → valor de --camera: "auto", índice ("Câmera 1" é o 0) ou caminho de vídeo."""
    texto = (texto or "").strip()
    if not texto or texto.lower().startswith("autom"):
        return "auto"
    numero = re.fullmatch(r"c[aâ]mera\s+(\d+)", texto, re.IGNORECASE)
    if numero:
        return str(max(int(numero.group(1)) - 1, 0))
    return texto


def mensagem_saida(codigo: int) -> str:
    if codigo == 0:
        return "Teste encerrado. O registro fica na pasta de registros."
    if codigo == SAIDA_SEM_CAMERA:
        return ("Nenhuma câmera respondeu. Confira se ela está conectada e se outro programa (Teams, Zoom, navegador) "
                "não está usando. Depois clique em Iniciar teste de novo.")
    return f"O teste terminou com erro (código {codigo}). Últimas linhas do registro:"


def fase_do_registro(texto: str) -> str | None:
    """Em que ponto está o teste, pelo registro escrito desde o clique em Iniciar (monitor em outro processo)."""
    if "Monitoramento iniciado" in texto:
        return "rodando"
    if "Câmera aberta" in texto or "Câmera encontrada" in texto:
        return "camera"
    return None


def texto_desde(caminho: Path, inicio: int, limite: int = 262_144) -> str:
    try:
        with open(caminho, "rb") as arquivo:
            arquivo.seek(inicio)
            return arquivo.read(limite).decode("utf-8", errors="replace")
    except OSError:
        return ""


def comando_monitor(argumentos: list[str], congelado: bool | None = None, executavel: str | None = None) -> list[str]:
    congelado = bool(getattr(sys, "frozen", False)) if congelado is None else congelado
    executavel = sys.executable if executavel is None else executavel
    if congelado:
        return [executavel, "--monitor", *argumentos]
    return [executavel, str(Path(__file__).resolve()), "--monitor", *argumentos]


def pasta_do_argumento(argumentos: list[str]) -> Path | None:
    for i, argumento in enumerate(argumentos):
        if argumento == "--data-dir" and i + 1 < len(argumentos):
            return Path(argumentos[i + 1])
        if argumento.startswith("--data-dir="):
            return Path(argumento.split("=", 1)[1])
    return None


def configurar_registro(pasta: Path) -> Path:
    """Registro em arquivo (e na tela, quando houver console). Executável de janela não tem stdout nem stderr."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / ARQUIVO_REGISTRO
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    raiz = logging.getLogger()
    arquivo = logging.FileHandler(caminho, encoding="utf-8")
    arquivo.setFormatter(formato)
    raiz.addHandler(arquivo)
    if sys.stderr is not None:
        tela = logging.StreamHandler()
        tela.setFormatter(formato)
        raiz.addHandler(tela)
    raiz.setLevel(logging.INFO)
    return caminho


def preparar_registro(pasta: Path) -> Path:
    caminho = configurar_registro(pasta)
    if sys.stdout is None or sys.stderr is None:
        fluxo = open(caminho, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - fica aberto até o processo sair
        sys.stdout = sys.stdout or fluxo
        sys.stderr = sys.stderr or fluxo
    return caminho


def rodar_monitor(argumentos: list[str]) -> int:
    pasta = pasta_do_argumento(argumentos)
    if pasta is None:
        pasta = pasta_dados_do_app()
        argumentos = [*argumentos, "--data-dir", str(pasta)]
    preparar_registro(pasta)
    import run_monitor

    return int(run_monitor.main(argumentos) or 0)


def abrir_pasta(pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(pasta)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(pasta)])
    else:
        subprocess.Popen(["xdg-open", str(pasta)])


def ultimas_linhas(caminho: Path, quantidade: int = 14) -> str:
    try:
        with open(caminho, encoding="utf-8", errors="replace") as arquivo:
            return "".join(deque(arquivo, maxlen=quantidade))
    except OSError:
        return ""


def avisos_de_terceiros() -> str:
    """THIRD_PARTY_NOTICES.md: dentro do pacote (datas do .spec) ou na raiz do repositório."""
    for caminho in (caminho_recurso("THIRD_PARTY_NOTICES.md"),
                    Path(__file__).resolve().parents[1] / "THIRD_PARTY_NOTICES.md"):
        if caminho.exists():
            return caminho.read_text(encoding="utf-8")
    return ""


def migrar_pasta_antiga(nova: Path) -> bool:
    """Spec 031 (NOM-04): o app se chamava RotaGuard Teste e guardava tudo em .../RotaGuard/Teste. Se só a pasta antiga
    existe, ela vira a nova (eventos, resumos, trechos e a conexão com a empresa vão juntos). Com as duas, nada muda.
    Falha (pasta em uso, sem permissão) nunca impede o app de abrir: ele segue com a pasta nova."""
    antiga = nova.with_name("teste" if nova.name.islower() else "Teste")
    try:
        if nova.exists() or not antiga.is_dir():
            return False
        os.replace(antiga, nova)
        return True
    except OSError:
        return False


def pasta_dados_do_app() -> Path:
    """Pasta de dados de verdade (não nos testes): já com a pasta antiga trazida para o nome novo."""
    pasta = pasta_dados()
    migrar_pasta_antiga(pasta)
    return pasta


def apagar_dados(pasta: Path) -> int:
    """Eliminação dos dados (LGPD, art. 18): apaga eventos, registro, sirene, resumos e perfis da pasta do teste.
    Só aceita a pasta do app (.../RotaGuard/Script, ou a antiga .../RotaGuard/Teste), que continua existindo, vazia."""
    if pasta.name.lower() not in ("script", "teste") or pasta.parent.name.lower() != "rotaguard":
        raise ValueError(f"pasta inesperada para apagar: {pasta}")
    if not pasta.exists():
        return 0
    removidos = 0
    for item in sorted(pasta.rglob("*"), key=lambda caminho: len(caminho.parts), reverse=True):
        if item.is_dir() and not item.is_symlink():
            item.rmdir()
        else:
            item.unlink()
            removidos += 1
    return removidos


def caminho_recurso(nome: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1] / "implantacao" / "app-teste"))
    return base / nome


def abrir_tela_teste(pasta: Path | None = None) -> int:
    """Tela nova (spec 023). O registro vai para registro-teste.log, como no monitor."""
    pasta = pasta_dados_do_app() if pasta is None else pasta
    preparar_registro(pasta)
    from tela_teste.app import executar

    return executar(pasta)


def verificar_tela(pasta: Path) -> int:
    """Teste de fumaça da tela (build.py, TEL-16): sobe o servidor sem janela e confere as rotas. 0 = tudo certo."""
    preparar_registro(pasta)
    from tela_teste.app import verificar

    return verificar(pasta)


def main(argv: list[str] | None = None, rodar: Callable[[list[str]], int] = rodar_monitor,
         tela: Callable[[], int] = abrir_tela_teste, verificar: Callable[[Path], int] = verificar_tela) -> int:
    argumentos = sys.argv[1:] if argv is None else list(argv)
    if not argumentos:
        return tela()
    if argumentos[0] == "--verificar-tela":
        return verificar(pasta_do_argumento(argumentos[1:]) or pasta_dados())
    if argumentos == ["--janela-opencv"]:
        return rodar(argumentos_monitor(OpcoesTeste(), pasta_dados_do_app(), janela=True))
    if argumentos[0] == "--monitor":
        argumentos = argumentos[1:]
    return rodar(argumentos)


if __name__ == "__main__":
    sys.exit(main())
