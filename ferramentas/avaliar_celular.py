"""Calibra a detecção de celular com gravações de aparelhos reais (etapa 2 do PENDENCIAS.md e CEL-03 da spec 028).

Roteiro:
  1. Grave cada aparelho em cada situação (na mão na frente do peito, na altura do queixo, digitando, no ouvido, no
     colo, no suporte), variando a distância da câmera e a luz, e grave também os negativos (mão vazia na orelha,
     coçar a orelha, apoiar a cabeça na mão, ajeitar o cabelo, boné, fone de ouvido, carteira, controle, maço de
     cigarro, copo, crachá, óculos na mão).
  2. Rode cada gravação:  python analisar_video.py gravacao.mp4 --celular --saida resultados/
  3. Anote os trechos à mão e rode:  python avaliar_celular.py anotacao_celular.csv --resultados resultados/

Anotação: CSV (vírgula ou ponto e vírgula, ponto decimal), uma linha por trecho:
  arquivo   nome do vídeo (a pasta é ignorada; procura resultados/<nome>_quadros.csv)
  aparelho  ex.: iphone13mini_capinha, galaxy_a54, dobravel, sem_aparelho, carteira
  inicio_s, fim_s
  estado    a verdade: sem_celular, celular_na_mao, celular_no_ouvido ou olhando_celular
  situacao  opcional: peito, queixo, digitando, ouvido, colo, suporte, noite_ir, negativo_fone...
  cena      opcional (spec 028): mao_vazia ou celular_real. Vazia: celular_no_ouvido vira celular_real, e sem_celular
            com mão, orelha, cabelo, cabeça ou boné na situação (ex.: negativo_mao_na_orelha) vira mao_vazia.

Gera `<anotacao>_celular.json`, `<anotacao>_aparelhos.csv` e `<anotacao>_cenas.csv`:
- por aparelho: quadros, fração com celular detectado, confiança (mediana e p10) e tamanho da caixa em larguras de
  rosto (largura, altura e proporção alto/largo: p10, mediana e p90), e os números das verificações da spec 028
  (fração de pele, fração fora da mão e confiança na orelha: p10, mediana e p90; aprovação média nos últimos 2 s);
- matriz de confusão por quadro entre os 4 estados, com precisão e sensibilidade (recall) de cada um;
- acerto por situação;
- faixa sugerida de tamanho (p5 a p95 da largura e da altura nos trechos com celular), para descartar caixas pequenas
  ou grandes demais. É sugestão: conferir antes de virar limiar em vision/phone.py;
- resumo por cena (CEL-03): "mão vazia" (episódios de "no ouvido" e falsos positivos por minuto; meta zero) e "celular
  real" (sensibilidade por quadro, trechos reconhecidos e tempo até o primeiro "no ouvido"; meta inicial 80%), com a
  distribuição dos números das verificações em cada uma, para calibrar SKIN_MAX_FRACTION, OUTSIDE_HAND_MIN_FRACTION e
  EAR_MIN_SCORE. `_cenas.csv` traz uma linha por trecho dessas cenas.

As medidas por quadro vêm das colunas celular, celular_confianca, celular_largura_rosto, celular_altura_rosto e
celular_proporcao do `_quadros.csv` (analisar_video.py com --celular) e, da spec 028, celular_fracao_pele,
celular_fracao_fora_da_mao, celular_confianca_orelha, celular_aprovados_2s e celular_deteccoes_2s
(vision/phone.py: check_columns). Nenhuma imagem é lida nem gravada aqui.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))  # vision/ fica em caixa/
from vision.evaluation import class_report, read_csv_rows, to_float  # noqa: E402

STATES = ("sem_celular", "celular_na_mao", "celular_no_ouvido", "olhando_celular")
MEASURES = ("celular_largura_rosto", "celular_altura_rosto", "celular_proporcao")
# Números das verificações na orelha (spec 028), como o check_columns de vision/phone.py grava no _quadros.csv.
CHECK_MEASURES = ("celular_fracao_pele", "celular_fracao_fora_da_mao", "celular_confianca_orelha")
APPROVED, DETECTIONS = "celular_aprovados_2s", "celular_deteccoes_2s"
EMPTY_HAND, REAL_PHONE = "mao_vazia", "celular_real"
EMPTY_HAND_WORDS = ("mao", "orelha", "cabelo", "cabeca", "bone")
TARGET_SENSITIVITY = 0.8  # meta inicial da spec 028 (CEL-03); o Matheus decide a final (spec 009, pergunta 1)


def percentile(values, fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[round(fraction * (len(ordered) - 1))], 3)


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().strip().lower().replace(" ", "_")


def scene_of(row: dict) -> str | None:
    """Cena do trecho para o resumo da CEL-03: coluna `cena`, ou deduzida do estado e da situação."""
    explicit = _plain(row.get("cena", ""))
    if explicit in (EMPTY_HAND, REAL_PHONE):
        return explicit
    state, situation = row.get("estado", ""), _plain(row.get("situacao", ""))
    if state == "celular_no_ouvido":
        return REAL_PHONE
    if state == "sem_celular" and any(word in situation for word in EMPTY_HAND_WORDS):
        return EMPTY_HAND
    return None


def collect_segments(annotation_rows, results_dir: Path) -> tuple[list, list]:
    """Trechos anotados com os quadros de cada um (linhas do _quadros.csv), e os arquivos que faltaram."""
    segments, missing, cache = [], [], {}
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
        frames = [frame for frame in cache[name] or []
                  if (t := to_float(frame.get("tempo_s"))) is not None and start <= t <= end]
        segments.append({"arquivo": row.get("arquivo", ""), "aparelho": row.get("aparelho") or "?",
                         "situacao": row.get("situacao") or "sem_situacao", "estado": truth, "cena": scene_of(row),
                         "inicio_s": start, "fim_s": end, "quadros": frames})
    return segments, missing


def collect(annotation_rows, results_dir: Path) -> tuple[list, list]:
    """Quadros dentro dos trechos anotados: (aparelho, situação, estado anotado, linha do _quadros.csv)."""
    segments, missing = collect_segments(annotation_rows, results_dir)
    frames = [(segment["aparelho"], segment["situacao"], segment["estado"], frame)
              for segment in segments for frame in segment["quadros"]]
    return frames, missing


def _values(frames, key: str) -> list[float]:
    return [value for value in (to_float(frame.get(key)) for frame in frames) if value is not None]


def check_stats(frames) -> dict:
    """p10, mediana e p90 dos números das verificações e a aprovação média (aprovados ÷ detecções nos últimos 2 s)."""
    stats = {}
    for measure in CHECK_MEASURES:
        values, short = _values(frames, measure), measure.removeprefix("celular_")
        stats.update({f"{short}_p10": percentile(values, 0.1), f"{short}_mediana": percentile(values, 0.5),
                      f"{short}_p90": percentile(values, 0.9)})
    ratios = [approved / detections for approved, detections in
              ((to_float(frame.get(APPROVED)), to_float(frame.get(DETECTIONS))) for frame in frames)
              if approved is not None and detections]
    stats["aprovacao_media"] = round(statistics.fmean(ratios), 3) if ratios else None
    return stats


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
        entry.update(check_stats(rows))
        table.append(entry)
    return table


def _ear_runs(frames) -> list[float]:
    """Início de cada episódio de "no ouvido" (quadros seguidos com o estado), em ordem de tempo."""
    starts, previous = [], False
    for frame in sorted(frames, key=lambda f: to_float(f.get("tempo_s")) or 0.0):
        now = (frame.get("celular") or "") == "celular_no_ouvido"
        if now and not previous:
            starts.append(to_float(frame.get("tempo_s")))
        previous = now
    return starts


def _minutes(segment) -> float:
    times = sorted(t for t in (to_float(frame.get("tempo_s")) for frame in segment["quadros"]) if t is not None)
    if not times:
        return 0.0
    step = statistics.median(b - a for a, b in zip(times, times[1:])) if len(times) > 1 else 0.0
    return max(0.0, min(segment["fim_s"], times[-1]) - max(segment["inicio_s"], times[0]) + step) / 60.0


def scene_summary(segments) -> tuple[dict, list]:
    """Resumo da CEL-03 por cena e uma linha por trecho (para o _cenas.csv)."""
    rows, groups = [], defaultdict(list)
    for segment in segments:
        if segment["cena"] is None or not segment["quadros"]:
            continue
        frames, minutes = segment["quadros"], _minutes(segment)
        runs = _ear_runs(frames)
        at_ear = sum(1 for frame in frames if (frame.get("celular") or "") == "celular_no_ouvido")
        row = {"arquivo": segment["arquivo"], "aparelho": segment["aparelho"], "situacao": segment["situacao"],
               "cena": segment["cena"], "inicio_s": segment["inicio_s"], "fim_s": segment["fim_s"],
               "quadros": len(frames), "minutos": round(minutes, 3), "fracao_quadros_no_ouvido": round(at_ear / len(frames), 3),
               "episodios_no_ouvido": len(runs),
               "primeiro_no_ouvido_s": round(runs[0] - segment["inicio_s"], 2) if runs else None,
               **check_stats(frames)}
        rows.append(row)
        groups[segment["cena"]].append((row, frames, at_ear))

    summary = {}
    for scene in (EMPTY_HAND, REAL_PHONE):
        entries = groups.get(scene, [])
        if not entries:
            continue
        frames = [frame for _, segment_frames, _ in entries for frame in segment_frames]
        minutes = sum(row["minutos"] for row, _, _ in entries)
        at_ear = sum(count for _, _, count in entries)
        episodes = sum(row["episodios_no_ouvido"] for row, _, _ in entries)
        entry = {"trechos": len(entries), "quadros": len(frames), "minutos": round(minutes, 2),
                 "fracao_quadros_no_ouvido": round(at_ear / len(frames), 3), "episodios_no_ouvido": episodes}
        if scene == EMPTY_HAND:
            entry["falsos_positivos_por_minuto"] = round(episodes / minutes, 2) if minutes else None
            entry["meta_zero_no_ouvido"] = episodes == 0
        else:
            sensitivity = at_ear / len(frames)
            latencies = [row["primeiro_no_ouvido_s"] for row, _, _ in entries if row["primeiro_no_ouvido_s"] is not None]
            entry.update(sensibilidade=round(sensitivity, 3),
                         trechos_com_no_ouvido=sum(1 for row, _, _ in entries if row["episodios_no_ouvido"]),
                         primeiro_no_ouvido_mediana_s=round(statistics.median(latencies), 2) if latencies else None,
                         meta_sensibilidade=sensitivity >= TARGET_SENSITIVITY)
        entry.update(check_stats(frames))
        summary[scene] = entry
    return summary, rows


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
    parser = argparse.ArgumentParser(description="Tamanho e confiança por aparelho, matriz de confusão do celular e "
                                                 "resumo por cena (mão vazia × celular real).")
    parser.add_argument("anotacao", help="CSV com os trechos anotados à mão")
    parser.add_argument("--resultados", default=None, help="pasta com os _quadros.csv (padrão: pasta da anotação)")
    args = parser.parse_args(argv)

    annotation = Path(args.anotacao)
    results_dir = Path(args.resultados) if args.resultados else annotation.parent
    try:
        segments, missing = collect_segments(read_csv_rows(annotation), results_dir)
    except ValueError as exc:
        print(f"Anotação inválida: {exc}")
        return 1
    frames = [(segment["aparelho"], segment["situacao"], segment["estado"], frame)
              for segment in segments for frame in segment["quadros"]]
    for path in missing:
        print(f"Aviso: não achei {path} (rode o analisar_video.py com --celular).")
    if not frames:
        print("Nenhum quadro dentro dos trechos anotados.")
        return 1
    if "celular_confianca" not in frames[0][3]:
        print("Os _quadros.csv não têm as medidas do celular: rode o analisar_video.py com --celular.")
        return 1
    if CHECK_MEASURES[0] not in frames[0][3]:
        print("Aviso: os _quadros.csv não têm os números das verificações da spec 028 (celular_fracao_pele...): "
              "o resumo por cena sai só com os estados.")

    result = evaluate(frames)
    result["cenas"], scene_rows = scene_summary(segments)
    result["arquivos_faltando"] = missing
    base = annotation.with_suffix("")
    Path(f"{base}_celular.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(f"{base}_aparelhos.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result["aparelhos"][0]))
        writer.writeheader()
        writer.writerows(result["aparelhos"])
    if scene_rows:
        with open(f"{base}_cenas.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(scene_rows[0]))
            writer.writeheader()
            writer.writerows(scene_rows)

    print(f"{result['quadros_avaliados']} quadros anotados. Por estado:")
    for state in STATES:
        scores = result["estados"][state]
        print(f"  {state}: precisão {scores['precisao']}, recall {scores['recall']} ({scores['suporte']} quadros)")
    for entry in result["aparelhos"]:
        print(f"  {entry['aparelho']}: detectado em {entry['fracao_com_celular_detectado']:.0%} dos quadros, "
              f"confiança mediana {entry['confianca_mediana']}, largura mediana {entry['largura_rosto_mediana']} rosto")
    print("Faixa sugerida (larguras de rosto):", result["faixa_sugerida_em_larguras_de_rosto"])
    empty, real = result["cenas"].get(EMPTY_HAND), result["cenas"].get(REAL_PHONE)
    if empty:
        print(f"Mão vazia ({empty['minutos']} min): {empty['episodios_no_ouvido']} episódio(s) de 'no ouvido', "
              f"{empty['falsos_positivos_por_minuto']} por minuto (meta: zero). Pele mediana {empty['fracao_pele_mediana']}, "
              f"p10 {empty['fracao_pele_p10']}")
    if real:
        print(f"Celular real ({real['minutos']} min): sensibilidade {real['sensibilidade']:.0%} "
              f"(meta {TARGET_SENSITIVITY:.0%}), {real['trechos_com_no_ouvido']} de {real['trechos']} trechos. "
              f"Pele p90 {real['fracao_pele_p90']}, fora da mão p10 {real['fracao_fora_da_mao_p10']}, "
              f"confiança na orelha p10 {real['confianca_orelha_p10']}")
    outputs = f"{base}_celular.json e {base}_aparelhos.csv" + (f" e {base}_cenas.csv" if scene_rows else "")
    print(f"Detalhes em {outputs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
