"""Alarme sonoro em quatro sinais, com preempção: Windows, macOS, Linux e Raspberry Pi (alto-falante ou buzzer).

Spec 027 (ALM-03 a ALM-05). Os sinais vêm do nível de risco (vision/risk.py, `RiskAssessment.alarm_kind`):
- `info`: duas notas suaves (calibração, "não vejo seus olhos", descanso previsto, autoteste). Não soa como alarme;
- `distracao`: dois pulsos médios (celular), nunca contínuo;
- `sonolencia`: rajada 3+2 (como a alta prioridade da IEC 60601-1-8), mais aguda; no 2º estágio, repetida;
- `critico`: pulsos curtos e rápidos alternando duas notas (microssono, sono, sem resposta), até o olho abrir.

Desenho do som (pesquisa de 19/10/2026, §1.3): fundamental entre 150 e 1.200 Hz e 5 parciais a no máximo 15 dB da
maior, para o som não sumir em pontos da cabine; urgência cresce com nota mais aguda e pulsos mais rápidos (Edworthy
et al., 1991; Suied et al., 2008); o Euro NCAP 2026 pede aviso de microssono e sono distinto e mais urgente que o de
distração (§1.4.2). As frequências são ponto de partida: precisam de teste de escuta e de medida na cabine (PI-02).

Os WAVs são síntese própria com numpy (nenhum arquivo de terceiros), determinística, gerados na pasta de dados na
primeira vez (`sirene_<tipo>.wav`). O crítico interrompe qualquer som; nenhum som menos urgente interrompe outro.
"""
from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("drivesafe.alarm")

SAMPLE_RATE = 22050
SOUND_KINDS = ("info", "distracao", "sonolencia", "critico")  # do menos ao mais urgente
PRIORIDADE = {tipo: posicao for posicao, tipo in enumerate(SOUND_KINDS)}

_DO5, _MI5, _SOL5, _LA5, _RE6 = 523.25, 659.26, 783.99, 880.0, 1174.66
# Pulsos de cada sinal: (frequência fundamental em Hz, duração do pulso em s, silêncio depois dele em s).
PADROES = {
    "info": ((_DO5, 0.20, 0.12), (_MI5, 0.24, 0.0)),
    "distracao": ((_MI5, 0.15, 0.12), (_MI5, 0.15, 0.0)),
    "sonolencia": ((_SOL5, 0.11, 0.05), (_SOL5, 0.11, 0.05), (_SOL5, 0.11, 0.22),
                   (_SOL5, 0.11, 0.05), (_SOL5, 0.11, 0.0)),
    "critico": tuple((nota, 0.07, 0.04) for _ in range(8) for nota in (_LA5, _RE6))[:-1] + ((_RE6, 0.07, 0.0),),
}
# Amplitude de cada parcial (fundamental e múltiplos): a menor fica a −12 dB (−14 dB no info) da maior.
HARMONICOS = {"info": (1.0, 0.5, 0.35, 0.25, 0.2)}
HARMONICOS_PADRAO = (1.0, 0.6, 0.45, 0.35, 0.25)
# Rampa de subida e descida de cada pulso (cosseno), sem clique.
RAMPA_S = {"info": 0.02}
RAMPA_PADRAO_S = 0.008
# Pico do WAV em fração da escala: o volume final depende da saída (no Pi, calibrar na cabine: PI-02).
PICO = {"info": 0.35, "distracao": 0.55, "sonolencia": 0.75, "critico": 0.90}
REPETICAO_PAUSA_S = 0.25

LINUX_PLAYERS = (
    ("aplay", ["aplay", "-q"]),
    ("paplay", ["paplay"]),
    ("pw-play", ["pw-play"]),
    ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
)


# ---------------------------------------------------------------------------------------------------------------
# Síntese
# ---------------------------------------------------------------------------------------------------------------
def duracao_s(tipo: str) -> float:
    return sum(pulso + silencio for _, pulso, silencio in PADROES[tipo])


def _pulso(np, frequencia: float, segundos: float, harmonicos, rampa_s: float):
    n = int(round(SAMPLE_RATE * segundos))
    t = np.arange(n) / SAMPLE_RATE
    sinal = np.zeros(n)
    for ordem, amplitude in enumerate(harmonicos, start=1):
        if frequencia * ordem < SAMPLE_RATE / 2:
            sinal += amplitude * np.sin(2 * np.pi * frequencia * ordem * t)
    sinal /= np.abs(sinal).max()
    m = int(round(SAMPLE_RATE * rampa_s))
    subida = 0.5 - 0.5 * np.cos(np.pi * np.arange(m) / m)
    envelope = np.ones(n)
    envelope[:m] = subida
    envelope[-m:] = subida[::-1]
    return sinal * envelope


def sintetizar(tipo: str):
    """PCM 16 bits mono (numpy int16) do sinal. Determinístico: mesma entrada, mesmos bytes."""
    import numpy as np  # só aqui: o resto do módulo funciona sem numpy (buzzer, testes leves)

    if tipo not in PADROES:
        raise ValueError(f"sinal desconhecido: {tipo!r}")
    harmonicos = HARMONICOS.get(tipo, HARMONICOS_PADRAO)
    rampa = RAMPA_S.get(tipo, RAMPA_PADRAO_S)
    partes = []
    for frequencia, pulso, silencio in PADROES[tipo]:
        partes.append(_pulso(np, frequencia, pulso, harmonicos, rampa))
        partes.append(np.zeros(int(round(SAMPLE_RATE * silencio))))
    sinal = np.concatenate(partes)
    sinal *= PICO[tipo] / np.abs(sinal).max()
    return np.round(sinal * 32767).astype("<i2")


def wav_bytes(tipo: str) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(sintetizar(tipo).tobytes())
    return buffer.getvalue()


def _gravar(caminho: Path, dados: bytes) -> None:
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_bytes(dados)
    os.replace(temporario, caminho)


def write_sound_wav(path: Path, tipo: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _gravar(path, wav_bytes(tipo))


def write_siren_wav(path: Path) -> None:
    """Compatibilidade com a versão de um som só: grava o sinal crítico."""
    write_sound_wav(path, "critico")


def caminhos_dos_sons(base: Path) -> dict:
    """sirene.wav → sirene_info.wav, sirene_distracao.wav, sirene_sonolencia.wav e sirene_critico.wav."""
    base = Path(base)
    return {tipo: base.with_name(f"{base.stem}_{tipo}.wav") for tipo in SOUND_KINDS}


def garantir_sons(base: Path) -> dict:
    """Gera os 4 WAVs na primeira vez. Arquivo igual não é regravado (poupa o cartão SD); diferente é refeito."""
    caminhos = caminhos_dos_sons(base)
    next(iter(caminhos.values())).parent.mkdir(parents=True, exist_ok=True)
    for tipo, caminho in caminhos.items():
        dados = wav_bytes(tipo)
        try:
            igual = caminho.read_bytes() == dados
        except OSError:
            igual = False
        if not igual:
            _gravar(caminho, dados)
    return caminhos


# ---------------------------------------------------------------------------------------------------------------
# Saídas de áudio. tocar() bloqueia a thread do alarme até o fim ou até `cancelar`; parar() silencia na hora.
# Depois de cancelada, uma reprodução nunca mexe mais na saída (quem cancelou já chamou parar()).
# ---------------------------------------------------------------------------------------------------------------
class SaidaTerminal:
    """Sem player: só o bipe do terminal. Conta como "sem saída de som" no autoteste."""

    nome = "terminal"
    sem_som = True
    reserva = None

    def tocar(self, tipo, cancelar) -> None:
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
        except (OSError, ValueError, AttributeError):
            pass

    def parar(self) -> None:
        pass


class SaidaSounddevice:
    """PortAudio pelo sounddevice (MIT; já vem com o MediaPipe), com um fluxo de saída aberto o tempo todo: trocar ou
    parar o som é só trocar o buffer que o callback lê, sem abrir nem fechar nada na hora do alarme.

    Medido neste notebook (Windows, MME, 19/10/2026): o callback pega o som novo em 5 a 11 ms e a placa leva mais
    ~90 ms (latency="low"). Com sd.play()/sd.stop() o stop() esperava o buffer esvaziar: ~210 ms travando quem chamou.
    Um fluxo por processo (a tela cria um Alarm a cada teste)."""

    nome = "sounddevice"
    sem_som = False

    def __init__(self, sd):
        self._sd = sd
        self._sons = {tipo: sintetizar(tipo) for tipo in SOUND_KINDS}
        self._trava = threading.Lock()  # buffer e posição (callback do PortAudio × thread do alarme)
        self._trava_fluxo = threading.Lock()  # abrir e reabrir o fluxo
        self._buffer = None
        self._posicao = 0
        self._fluxo = None
        self.reserva = None
        self._abrir()

    def _abrir(self) -> None:
        erro = None
        for canais in (1, 2):  # alguns dispositivos não abrem em mono
            try:
                fluxo = self._sd.OutputStream(samplerate=SAMPLE_RATE, channels=canais, dtype="int16",
                                              callback=self._preencher, latency="low")
                fluxo.start()
            except Exception as exc:
                erro = exc
                continue
            self._fluxo = fluxo
            return
        raise erro

    def _preencher(self, saida, quadros, _tempo, _estado) -> None:
        try:
            with self._trava:
                buffer, posicao = self._buffer, self._posicao
                if buffer is None:
                    saida.fill(0)
                    return
                n = min(quadros, len(buffer) - posicao)
                saida[:n] = buffer[posicao:posicao + n, None]
                saida[n:] = 0
                self._posicao = posicao + n
                if self._posicao >= len(buffer):
                    self._buffer = None
        except Exception:  # o callback nunca pode levantar: derrubaria o fluxo
            saida.fill(0)

    def tocar(self, tipo, cancelar) -> None:
        with self._trava_fluxo:
            if self._fluxo is None or not self._fluxo.active:
                if self._fluxo is not None:
                    try:
                        self._fluxo.close(ignore_errors=True)
                    except Exception:
                        pass
                    logger.warning("Fluxo de áudio parou (dispositivo trocado?): reabrindo.")
                self._fluxo = None
                self._abrir()
            latencia = float(getattr(self._fluxo, "latency", 0.0) or 0.0)
        with self._trava:
            if cancelar.is_set():
                return
            self._buffer, self._posicao = self._sons[tipo], 0
        cancelar.wait(len(self._sons[tipo]) / SAMPLE_RATE + latencia + 0.02)

    def parar(self) -> None:
        with self._trava:
            self._buffer = None


_SAIDA_SOUNDDEVICE = None
_SAIDA_SOUNDDEVICE_TRAVA = threading.Lock()


def _saida_sounddevice():
    """O fluxo do sounddevice, aberto uma vez por processo; None se não houver PortAudio ou dispositivo de saída."""
    global _SAIDA_SOUNDDEVICE
    with _SAIDA_SOUNDDEVICE_TRAVA:
        if _SAIDA_SOUNDDEVICE is None:
            sd = _carregar_sounddevice()
            if sd is None:
                return None
            try:
                _SAIDA_SOUNDDEVICE = SaidaSounddevice(sd)
            except Exception as exc:
                logger.info("sounddevice sem fluxo de saída (%s): usando o player do sistema.", exc)
                return None
        return _SAIDA_SOUNDDEVICE


class SaidaWinsound:
    """Windows sem sounddevice: PlaySound assíncrono; PlaySound(None) corta o som."""

    nome = "winsound"
    sem_som = False

    def __init__(self, caminhos: dict):
        self._caminhos = dict(caminhos)
        self._trava = threading.Lock()
        self.reserva = None

    def tocar(self, tipo, cancelar) -> None:
        import winsound

        with self._trava:
            if cancelar.is_set():
                return
            winsound.PlaySound(str(self._caminhos[tipo]),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        cancelar.wait(duracao_s(tipo) + 0.05)

    def parar(self) -> None:
        import winsound

        with self._trava:
            winsound.PlaySound(None, 0)


class SaidaProcesso:
    """Player do sistema (aplay, paplay, pw-play, ffplay, afplay) em subprocesso: terminate() corta o som."""

    sem_som = False

    def __init__(self, nome: str, comando: list, caminhos: dict):
        self.nome = nome
        self._comando = list(comando)
        self._caminhos = dict(caminhos)
        self._trava = threading.Lock()
        self._processo = None
        self.reserva = None

    def tocar(self, tipo, cancelar) -> None:
        with self._trava:
            if cancelar.is_set():
                return
            processo = self._processo = subprocess.Popen(
                self._comando + [str(self._caminhos[tipo])],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        limite = time.monotonic() + duracao_s(tipo) + 5.0
        while processo.poll() is None:
            if cancelar.wait(0.02):
                self._encerrar(processo)
                return
            if time.monotonic() > limite:
                self._encerrar(processo)
                raise TimeoutError(f"{self.nome} não terminou de tocar")
        erro = processo.communicate()[1]
        if processo.returncode != 0:
            detalhe = erro.decode("utf-8", "replace").strip() if erro else ""
            raise OSError(f"{self.nome} saiu com código {processo.returncode}: {detalhe}")

    def parar(self) -> None:
        with self._trava:
            processo = self._processo
            if processo is not None and processo.poll() is None:
                try:
                    processo.terminate()
                except OSError:
                    pass

    @staticmethod
    def _encerrar(processo) -> None:
        try:
            processo.terminate()
            processo.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.communicate()
        except OSError:
            pass


class SaidaBuzzer:
    """Buzzer ativo no GPIO do Pi (gpiozero.Buzzer): só liga e desliga, então os sinais diferem pelo ritmo (PI-03)."""

    nome = "buzzer_gpio"
    sem_som = False
    reserva = None

    def __init__(self, buzzer):
        self._buzzer = buzzer
        self._trava = threading.Lock()

    def tocar(self, tipo, cancelar) -> None:
        for _, ligado, desligado in PADROES[tipo]:
            if not self._mexer(cancelar, self._buzzer.on) or cancelar.wait(ligado):
                return
            if not self._mexer(cancelar, self._buzzer.off) or (desligado and cancelar.wait(desligado)):
                return

    def _mexer(self, cancelar, acao) -> bool:
        with self._trava:
            if cancelar.is_set():
                return False
            acao()
            return True

    def parar(self) -> None:
        with self._trava:
            self._buzzer.off()


def _carregar_sounddevice():
    try:
        import sounddevice as sd

        sd.query_devices(kind="output")  # sem dispositivo de saída padrão, levanta erro
        return sd
    except Exception as exc:  # ImportError, OSError (PortAudio ausente) ou PortAudioError (sem saída)
        logger.info("sounddevice indisponível (%s): usando o player do sistema.", exc)
        return None


def descobrir_saida(caminhos: dict, plataforma: str | None = None, which=shutil.which, usar_sounddevice: bool = True):
    """Primeira saída que existe, com as seguintes como reserva (se uma falhar ao tocar, o alarme passa para a
    próxima). Ordem: sounddevice → winsound (Windows), afplay (macOS) ou aplay/paplay/pw-play/ffplay (Linux) →
    bipe do terminal."""
    plataforma = plataforma or sys.platform
    cadeia = []
    if usar_sounddevice:
        fluxo = _saida_sounddevice()
        if fluxo is not None:
            cadeia.append(fluxo)
    if caminhos:
        if plataforma == "win32":
            cadeia.append(SaidaWinsound(caminhos))
        elif plataforma == "darwin":
            cadeia.append(SaidaProcesso("afplay", ["afplay"], caminhos))
        else:
            for nome, comando in LINUX_PLAYERS:
                if which(nome):
                    cadeia.append(SaidaProcesso(nome, comando, caminhos))
                    break
    if not cadeia:
        logger.warning("Nenhum player de áudio encontrado (sounddevice, aplay, paplay, pw-play, ffplay). No Raspberry "
                       "Pi OS instale com: sudo apt install alsa-utils. Usando só o bipe do terminal.")
    cadeia.append(SaidaTerminal())
    for atual, seguinte in zip(cadeia, cadeia[1:]):
        atual.reserva = seguinte
    if not cadeia[0].sem_som:
        logger.info("Alarme pelo alto-falante (%s%s).", cadeia[0].nome,
                    f"; reserva: {cadeia[1].nome}" if len(cadeia) > 2 else "")
    return cadeia[0]


# ---------------------------------------------------------------------------------------------------------------
# Alarme
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class _Reproducao:
    tipo: str
    repeticoes: int
    cancelar: threading.Event = field(default_factory=threading.Event)
    fim: threading.Event = field(default_factory=threading.Event)
    erro: BaseException | None = None
    saida: str | None = None

    def ativa(self) -> bool:
        return not self.cancelar.is_set() and not self.fim.is_set()


class Alarm:
    """Toca os sinais em segundo plano sem travar a leitura da câmera.

    sound_path: caminho base na pasta de dados (ex.: <dados>/sirene.wav); os WAVs ficam ao lado
    (sirene_<tipo>.wav). saida: injeta uma saída (testes); None descobre a do sistema.
    `muted` pode mudar com o alarme rodando (tecla S da tela): os sons ficam sempre preparados."""

    def __init__(self, sound_path: Path, buzzer_pin: int | None = None, muted: bool = False, saida=None):
        self._sound_path = Path(sound_path)
        self._lock = threading.Lock()
        self._atual: _Reproducao | None = None
        self._muted = bool(muted)
        self.sound_paths: dict = {}

        if saida is None and buzzer_pin is not None:
            saida = self._buzzer(buzzer_pin)
        if saida is None or not isinstance(saida, SaidaBuzzer):
            try:
                self.sound_paths = garantir_sons(self._sound_path)
            except OSError as exc:
                logger.warning("Não deu para gravar os sons em %s (%s): só a saída pela memória funciona.",
                               self._sound_path.parent, exc)
        self._saida = saida if saida is not None else descobrir_saida(self.sound_paths)
        if self._muted:
            logger.info("Alarme sonoro desligado (--mute ou tela): os sons ficam preparados.")

    def _buzzer(self, pin: int):
        try:
            from gpiozero import Buzzer  # vem instalado no Raspberry Pi OS
        except ImportError as exc:
            if self._muted:
                logger.warning("Buzzer no GPIO %s pedido, mas o gpiozero não está disponível (alarme mudo).", pin)
                return None
            raise RuntimeError(
                "Buzzer pedido, mas gpiozero não está disponível. No Raspberry Pi OS crie o venv com "
                "--system-site-packages ou rode: pip install gpiozero lgpio"
            ) from exc
        logger.info("Alarme pelo buzzer no GPIO %s.", pin)
        return SaidaBuzzer(Buzzer(pin))

    @property
    def saida_nome(self) -> str:
        return self._saida.nome

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, valor: bool) -> None:
        self._muted = bool(valor)
        if self._muted:
            self.stop()

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._atual is not None and self._atual.ativa()

    @property
    def tocando(self) -> str | None:
        """Tipo do sinal tocando agora, ou None."""
        with self._lock:
            atual = self._atual
            return atual.tipo if atual is not None and atual.ativa() else None

    def trigger(self, kind: str | None = None, repeticoes: int = 1) -> None:
        """Pede um sinal. Sem tipo = o mais urgente (crítico), como a sirene única de antes. Pedido do mesmo tipo ou
        menos urgente que o que está tocando é ignorado; mais urgente interrompe na hora."""
        self._iniciar(kind or "critico", repeticoes)

    def update(self, risk) -> None:
        """Uma chamada por quadro com o `RiskAssessment`: para o crítico quando o olho abre e toca o que o risco pediu.
        Risco sem `alarm_kind` mas com `alarm` (versão antiga) toca o crítico."""
        if getattr(risk, "parar_alarme", False):
            self.stop("critico")
        tipo = getattr(risk, "alarm_kind", None)
        if tipo is None and getattr(risk, "alarm", False):
            tipo = "critico"
        if tipo is not None:
            self.trigger(tipo, getattr(risk, "alarm_repeticoes", 1) or 1)

    def stop(self, kind: str | None = None) -> None:
        """Silencia na hora. Com tipo, só se for esse o sinal tocando."""
        with self._lock:
            atual = self._atual
            if atual is None or not atual.ativa() or (kind is not None and atual.tipo != kind):
                return
            atual.cancelar.set()
            self._atual = None
            self._parar_saida()

    def autoteste(self, store=None, espera_s: float = 5.0) -> dict:
        """RF-04 (ALM-05): toca `info` uma vez ao ligar. Sem saída de som (só o bipe do terminal, ou o player
        falhou), avisa no log e grava `estado_aparelho` com `som: sem_saida_de_som` na fila, se houver."""
        if self._muted:
            logger.info("Autoteste do som não tocou: alarme mudo.")
            return {"som": "mudo", "saida": self.saida_nome}
        sem_som = getattr(self._saida, "sem_som", False)
        reproducao = None if sem_som else self._iniciar("info", 1)
        if reproducao is not None:
            reproducao.fim.wait(espera_s)
        saida = reproducao.saida if reproducao is not None and reproducao.saida else self.saida_nome
        funcionou = reproducao is not None and reproducao.erro is None and not getattr(self._saida, "sem_som", False)
        if funcionou:
            logger.info("Autoteste do som: sinal info tocado (%s).", saida)
            return {"som": "ok", "saida": saida}
        erro = reproducao.erro if reproducao is not None else None
        logger.warning("Autoteste do som: nenhuma saída de áudio funcionou%s. O alarme não vai ser ouvido.",
                       f" ({erro})" if erro else "")
        if store is not None:
            detalhes = {"som": "sem_saida_de_som", "saida": saida}
            if erro is not None:
                detalhes["erro"] = str(erro)[:200]
            store.add("estado_aparelho", 1, 0.0, detalhes)
        return {"som": "sem_saida_de_som", "saida": saida}

    def _iniciar(self, tipo: str, repeticoes: int) -> _Reproducao | None:
        if tipo not in PRIORIDADE:
            raise ValueError(f"sinal desconhecido: {tipo!r} (use {', '.join(SOUND_KINDS)})")
        with self._lock:
            if self._muted:
                return None
            atual = self._atual
            if atual is not None and atual.ativa():
                if PRIORIDADE[atual.tipo] >= PRIORIDADE[tipo]:
                    return None
                atual.cancelar.set()
                self._parar_saida()
            reproducao = self._atual = _Reproducao(tipo, max(1, int(repeticoes)))
        threading.Thread(target=self._tocar, args=(reproducao,), name="drivesafe-alarm", daemon=True).start()
        return reproducao

    def _parar_saida(self) -> None:
        try:
            self._saida.parar()
        except Exception as exc:  # parar nunca derruba quem chamou (o loop da câmera)
            logger.debug("Falha ao parar o som (%s): %s", self._saida.nome, exc)

    def _tocar(self, reproducao: _Reproducao) -> None:
        try:
            for vez in range(reproducao.repeticoes):
                if reproducao.cancelar.is_set() or (vez and reproducao.cancelar.wait(REPETICAO_PAUSA_S)):
                    break
                self._tocar_uma_vez(reproducao)
        finally:
            reproducao.fim.set()
            with self._lock:
                if self._atual is reproducao:
                    self._atual = None

    def _tocar_uma_vez(self, reproducao: _Reproducao) -> None:
        while True:
            saida = self._saida
            reproducao.saida = saida.nome
            try:
                saida.tocar(reproducao.tipo, reproducao.cancelar)
                reproducao.erro = None
                return
            except Exception as exc:
                reproducao.erro = exc
                reserva = getattr(saida, "reserva", None)
                if reserva is None or reproducao.cancelar.is_set():
                    logger.warning("Falha ao tocar o alarme (%s): %s", saida.nome, exc)
                    return
                logger.warning("Falha ao tocar o alarme (%s): %s. Passando para %s.", saida.nome, exc, reserva.nome)
                if self._saida is saida:
                    self._saida = reserva
                if getattr(reserva, "sem_som", False):
                    reserva.tocar(reproducao.tipo, reproducao.cancelar)
                    return
