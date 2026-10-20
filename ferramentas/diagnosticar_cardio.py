"""Diagnóstico do pulso pela câmera (vision/cardio.py, spec 022) num vídeo gravado.

Roda o Face Landmarker do MediaPipe e o CardioMonitor quadro a quadro e imprime, uma linha por segundo: estado,
motivo, bpm (ou o último bom entre parênteses), SNR, taxa de quadros medida, luminância média das ROIs, fração de
pixels estourados, progresso e segundos que faltam. No fim, o resumo: fração do tempo com número, tempo até o primeiro
número, quantas vezes o número sumiu e, com --bpm-real, o erro.

Exemplos:
  python ferramentas/diagnosticar_cardio.py video.avi
  python ferramentas/diagnosticar_cardio.py video.avi --bpm-real 72 --pontos pontos.npz
  python ferramentas/diagnosticar_cardio.py video.avi --pular 2      (1 a cada 2 quadros: simula câmera lenta)

--pontos guarda os 478 pontos de cada quadro num .npz na primeira vez e reaproveita depois (o MediaPipe é a parte cara).
Nada daqui vai para evento, fila ou servidor: é dado de saúde (LGPD art. 11) e fica só na tela de quem rodou.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))  # vision/ fica em caixa/

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2  # noqa: E402
import numpy as np  # noqa: E402


def quadros_do_video(caminho: str, pular: int = 1):
    """(índice, tempo em s, quadro BGR). O tempo vem do índice e da taxa do arquivo (estável e reproduzível)."""
    captura = cv2.VideoCapture(str(caminho))
    if not captura.isOpened():
        raise SystemExit(f"Não abriu o vídeo {caminho}")
    fps = captura.get(cv2.CAP_PROP_FPS) or 30.0
    indice = 0
    try:
        while True:
            lido, quadro = captura.read()
            if not lido:
                break
            if indice % max(1, pular) == 0:
                yield indice, indice / fps, quadro
            indice += 1
    finally:
        captura.release()


def pontos_do_video(caminho: str, cache: str | None, pular: int = 1) -> dict[int, np.ndarray | None]:
    """Pontos (478 × 2, em pixels) por índice de quadro, pelo vision/face.py; com cache em .npz se pedido."""
    if cache and Path(cache).is_file():
        dados = np.load(cache)
        indices, pontos, achou = dados["indices"], dados["pontos"], dados["achou"]
        return {int(i): (p if a else None) for i, p, a in zip(indices, pontos, achou)}
    from vision.face import FaceAnalyzer

    analisador = FaceAnalyzer(classifier=None)
    saida: dict[int, np.ndarray | None] = {}
    try:
        for indice, t, quadro in quadros_do_video(caminho, 1):
            medidas = analisador.analyze(quadro, t)
            saida[indice] = medidas.landmarks if medidas.face_found else None
    finally:
        analisador.close()
    if cache:
        indices = np.array(sorted(saida))
        vazio = np.zeros((478, 2), np.float32)
        np.savez_compressed(cache, indices=indices,
                            pontos=np.stack([saida[i] if saida[i] is not None else vazio for i in indices]),
                            achou=np.array([saida[i] is not None for i in indices]))
    return saida


def _f(valor, casas: int = 1, largura: int = 6) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "-".rjust(largura)
    return f"{valor:.{casas}f}".rjust(largura)


def diagnosticar(caminho: str, monitor=None, pontos: dict | None = None, pular: int = 1, bpm_real: float | None = None,
                 imprimir: bool = True, infrared: bool = False) -> dict:
    """Roda o monitor no vídeo e devolve o resumo; com imprimir=True mostra uma linha por segundo."""
    if monitor is None:
        from vision.cardio import CardioMonitor

        monitor = CardioMonitor()
    pontos = pontos if pontos is not None else pontos_do_video(caminho, None, pular)
    if imprimir:
        print("    t  estado        motivo           bpm   SNR dB    fps    luz  estour  progr  faltam")
    leituras, segundo = [], -1
    for indice, t, quadro in quadros_do_video(caminho, pular):
        leitura = monitor.update(quadro, pontos.get(indice), t, infrared=infrared)
        leituras.append((t, leitura))
        if imprimir and int(t) != segundo:
            segundo = int(t)
            bpm = _f(leitura.bpm, 1) if leitura.bpm is not None else (
                f"({leitura.ultimo_bpm:.1f})".rjust(6) if leitura.ultimo_bpm is not None else "-".rjust(6))
            saturado = getattr(leitura, "fracao_saturada", None)
            print(f"{t:5.0f}  {leitura.estado:<12}  {str(getattr(leitura, 'motivo', None) or '-'):<14} {bpm}  "
                  f"{_f(leitura.snr_db)}  {_f(getattr(leitura, 'fps', None))}  "
                  f"{_f(getattr(leitura, 'luminancia', None), 0, 5)}  "
                  f"{_f(None if saturado is None else 100.0 * saturado, 0, 5)}%  {_f(leitura.progresso, 2, 5)}  "
                  f"{_f(getattr(leitura, 'segundos_para_medida', None), 0, 6)}")
    return resumir(leituras, bpm_real)


def resumir(leituras, bpm_real: float | None = None) -> dict:
    """Fração do tempo com número (geral e depois dos primeiros 15 s), primeiro número, quedas e erro."""
    if not leituras:
        return {}
    tempos = np.array([t for t, _ in leituras])
    com_numero = np.array([leitura.estado == "pronto" and leitura.bpm is not None for _, leitura in leituras])
    dt = np.diff(np.append(tempos, tempos[-1] + (np.median(np.diff(tempos)) if len(tempos) > 1 else 0.0)))
    total = float(dt.sum())
    depois = tempos >= tempos[0] + 15.0
    primeiro = float(tempos[com_numero][0] - tempos[0]) if com_numero.any() else None
    quedas = int(np.sum(com_numero[:-1] & ~com_numero[1:]))
    maior_buraco, inicio = 0.0, None
    if primeiro is not None:
        for t, tem in zip(tempos[tempos >= tempos[0] + primeiro], com_numero[tempos >= tempos[0] + primeiro]):
            if not tem and inicio is None:
                inicio = t
            elif tem and inicio is not None:
                maior_buraco, inicio = max(maior_buraco, t - inicio), None
        if inicio is not None:
            maior_buraco = max(maior_buraco, float(tempos[-1] - inicio))
    resumo = {
        "duracao_s": round(total, 1),
        "fracao_com_numero": round(float(dt[com_numero].sum() / total), 3) if total else 0.0,
        "fracao_com_numero_depois_15s": round(float(dt[com_numero & depois].sum() / dt[depois].sum()), 3)
        if dt[depois].sum() else 0.0,
        "primeiro_numero_s": None if primeiro is None else round(primeiro, 1),
        "quedas": quedas,
        "maior_buraco_s": round(maior_buraco, 1),
        "estados": {e: round(float(dt[[leitura.estado == e for _, leitura in leituras]].sum() / total), 3)
                    for e in sorted({leitura.estado for _, leitura in leituras})},
    }
    motivos = [getattr(leitura, "motivo", None) for _, leitura in leituras]
    if any(m is not None for m in motivos):
        resumo["motivos"] = {m: round(float(dt[[x == m for x in motivos]].sum() / total), 3)
                             for m in sorted({m for m in motivos if m is not None})}
    if bpm_real is not None and com_numero.any():
        erros = np.abs(np.array([leitura.bpm for _, leitura in leituras if leitura.estado == "pronto"
                                 and leitura.bpm is not None]) - bpm_real)
        resumo.update(erro_medio_bpm=round(float(erros.mean()), 2), erro_p95_bpm=round(float(np.percentile(erros, 95)), 2),
                      erro_max_bpm=round(float(erros.max()), 2),
                      fracao_erro_ate_3bpm=round(float(np.mean(erros <= 3.0)), 3))
    return resumo


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("video")
    parser.add_argument("--pontos", help="cache .npz dos pontos do MediaPipe (cria se não existir)")
    parser.add_argument("--bpm-real", type=float, help="bpm de referência (oxímetro ou pulso sintético) para o erro")
    parser.add_argument("--pular", type=int, default=1, help="usa 1 a cada N quadros (simula câmera lenta)")
    parser.add_argument("--ir", action="store_true", help="marca os quadros como infravermelho (um canal só)")
    args = parser.parse_args(argv)
    pontos = pontos_do_video(args.video, args.pontos, args.pular)
    resumo = diagnosticar(args.video, pontos=pontos, pular=args.pular, bpm_real=args.bpm_real, infrared=args.ir)
    print("\nResumo")
    for chave, valor in resumo.items():
        print(f"  {chave}: {valor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
