"""Gera o ícone do RotaGuard Teste (escudo com "A" do logotipo do site) em PNG e ICO.

Uso: python implantacao/app-teste/gerar_icone.py
Saídas ao lado deste arquivo: rotaguard.png (512 px) e rotaguard.ico (16, 24, 32, 48, 64, 128 e 256 px).
Só usa numpy e OpenCV, que já são dependências da caixa.
"""
from __future__ import annotations

import struct
from pathlib import Path

import cv2
import numpy as np

PASTA = Path(__file__).resolve().parent
VERDE = (49, 62, 16)  # #103e31 em BGR
LIMA = (105, 246, 213)  # #d5f669 em BGR
TAMANHOS_ICO = (16, 24, 32, 48, 64, 128, 256)


def desenhar(lado: int) -> np.ndarray:
    """Desenha em 4× e reduz, para bordas suaves."""
    escala = 4
    s = lado * escala
    img = np.zeros((s, s, 4), dtype=np.uint8)

    def pt(x, y):  # coordenadas no viewBox 34 × 37 do logotipo, centralizado no quadrado
        k = s / 40.0
        return int(round((x + 3) * k)), int(round((y + 1.5) * k))

    raio = int(s * 0.22)
    cv2.rectangle(img, (raio, 0), (s - raio, s), (*VERDE, 255), -1)
    cv2.rectangle(img, (0, raio), (s, s - raio), (*VERDE, 255), -1)
    for cx, cy in ((raio, raio), (s - raio, raio), (raio, s - raio), (s - raio, s - raio)):
        cv2.circle(img, (cx, cy), raio, (*VERDE, 255), -1, lineType=cv2.LINE_AA)

    escudo = [pt(17, 2), pt(31, 8), pt(31, 20)]
    for t in np.linspace(0, 1, 12):  # curva de baixo do escudo
        escudo.append(pt(31 - 14 * t, 20 + 15 * np.sin(t * np.pi / 2)))
    for t in np.linspace(0, 1, 12):
        escudo.append(pt(17 - 14 * t, 35 - 15 * (1 - np.cos(t * np.pi / 2))))
    escudo += [pt(3, 8)]
    espessura = max(2, int(s * 0.055))
    cv2.polylines(img, [np.array(escudo, dtype=np.int32)], True, (*LIMA, 255), espessura, lineType=cv2.LINE_AA)

    traco = max(2, int(s * 0.065))
    cv2.polylines(img, [np.array([pt(10, 25), pt(15, 11), pt(20, 11), pt(24, 25)], dtype=np.int32)], False,
                  (*LIMA, 255), traco, lineType=cv2.LINE_AA)
    cv2.line(img, pt(12, 20), pt(22, 20), (*LIMA, 255), traco, lineType=cv2.LINE_AA)
    return cv2.resize(img, (lado, lado), interpolation=cv2.INTER_AREA)


def png_bytes(img: np.ndarray) -> bytes:
    ok, dados = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("falha ao gerar PNG")
    return dados.tobytes()


def escrever_ico(caminho: Path, tamanhos=TAMANHOS_ICO) -> None:
    imagens = [png_bytes(desenhar(t)) for t in tamanhos]
    cabecalho = struct.pack("<HHH", 0, 1, len(imagens))
    deslocamento = 6 + 16 * len(imagens)
    entradas, corpo = b"", b""
    for t, dados in zip(tamanhos, imagens):
        lado = 0 if t >= 256 else t
        entradas += struct.pack("<BBBBHHII", lado, lado, 0, 0, 1, 32, len(dados), deslocamento + len(corpo))
        corpo += dados
    caminho.write_bytes(cabecalho + entradas + corpo)


if __name__ == "__main__":
    (PASTA / "rotaguard.png").write_bytes(png_bytes(desenhar(512)))
    escrever_ico(PASTA / "rotaguard.ico")
    print("ícones gerados em", PASTA)
