"""Calibra a detecção de celular com gravações de aparelhos reais (etapa 2 do PENDENCIAS.md).

Roteiro:
  1. Grave cada aparelho em cada situação (na mão na frente do peito, na altura do queixo, digitando, no ouvido, no
     colo, no suporte), variando a distância da câmera e a luz, e grave também os negativos (mão vazia na orelha,
     fone de ouvido, carteira, controle, maço de cigarro, copo, crachá, óculos na mão).
  2. Rode cada gravação:  python analisar_video.py gravacao.mp4 --celular --saida resultados/
  3. Anote os trechos à mão e rode:  python avaliar_celular.py anotacao_celular.csv --resultados resultados/

Anotação: CSV (vírgula ou ponto e vírgula, ponto decimal), uma linha por trecho:
  arquivo   nome do vídeo (a pasta é ignorada; procura resultados/<nome>_quadros.csv)
  aparelho  ex.: iphone13mini_capinha, galaxy_a54, dobravel, sem_aparelho, carteira
  inicio_s, fim_s
  estado    a verdade: sem_celular, celular_na_mao, celular_no_ouvido ou olhando_celular
  situacao  opcional: peito, queixo, digitando, ouvido, colo, suporte, noite_ir, negativo_fone...

Gera `<anotacao>_celular.json` e `<anotacao>_aparelhos.csv`:
- por aparelho: quadros, fração com celular detectado, confiança (mediana e p10) e tamanho da caixa em larguras de
  rosto (largura, altura e proporção alto/largo: p10, mediana e p90);
- matriz de confusão por quadro entre os 4 estados, com precisão e sensibilidade (recall) de cada um;
- acerto por situação;
- faixa sugerida de tamanho (p5 a p95 da largura e da altura nos trechos com celular), para descartar caixas pequenas
  ou grandes demais. É sugestão: conferir antes de virar limiar em vision/phone.py.

As medidas por quadro vêm das colunas celular, celular_confianca, celular_largura_rosto, celular_altura_rosto e
celular_proporcao do `_quadros.csv` (analisar_video.py com --celular).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))  # vision/ fica em caixa/
from vision.evaluation import class_report, read_csv_rows, to_float  # noqa: E402

STATES = ("sem_celular", "celular_na_mao", "celular_no_ouvido", "olhando_celular")
MEASURES = ("celular_largura_rosto", "celular_altura_rosto", "celular_proporcao")


def percentile(values, fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[round(fraction * (len(ordered) - 1))], 3)


def collect(annotation_rows, results_dir: Path) -> tuple[list, list]:
    """Quadros dentro dos trechos anotados: (aparelho, situação, estado anotado, linha do _quadros.csv)."""
    frames, missing, cache = [], [], {}
    for row in annotation_rows:
        name = Path(row.get("arquivo", "")).stem
        start, end, truth = to_float(row.get("inicio_s")), to_float(row.get("fim_s")), row.get("estado", "")
        if not name or start is None or end is None or truth not in STATES:
            raise ValueError(f"linha inválida (arquivo, inicio_s, fim_s e estado são obrigatórios): {row}")
        if name not in cache:
            path = results_dir / f"{name}_quadros.csv"
            cache[name] = read_csv_rows(path) if path.is_file() else None
            if cache[name] is None:
                missing.append(str(path))
        for frame in cache[name] or []:
            t = to_float(frame.get("tempo_s"))
            if t is not None and start <= t <= end:
                frames.append((row.get("aparelho") or "?", row.get("situacao") or "sem_situacao", truth, frame))
    return frames, missing


def _values(frames, key: str) -> list[float]:
    return [value for value in (to_float(frame.get(key)) for frame in frames) if value is not None]


def device_table(frames) -> list[dict]:
    groups = defaultdict(list)
    for device, _, _, frame in frames:
        groups[device].append(frame)
    table = []
    for device in sorted(groups):
        rows = groups[device]
        scores = _values(rows, "celular_confianca")
        entry = {"aparelho": device, "quadros": len(rows),
                 "fracao_com_celular_detectado": round(len(scores) / len(rows), 3),
                 "confianca_p10": percentile(scores, 0.1), "confianca_mediana": percentile(scores, 0.5)}
        for measure in MEASURES:
            values, short = _values(rows, measure), measure.removeprefix("celular_")
            entry.update({f"{short}_p10": percentile(values, 0.1), f"{short}_mediana": percentile(values, 0.5),
                          f"{short}_p90": percentile(values, 0.9)})
        table.append(entry)
    return table


def evaluate(frames) -> dict:
    truth = [state for _, _, state, _ in frames]
    predicted = [frame.get("celular") or "sem_celular" for _, _, _, frame in frames]
    with_phone = [frame for _, _, state, frame in frames if state != "sem_celular"]
    situations = defaultdict(lambda: [0, 0])
    for (_, situation, state, _), guess in zip(frames, predicted):
        situations[situation][0] += 1
        situations[situation][1] += guess == state
    return {
        "quadros_avaliados": len(frames),
        "aparelhos": device_table(frames),
        "estados": class_report(truth, predicted, list(STATES)),
        "acerto_por_situacao": {name: {"quadros": count, "acuracia": round(hits / count, 3)}
                                for name, (count, hits) in sorted(situations.items())},
        "faixa_sugerida_em_larguras_de_rosto": {
            measure.removeprefix("celular_"): {"p5": percentile(values, 0.05), "p95": percentile(values, 0.95),
                                               "quadros": len(values)}
            for measure, values in ((m, _values(with_phone, m)) for m in ("celular_largura_rosto", "celular_altura_rosto"))
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Tamanho e confiança por aparelho e matriz de confusão do celular.")
    parser.add_argument("anotacao", help="CSV com os trechos anotados à mão")
    parser.add_argument("--resultados", default=None, help="pasta com os _quadros.csv (padrão: pasta da anotação)")
    args = parser.parse_args(argv)

    annotation = Path(args.anotacao)
    results_dir = Path(args.resultados) if args.resultados else annotation.parent
    try:
        frames, missing = collect(read_csv_rows(annotation), results_dir)
    except ValueError as exc:
        print(f"Anotação inválida: {exc}")
        return 1
    for path in missing:
        print(f"Aviso: não achei {path} (rode o analisar_video.py com --celular).")
    if not frames:
        print("Nenhum quadro dentro dos trechos anotados.")
        return 1
    if "celular_confianca" not in frames[0][3]:
        print("Os _quadros.csv não têm as medidas do celular: rode o analisar_video.py com --celular.")
        return 1

    result = evaluate(frames)
    result["arquivos_faltando"] = missing
    base = annotation.with_suffix("")
    Path(f"{base}_celular.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(f"{base}_aparelhos.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result["aparelhos"][0]))
        writer.writeheader()
        writer.writerows(result["aparelhos"])

    print(f"{result['quadros_avaliados']} quadros anotados. Por estado:")
    for state in STATES:
        scores = result["estados"][state]
        print(f"  {state}: precisão {scores['precisao']}, recall {scores['recall']} ({scores['suporte']} quadros)")
    for entry in result["aparelhos"]:
        print(f"  {entry['aparelho']}: detectado em {entry['fracao_com_celular_detectado']:.0%} dos quadros, "
              f"confiança mediana {entry['confianca_mediana']}, largura mediana {entry['largura_rosto_mediana']} rosto")
    print("Faixa sugerida (larguras de rosto):", result["faixa_sugerida_em_larguras_de_rosto"])
    print(f"Detalhes em {base}_celular.json e {base}_aparelhos.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
