"""Valida os gestos de sono (olhos esfregados e mão no rosto) contra uma anotação manual.

Uso:
  python analisar_video.py gravacao.mp4 --celular --saida resultados/
  python avaliar_gestos.py resultados/gravacao_gestos.csv anotacao_gestos.csv
  python avaliar_gestos.py resultados/gravacao_gestos.csv anotacao_gestos.csv --tolerancia 1.5 --inicio 60

- Detecção: o `_gestos.csv` do analisar_video.py rodado com --celular (as mãos vêm do detector de celular).
- Anotação: CSV (vírgula ou ponto e vírgula, ponto decimal), uma linha por gesto, com `inicio_s`, `fim_s` e `gesto`:
  - `olhos_esfregados` ou `mao_no_rosto`: o que o sistema deve contar;
  - qualquer outro nome (`ajustar_oculos`, `cocar_nariz`, `comer`, `beber`, `suor`, `celular_no_ouvido`...) é um
    negativo, algo que o sistema não deve contar. Serve para ver qual gesto parecido vira falso positivo.
- Casamento um para um pelo centro do gesto, do par mais próximo ao mais distante, dentro da tolerância (padrão 1 s:
  os episódios duram segundos e gestos a menos de 1,5 s se juntam num só).

Mostra, por gesto e para "qualquer gesto": acertos, falsos positivos, perdidos, precisão, sensibilidade (recall) e
F1; a troca entre os dois gestos; e os falsos positivos em cima de cada negativo. Grava `<anotacao>_comparacao.json`
e `<anotacao>_pares.csv`.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from vision.evaluation import match_events, precision_recall_f1, read_csv_rows, to_float

GESTURES = ("olhos_esfregados", "mao_no_rosto")


def read_gestures(path) -> list[tuple[float, float, str]]:
    """(início, fim, gesto), em ordem. Linhas sem início ou sem gesto ficam de fora."""
    gestures = []
    for row in read_csv_rows(path):
        start, end, label = to_float(row.get("inicio_s")), to_float(row.get("fim_s")), row.get("gesto", "").lower()
        if start is not None and label:
            gestures.append((start, end if end is not None else start, label))
    return sorted(gestures)


def _rounded(value):
    return None if value is None else round(value, 3)


def _scores(tp: int, fp: int, fn: int) -> dict:
    precision, recall, f1 = precision_recall_f1(tp, fp, fn)
    return {"acertos": tp, "falsos_positivos": fp, "perdidos": fn, "precisao": _rounded(precision),
            "recall": _rounded(recall), "f1": _rounded(f1)}


def compare(detected, annotated, tolerance: float) -> tuple[dict, list]:
    positives = [gesture for gesture in annotated if gesture[2] in GESTURES]
    negatives = [gesture for gesture in annotated if gesture[2] not in GESTURES]
    result = {"tolerancia_s": tolerance, "anotados": len(positives), "detectados": len(detected)}
    for name in GESTURES:
        mine = [gesture[:2] for gesture in detected if gesture[2] == name]
        truth = [gesture[:2] for gesture in positives if gesture[2] == name]
        pairs, extra, missed = match_events(mine, truth, tolerance)
        result[name] = _scores(len(pairs), len(extra), len(missed))

    # Sem olhar o nome: o gesto foi achado, mesmo que classificado como o outro?
    pairs, extra, missed = match_events([g[:2] for g in detected], [g[:2] for g in positives], tolerance)
    result["qualquer_gesto"] = _scores(len(pairs), len(extra), len(missed))
    confusion = Counter((positives[j][2], detected[i][2]) for i, j, _ in pairs)
    result["anotado_x_detectado"] = {truth: {mine: confusion[(truth, mine)] for mine in GESTURES} for truth in GESTURES}
    by_negative = Counter()
    for i in extra:
        start, end, _ = detected[i]
        hits = [negative[2] for negative in negatives if start <= negative[1] + tolerance and end >= negative[0] - tolerance]
        by_negative[hits[0] if hits else "sem_anotacao"] += 1
    result["falsos_positivos_por_negativo"] = dict(by_negative)
    result["negativos_anotados"] = dict(Counter(negative[2] for negative in negatives))

    rows = [["par", *detected[i], *positives[j], f"{offset:.3f}"] for i, j, offset in pairs]
    rows += [["falso_positivo", *detected[i], "", "", "", ""] for i in extra]
    rows += [["perdido", "", "", "", *positives[j], ""] for j in missed]
    return result, rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compara gestos de sono detectados com anotação manual.")
    parser.add_argument("detectados", help="_gestos.csv do analisar_video.py (com --celular)")
    parser.add_argument("anotacao", help="CSV com os gestos anotados à mão")
    parser.add_argument("--tolerancia", type=float, default=1.0, help="segundos entre os centros (padrão 1)")
    parser.add_argument("--inicio", type=float, default=None, help="só compara a partir deste segundo")
    parser.add_argument("--fim", type=float, default=None, help="só compara até este segundo")
    args = parser.parse_args(argv)

    def inside(gesture):
        center = (gesture[0] + gesture[1]) / 2.0
        return (args.inicio is None or center >= args.inicio) and (args.fim is None or center <= args.fim)

    detected = [gesture for gesture in read_gestures(args.detectados) if inside(gesture)]
    annotated = [gesture for gesture in read_gestures(args.anotacao) if inside(gesture)]
    if not annotated:
        print("A anotação não tem gestos legíveis (colunas inicio_s, fim_s e gesto).")
        return 1

    result, rows = compare(detected, annotated, args.tolerancia)
    base = Path(args.anotacao).with_suffix("")
    Path(f"{base}_comparacao.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(f"{base}_pares.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tipo", "detectado_inicio_s", "detectado_fim_s", "detectado_gesto",
                         "anotado_inicio_s", "anotado_fim_s", "anotado_gesto", "diferenca_s"])
        writer.writerows(rows)

    for name in (*GESTURES, "qualquer_gesto"):
        scores = result[name]
        print(f"{name}: {scores['acertos']} certos, {scores['falsos_positivos']} a mais, {scores['perdidos']} perdidos "
              f"(precisão {scores['precisao']}, recall {scores['recall']}, F1 {scores['f1']}).")
    if result["falsos_positivos_por_negativo"]:
        print("Falsos positivos por negativo anotado:", result["falsos_positivos_por_negativo"])
    print(f"Detalhes em {base}_comparacao.json e {base}_pares.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
