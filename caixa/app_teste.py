"""RotaGuard Teste: o script da caixa num app, para testar a detecção com a câmera de qualquer computador (spec 010).

Sem argumentos abre a tela de início. Com "--monitor" (ou com qualquer argumento) roda o monitoramento com esses
argumentos, no mesmo formato do run_monitor.py. A tela de início chama o próprio executável com "--monitor" num
processo separado, para a janela do OpenCV e a do Tkinter não disputarem a linha principal (exigência do macOS).

Exemplos fora do pacote:
  python caixa/app_teste.py
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

import textos_legais

NOME_APP = "RotaGuard Teste"
ROTULO_LEGAL = "Privacidade, LGPD e termos"
ARQUIVO_REGISTRO = "registro-teste.log"
CAMERAS = ("Automática (recomendado)", "Câmera 1", "Câmera 2", "Câmera 3", "Câmera 4")
# Sem imagem por 15 s o teste termina com aviso, em vez de ficar esperando sem janela.
ESPERA_CAMERA_S = 15
SAIDA_SEM_CAMERA = 3  # o mesmo de run_monitor.SAIDA_SEM_CAMERA; a tela não importa o monitor
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


def pasta_dados(sistema: str | None = None, ambiente: Mapping[str, str] | None = None, home: Path | None = None) -> Path:
    """Pasta do usuário para fila de eventos, perfis e registro. Nunca ao lado do programa (pode ser só leitura)."""
    sistema = sys.platform if sistema is None else sistema
    ambiente = os.environ if ambiente is None else ambiente
    home = Path.home() if home is None else home
    if sistema.startswith("win"):
        base = Path(ambiente["LOCALAPPDATA"]) if ambiente.get("LOCALAPPDATA") else home / "AppData" / "Local"
        return base / "RotaGuard" / "Teste"
    if sistema == "darwin":
        return home / "Library" / "Application Support" / "RotaGuard" / "Teste"
    base = Path(ambiente["XDG_DATA_HOME"]) if ambiente.get("XDG_DATA_HOME") else home / ".local" / "share"
    return base / "rotaguard" / "teste"


def argumentos_monitor(opcoes: OpcoesTeste, pasta: Path) -> list[str]:
    argumentos = [
        "--camera", str(opcoes.camera),
        "--window",
        "--sem-servidor",
        "--data-dir", str(pasta),
        "--driver-key", "teste",
        "--camera-ir", opcoes.camera_ir,
        "--espera-camera", str(ESPERA_CAMERA_S),
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
    """Em que ponto está o teste, pelo registro escrito desde o clique em Iniciar."""
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


def rodar_monitor(argumentos: list[str]) -> int:
    pasta = pasta_do_argumento(argumentos)
    if pasta is None:
        pasta = pasta_dados()
        argumentos = [*argumentos, "--data-dir", str(pasta)]
    caminho = configurar_registro(pasta)
    if sys.stdout is None or sys.stderr is None:
        fluxo = open(caminho, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - fica aberto até o processo sair
        sys.stdout = sys.stdout or fluxo
        sys.stderr = sys.stderr or fluxo
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


def apagar_dados(pasta: Path) -> int:
    """Eliminação dos dados (LGPD, art. 18): apaga eventos, registro, sirene e perfis da pasta do teste.
    Só aceita a pasta do app (.../RotaGuard/Teste ou .../rotaguard/teste), que continua existindo, vazia."""
    if pasta.name.lower() != "teste" or pasta.parent.name.lower() != "rotaguard":
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


class TelaInicio:
    VERDE = "#103e31"
    LIMA = "#d5f669"
    PAPEL = "#fafcf7"
    CINZA = "#5c6a59"

    def __init__(self, tk, ttk, filedialog, messagebox):
        self.tk, self.ttk, self.filedialog, self.messagebox = tk, ttk, filedialog, messagebox
        self.processo: subprocess.Popen | None = None
        self._janela_legal = None
        self._inicio_registro = 0
        self._fase: str | None = None
        self.pasta = pasta_dados()
        self.raiz = tk.Tk()
        self.raiz.title(NOME_APP)
        self.raiz.configure(bg=self.PAPEL, padx=26, pady=22)
        self.raiz.resizable(False, False)
        icone = caminho_recurso("rotaguard.png")
        if icone.exists():
            try:
                self._icone = tk.PhotoImage(file=str(icone))
                self.raiz.iconphoto(True, self._icone)
            except tk.TclError:
                pass
        self.camera = tk.StringVar(value=CAMERAS[0])
        self.celular = tk.BooleanVar(value=True)
        self.som = tk.BooleanVar(value=True)
        self.calibracao_rapida = tk.BooleanVar(value=True)
        self.camera_ir = tk.StringVar(value="auto")
        self.status = tk.StringVar(value="Pronto para testar.")
        self._montar()
        self.raiz.protocol("WM_DELETE_WINDOW", self._fechar)

    def _rotulo(self, pai, texto, tamanho=10, cor=None, negrito=False, **opcoes):
        fonte = ("Segoe UI" if sys.platform.startswith("win") else "Helvetica", tamanho, "bold" if negrito else "normal")
        return self.tk.Label(pai, text=texto, font=fonte, bg=self.PAPEL, fg=cor or self.VERDE, justify="left", **opcoes)

    def _montar(self):
        tk = self.tk
        self._rotulo(self.raiz, "rotaguard", 22, negrito=True).grid(row=0, column=0, columnspan=3, sticky="w")
        self._rotulo(self.raiz, "Teste da câmera neste computador", 11, cor=self.CINZA).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))
        self._rotulo(
            self.raiz,
            "Roda o script do RotaGuard com a câmera deste computador: sinais de sono e uso de celular, "
            "com alarme sonoro. Nada é enviado para servidor.",
            10, cor=self.CINZA, wraplength=400,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 16))

        self._rotulo(self.raiz, "Câmera", negrito=True).grid(row=3, column=0, sticky="w")
        self.lista_cameras = self.ttk.Combobox(self.raiz, textvariable=self.camera, values=CAMERAS, width=28)
        self.lista_cameras.grid(row=3, column=1, sticky="w", padx=(10, 0))
        tk.Button(self.raiz, text="Vídeo gravado…", command=self._escolher_video, relief="flat", bg="#e7ede3",
                  fg=self.VERDE, activebackground=self.LIMA, padx=8).grid(row=3, column=2, sticky="w", padx=(8, 0))

        linha = 4
        for texto, variavel in (("Detectar uso de celular", self.celular), ("Som do alarme", self.som),
                                ("Calibração rápida (1 a 2 min)", self.calibracao_rapida)):
            tk.Checkbutton(self.raiz, text=texto, variable=variavel, bg=self.PAPEL, fg=self.VERDE,
                           activebackground=self.PAPEL, selectcolor="white", anchor="w").grid(
                row=linha, column=0, columnspan=3, sticky="w", pady=(8 if linha == 4 else 2, 0))
            linha += 1
        self._rotulo(self.raiz, "Câmera infravermelha").grid(row=linha, column=0, sticky="w", pady=(8, 0))
        self.ttk.Combobox(self.raiz, textvariable=self.camera_ir, values=("auto", "sim", "nao"), width=8,
                          state="readonly").grid(row=linha, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        linha += 1

        self.botao = tk.Button(self.raiz, text="Iniciar teste  ↗", command=self._iniciar, bg=self.VERDE, fg=self.PAPEL,
                               activebackground="#285641", activeforeground=self.PAPEL, relief="flat",
                               font=("Segoe UI" if sys.platform.startswith("win") else "Helvetica", 11, "bold"),
                               padx=16, pady=10, cursor="hand2")
        self.botao.grid(row=linha, column=0, columnspan=3, sticky="we", pady=(20, 6))
        linha += 1
        self._rotulo(self.raiz, "Na janela da câmera: Q ou Esc encerra · C recalibra", 9, cor=self.CINZA).grid(
            row=linha, column=0, columnspan=3, sticky="w")
        linha += 1
        self._rotulo(self.raiz, "", 10, textvariable=self.status, wraplength=400).grid(
            row=linha, column=0, columnspan=3, sticky="w", pady=(12, 4))
        linha += 1
        self.detalhes = tk.Text(self.raiz, height=8, width=58, font=("Consolas" if sys.platform.startswith("win") else "Menlo", 8),
                                bg="#f0f4ed", fg=self.VERDE, relief="flat", wrap="word")
        self.detalhes.grid(row=linha, column=0, columnspan=3, sticky="we")
        self.detalhes.grid_remove()
        linha += 1
        rodape = tk.Frame(self.raiz, bg=self.PAPEL)
        rodape.grid(row=linha, column=0, columnspan=3, sticky="we", pady=(8, 0))
        for texto, comando, lado in (("Abrir pasta de registros", lambda: abrir_pasta(self.pasta), "left"),
                                     (ROTULO_LEGAL, self._abrir_legal, "right")):
            tk.Button(rodape, text=texto, command=comando, relief="flat", bg=self.PAPEL, fg=self.VERDE,
                      activebackground=self.LIMA, cursor="hand2").pack(side=lado)

    def _abrir_legal(self):
        """Seção só para consulta (pedido de 14/09/2026): nada aqui bloqueia ou condiciona o uso do app."""
        if self._janela_legal is not None and self._janela_legal.winfo_exists():
            self._janela_legal.lift()
            return
        tk, ttk = self.tk, self.ttk
        janela = self._janela_legal = tk.Toplevel(self.raiz)
        janela.title(f"{NOME_APP} · {ROTULO_LEGAL}")
        janela.configure(bg=self.PAPEL, padx=16, pady=14)
        janela.geometry("760x580")
        abas = ttk.Notebook(janela)
        abas.pack(fill="both", expand=True)
        fonte = ("Segoe UI" if sys.platform.startswith("win") else "Helvetica", 10)
        for titulo, conteudo in textos_legais.secoes(self.pasta, avisos_de_terceiros()):
            quadro = tk.Frame(abas, bg=self.PAPEL)
            barra = tk.Scrollbar(quadro)
            barra.pack(side="right", fill="y")
            texto = tk.Text(quadro, wrap="word", font=fonte, bg="white", fg="#1d2a24", relief="flat", padx=14, pady=12,
                            yscrollcommand=barra.set)
            texto.insert("1.0", conteudo)
            texto.configure(state="disabled")
            texto.pack(side="left", fill="both", expand=True)
            barra.configure(command=texto.yview)
            abas.add(quadro, text=titulo)
        botoes = tk.Frame(janela, bg=self.PAPEL)
        botoes.pack(fill="x", pady=(10, 0))
        for texto, comando in (("Abrir pasta de dados", lambda: abrir_pasta(self.pasta)),
                               ("Apagar dados deste computador", self._apagar_dados)):
            tk.Button(botoes, text=texto, command=comando, relief="flat", bg="#e7ede3", fg=self.VERDE,
                      activebackground=self.LIMA, padx=10, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(botoes, text="Fechar", command=janela.destroy, relief="flat", bg=self.VERDE, fg=self.PAPEL,
                  activebackground="#285641", activeforeground=self.PAPEL, padx=14, cursor="hand2").pack(side="right")

    def _apagar_dados(self):
        janela = self._janela_legal
        pai = janela if janela is not None and janela.winfo_exists() else self.raiz
        if self.processo is not None and self.processo.poll() is None:
            self.messagebox.showinfo(NOME_APP, "Encerre o teste antes de apagar os dados.", parent=pai)
            return
        if not self.messagebox.askyesno(NOME_APP, f"Apagar eventos, registro e demais arquivos do teste em\n{self.pasta}?",
                                        parent=pai):
            return
        try:
            removidos = apagar_dados(self.pasta)
        except (OSError, ValueError) as exc:
            self.messagebox.showerror(NOME_APP, f"Não foi possível apagar: {exc}", parent=pai)
            return
        self.messagebox.showinfo(NOME_APP, f"Pronto: {removidos} arquivo(s) apagado(s).", parent=pai)

    def _escolher_video(self):
        caminho = self.filedialog.askopenfilename(
            title="Escolher vídeo gravado",
            filetypes=[("Vídeos", "*.mp4 *.avi *.mov *.mkv *.webm"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.camera.set(caminho)

    def _opcoes(self) -> OpcoesTeste:
        return OpcoesTeste(camera=camera_escolhida(self.camera.get()), celular=self.celular.get(), som=self.som.get(),
                           calibracao_rapida=self.calibracao_rapida.get(), camera_ir=self.camera_ir.get())

    def _iniciar(self):
        if self.processo is not None:
            return
        registro = self.pasta / ARQUIVO_REGISTRO
        self._inicio_registro = registro.stat().st_size if registro.exists() else 0
        self._fase = None
        comando = comando_monitor(argumentos_monitor(self._opcoes(), self.pasta))
        opcoes = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform.startswith("win") else {}
        try:
            self.processo = subprocess.Popen(comando, **opcoes)
        except OSError as exc:
            self.status.set(f"Não foi possível iniciar o teste: {exc}")
            return
        self.detalhes.grid_remove()
        self.botao.configure(state="disabled", text="Teste em andamento…")
        self.status.set("Procurando a câmera e carregando a detecção. A janela do teste abre em alguns segundos.")
        self.raiz.after(500, self._acompanhar)

    def _acompanhar(self):
        if self.processo is None:
            return
        codigo = self.processo.poll()
        if codigo is None:
            fase = fase_do_registro(texto_desde(self.pasta / ARQUIVO_REGISTRO, self._inicio_registro))
            if fase is not None and fase != self._fase:
                self._fase = fase
                self.status.set(FASES[fase])
            self.raiz.after(500, self._acompanhar)
            return
        self.processo = None
        self.botao.configure(state="normal", text="Iniciar teste  ↗")
        self.status.set(mensagem_saida(codigo))
        if codigo == 0:
            return
        self.detalhes.configure(state="normal")
        self.detalhes.delete("1.0", "end")
        self.detalhes.insert("1.0", ultimas_linhas(self.pasta / ARQUIVO_REGISTRO) or "Registro vazio.")
        self.detalhes.configure(state="disabled")
        self.detalhes.grid()

    def _fechar(self):
        if self.processo is not None and self.processo.poll() is None:
            self.processo.terminate()
        self.raiz.destroy()

    def executar(self):
        self.raiz.mainloop()


def abrir_tela_inicio() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print("Tela de início indisponível (Tkinter ausente). Use: --monitor --camera 0 --window --sem-servidor")
        return 2
    TelaInicio(tk, ttk, filedialog, messagebox).executar()
    return 0


def main(argv: list[str] | None = None, rodar: Callable[[list[str]], int] = rodar_monitor,
         tela: Callable[[], int] = abrir_tela_inicio) -> int:
    argumentos = sys.argv[1:] if argv is None else list(argv)
    if not argumentos:
        return tela()
    if argumentos[0] == "--monitor":
        argumentos = argumentos[1:]
    return rodar(argumentos)


if __name__ == "__main__":
    sys.exit(main())
