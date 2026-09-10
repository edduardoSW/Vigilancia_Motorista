"""Valida o detector de piscadas contra uma anotação manual.

Uso:
  python avaliar_piscadas.py resultados/video_piscadas.csv anotacao.csv
  python avaliar_piscadas.py resultados/video_piscadas.csv anotacao.csv --tolerancia 0.25 --inicio 60 --fim 300

- Detecção: o `_piscadas.csv` gerado pelo analisar_video.py.
- Anotação: CSV (vírgula ou ponto e vírgula) com uma linha por piscada e a coluna `inicio_s` (e `fim_s`, se houver).
  Também aceita `tempo_s` (um instante por piscada) ou `quadro`, `quadro_inicio` e `quadro_fim` com --fps.
- Casamento um para um pelo centro de cada piscada, do par mais próximo ao mais distante, dentro da tolerância.

Mostra verdadeiros e falsos positivos, falsos negativos, precisão, recall, F1, erro de contagem e desvio de tempo,
e grava `<anotacao>_comparacao.json` e `<anotacao>_pares.csv`.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

from vision.evaluation import events_from_rows, match_events, precision_recall_f1, read_csv_rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compara piscadas detectadas com anotação manual.")
    parser.add_argument("detectadas", help="_piscadas.csv do analisar_video.py")
    parser.add_argument("anotacao", help="CSV com as piscadas anotadas à mão")
    parser.add_argument("--tolerancia", type=float, default=0.25, help="segundos entre os centros (padrão 0,25)")
    parser.add_argument("--fps", type=float, default=None, help="necessário se a anotação vier em quadros")
    parser.add_argument("--inicio", type=float, default=None, help="só compara a partir deste segundo")
    parser.add_argument("--fim", type=float, default=None, help="só compara até este segundo")
    parser.add_argument("--so-completas", action="store_true",
                        help="ignora piscadas detectadas incompletas (olho fechou menos de 60%%)")
    args = parser.parse_args(argv)

    detected_rows = read_csv_rows(args.detectadas)
    if args.so_completas:
        detected_rows = [row for row in detected_rows if row.get("completa") == "1"]
    detected = events_from_rows(detected_rows)
    annotated = events_from_rows(read_csv_rows(args.anotacao), fps=args.fps)
    if not annotated:
        print("A anotação não tem piscadas legíveis (colunas inicio_s, tempo_s ou quadro com --fps).")
        return 1

    def inside(event):
        center = (event[0] + event[1]) / 2.0
        return (args.inicio is None or center >= args.inicio) and (args.fim is None or center <= args.fim)

    detected = [event for event in detected if inside(event)]
    annotated = [event for event in annotated if inside(event)]
    pairs, false_positives, false_negatives = match_events(detected, annotated, args.tolerancia)
    precision, recall, f1 = precision_recall_f1(len(pairs), len(false_positives), len(false_negatives))
    offsets = [offset for _, _, offset in pairs]

    result = {
        "tolerancia_s": args.tolerancia,
        "anotadas": len(annotated),
        "detectadas": len(detected),
        "verdadeiros_positivos": len(pairs),
        "falsos_positivos": len(false_positives),
        "falsos_negativos": len(false_negatives),
        "precisao": None if precision is None else round(precision, 3),
        "recall": None if recall is None else round(recall, 3),
        "f1": None if f1 is None else round(f1, 3),
        "erro_de_contagem": len(detected) - len(annotated),
        "desvio_medio_s": round(statistics.fmean(offsets), 3) if offsets else None,
        "desvio_absoluto_mediano_s": round(statistics.median(abs(o) for o in offsets), 3) if offsets else None,
    }
    base = Path(args.anotacao).with_suffix("")
    Path(f"{base}_comparacao.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(f"{base}_pares.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tipo", "detectada_inicio_s", "detectada_fim_s", "anotada_inicio_s", "anotada_fim_s", "diferenca_s"])
        for i, j, offset in pairs:
            writer.writerow(["par", *detected[i], *annotated[j], f"{offset:.3f}"])
        for i in false_positives:
            writer.writerow(["falso_positivo", *detected[i], "", "", ""])
        for j in false_negatives:
            writer.writerow(["falso_negativo", "", "", *annotated[j], ""])

    print(f"Anotadas {result['anotadas']}, detectadas {result['detectadas']}: "
          f"{result['verdadeiros_positivos']} certas, {result['falsos_positivos']} a mais, {result['falsos_negativos']} perdidas.")
    print(f"Precisão {result['precisao']}, recall {result['recall']}, F1 {result['f1']}. "
          f"Desvio mediano de tempo {result['desvio_absoluto_mediano_s']} s.")
    print(f"Detalhes em {base}_comparacao.json e {base}_pares.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
