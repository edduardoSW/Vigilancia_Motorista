"""Avaliação em dataset rotulado, com validação por sujeito: o mesmo motorista nunca fica no treino e no teste.

Etapa 1, extrair (precisa do MediaPipe; é lenta e fica em cache):
  python avaliar_dataset.py extrair lista.csv --saida avaliacao/
Etapa 2, avaliar (rápida, só lê os CSVs):
  python avaliar_dataset.py avaliar avaliacao/
  python avaliar_dataset.py avaliar avaliacao/ --classificador     # precisa de ferramentas/requirements.txt

lista.csv (vírgula ou ponto e vírgula) com as colunas: video, sujeito, rotulo e, opcional, calibracao.
- rotulo: alerta ou sonolento. Também aceita 0 (alerta) e 10 (sonolento), como no UTA-RLDD; 5 (baixa vigilância)
  fica de fora, a não ser com --baixa-vigilancia alerta|sonolento.
- calibracao: "sim" no vídeo alerta que dá a linha de base do sujeito (no UTA-RLDD, o vídeo 0). O começo dele
  calibra e fica fora da avaliação. Sem vídeo marcado, cada vídeo calibra com o próprio começo, o que é menos
  realista, porque o começo de um vídeo sonolento já está sonolento.

O que é medido:
- Uma linha a cada 10 s, com as métricas dos últimos 60 s e o rótulo do vídeo. Linhas vizinhas se sobrepõem e não
  são independentes: trate os números como estimativa otimista.
- Detector por regras (o do dispositivo): prevê "sonolento" quando o nível de sonolência chega a --limiar-nivel (2).
- Precisão, recall e F1 por classe (a prioridade é o recall de "sonolento") e matriz de confusão.
- Falsos alarmes por hora nos vídeos alerta e latência até o primeiro alarme nos vídeos sonolentos.
- --classificador: regressão logística nas métricas de janela e nos z-scores, deixando um sujeito de fora por vez.

Datasets públicos de sonolência (UTA-RLDD, NTHU-DDD, DMD etc.) costumam ser liberados só para pesquisa:
confira a licença antes de usar os resultados em produto comercial.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))  # vision/ fica em caixa/
from vision.evaluation import (  # noqa: E402
    alert_latency,
    class_report,
    false_alarms_per_hour,
    leave_one_subject_out,
    read_csv_rows,
    to_float,
)

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

CLASSES = ("alerta", "sonolento")
ROW_STEP_S = 10.0
WINDOW_S = 60.0
NON_FEATURES = {"sujeito", "video", "rotulo", "tempo_s", "nivel_sonolencia", "alarme", "nivel_risco", "fps"}


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_") or "x"


def normalize_label(value: str, low_vigilance: str | None = None) -> str | None:
    value = value.strip().lower()
    if value in ("alerta", "alert", "0"):
        return "alerta"
    if value in ("sonolento", "drowsy", "10"):
        return "sonolento"
    if value in ("5", "baixa_vigilancia", "low_vigilant"):
        return low_vigilance
    raise ValueError(f"rótulo desconhecido: {value!r} (use alerta, sonolento, 0, 5 ou 10)")


def read_manifest(path, low_vigilance: str | None = None) -> list[dict]:
    base = Path(path).resolve().parent
    items = []
    for row in read_csv_rows(path):
        label = normalize_label(row["rotulo"], low_vigilance)
        if label is None:
            continue
        video = Path(row["video"])
        items.append({
            "video": video if video.is_absolute() else base / video,
            "sujeito": row["sujeito"],
            "rotulo": label,
            "calibracao": row.get("calibracao", "").lower() in ("sim", "1", "true", "x"),
        })
    return items


def video_id(item: dict) -> str:
    return f"{safe_name(item['sujeito'])}__{safe_name(Path(item['video']).stem)}"


# ---------------------------------------------------------------- etapa 1: extrair

def process_video(item: dict, profile, baseline, calibration_s: float, out_dir: Path):
    """Roda o dispositivo no vídeo e grava as linhas de janela e os alarmes. Retorna (perfil, linha de base)."""
    import cv2

    from vision.calibration import Calibrator
    from vision.drowsiness import DrowsinessMonitor
    from vision.engine import DriverStateEngine
    from vision.eye_state import EyeStateClassifier
    from vision.face import FaceAnalyzer

    capture = cv2.VideoCapture(str(item["video"]))
    if not capture.isOpened():
        raise RuntimeError(f"não foi possível abrir {item['video']}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    fps = fps if 1 < fps <= 1000 else 30.0

    calibrator = None
    if profile is None:
        calibrator = Calibrator(min_seconds=calibration_s, max_seconds=calibration_s, target_blinks=10 ** 9)
    engine = DriverStateEngine(DrowsinessMonitor(profile=profile, calibrator=calibrator), activation_mode="local",
                               background_baseline=False)
    engine.trip_baseline = baseline
    analyzer = FaceAnalyzer(classifier=EyeStateClassifier())
    rows, alarms = [], []
    evaluation_start = None if calibrator is not None else 0.0
    next_row = None
    level, alarm_in_row, alarm_before = 0, False, False
    index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            t = index / fps
            index += 1
            state = engine.update(analyzer.analyze(frame, t))
            if evaluation_start is None:
                if state.drowsiness.calibrating:
                    continue
                evaluation_start = t
            if next_row is None:
                next_row = evaluation_start + WINDOW_S
            level = max(level, state.drowsiness.level)
            if state.alarm and not alarm_before:
                alarms.append(round(t - evaluation_start, 2))
                alarm_in_row = True
            alarm_before = state.alarm
            if t >= next_row:
                next_row += ROW_STEP_S
                row = {"sujeito": item["sujeito"], "video": Path(item["video"]).name, "rotulo": item["rotulo"],
                       "tempo_s": round(t - evaluation_start, 1), "nivel_sonolencia": level, "alarme": int(alarm_in_row),
                       "nivel_risco": state.risk.level}
                row.update({key: value for key, value in state.window.items()
                            if isinstance(value, (int, float)) and not isinstance(value, bool)})
                row.update({f"z_{key}": value for key, value in state.zscores.items()})
                rows.append(row)
                level, alarm_in_row = 0, False
    finally:
        capture.release()
        analyzer.close()
        engine.close()

    evaluated = index / fps - evaluation_start if evaluation_start is not None else 0.0
    identifier = video_id(item)
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with open(out_dir / "janelas" / f"{identifier}.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns or ["sujeito"])
        writer.writeheader()
        writer.writerows(rows)
    info = {"video": str(item["video"]), "sujeito": item["sujeito"], "rotulo": item["rotulo"], "fps": round(fps, 2),
            "segundos_avaliados": round(max(evaluated, 0.0), 1), "alarmes_s": alarms,
            "calibrou_neste_video": calibrator is not None}
    (out_dir / "videos" / f"{identifier}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {identifier}: {len(rows)} linhas, {info['segundos_avaliados']:.0f} s avaliados, {len(alarms)} alarmes")
    return engine.drowsiness.profile, engine.trip_baseline


def _save_baseline(baseline, path: Path) -> None:
    if baseline is None:
        return
    data = baseline.to_dict()
    data["qualidade"] = baseline.quality
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_baseline(path: Path):
    from vision.baseline import Baseline

    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    baseline = Baseline.from_dict(data)
    baseline.source, baseline.quality = "viagem", float(data.get("qualidade", 0.75))
    return baseline


def extract(manifest: Path, out_dir: Path, calibration_s: float, low_vigilance: str | None, redo: bool) -> int:
    from vision.eyes import DriverProfile

    items = read_manifest(manifest, low_vigilance)
    for folder in ("janelas", "videos", "perfis"):
        (out_dir / folder).mkdir(parents=True, exist_ok=True)
    subjects = defaultdict(list)
    for item in items:
        subjects[item["sujeito"]].append(item)

    for subject, videos in sorted(subjects.items()):
        print(f"Sujeito {subject}: {len(videos)} vídeos")
        calibration = next((video for video in videos if video["calibracao"]), None)
        profile_path = out_dir / "perfis" / f"{safe_name(subject)}.json"
        baseline_path = out_dir / "perfis" / f"{safe_name(subject)}_linha_de_base.json"
        profile = baseline = None
        if calibration is not None:
            done = (out_dir / "janelas" / f"{video_id(calibration)}.csv").is_file() and profile_path.is_file()
            if done and not redo:
                profile, baseline = DriverProfile.load(profile_path), _load_baseline(baseline_path)
                print(f"  {video_id(calibration)}: já extraído (perfil em cache)")
            else:
                profile, baseline = process_video(calibration, None, None, calibration_s, out_dir)
                if profile is not None:
                    profile.save(profile_path)
                    _save_baseline(baseline, baseline_path)
            if profile is None:
                print("  calibração sem rosto suficiente: os outros vídeos calibram com o próprio começo")
        for item in videos:
            if item is calibration:
                continue
            if (out_dir / "janelas" / f"{video_id(item)}.csv").is_file() and not redo:
                print(f"  {video_id(item)}: já extraído")
                continue
            process_video(item, profile, baseline if profile is not None else None, calibration_s, out_dir)
    return 0


# ---------------------------------------------------------------- etapa 2: avaliar

def load_extracted(out_dir: Path) -> tuple[list[dict], list[dict]]:
    rows = []
    for path in sorted((out_dir / "janelas").glob("*.csv")):
        for row in read_csv_rows(path):
            converted = {key: (value if key in ("sujeito", "video", "rotulo") else to_float(value)) for key, value in row.items()}
            rows.append(converted)
    videos = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((out_dir / "videos").glob("*.json"))]
    return rows, videos


def rule_based(rows: list[dict], level_threshold: int) -> dict:
    y_true = [row["rotulo"] for row in rows]
    y_pred = ["sonolento" if (row.get("nivel_sonolencia") or 0) >= level_threshold else "alerta" for row in rows]
    report = class_report(y_true, y_pred, CLASSES)
    per_subject = {}
    for subject, _, test in leave_one_subject_out(rows):
        truth = [row["rotulo"] for row in test]
        predicted = ["sonolento" if (row.get("nivel_sonolencia") or 0) >= level_threshold else "alerta" for row in test]
        per_subject[subject] = class_report(truth, predicted, CLASSES)["sonolento"]["recall"]
    report["recall_sonolento_por_sujeito"] = per_subject
    return report


def feature_names(rows: list[dict]) -> list[str]:
    counts = defaultdict(int)
    for row in rows:
        for key, value in row.items():
            if key not in NON_FEATURES and isinstance(value, float):
                counts[key] += 1
    return sorted(key for key, count in counts.items() if count >= 0.5 * len(rows))


def classifier(rows: list[dict]) -> dict:
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return {"erro": "scikit-learn não instalado: pip install -r ferramentas/requirements.txt"}

    features = feature_names(rows)
    if not features:
        return {"erro": "nenhuma métrica numérica suficiente nas janelas"}

    def matrix(part):
        return [[math.nan if row.get(name) is None else row[name] for name in features] for row in part]

    y_true, y_pred, skipped = [], [], []
    for subject, train, test in leave_one_subject_out(rows):
        assert not {row["sujeito"] for row in train} & {row["sujeito"] for row in test}
        if len({row["rotulo"] for row in train}) < 2:
            skipped.append(subject)
            continue
        model = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                              LogisticRegression(class_weight="balanced", max_iter=2000))
        model.fit(matrix(train), [row["rotulo"] for row in train])
        y_true.extend(row["rotulo"] for row in test)
        y_pred.extend(model.predict(matrix(test)))
    report = class_report(y_true, list(y_pred), CLASSES)
    report.update(metricas_usadas=features, sujeitos_pulados=skipped,
                  validacao="deixa um sujeito de fora por vez (LeaveOneGroupOut)")
    return report


def evaluate(out_dir: Path, level_threshold: int = 2, use_classifier: bool = False) -> dict:
    rows, videos = load_extracted(out_dir)
    rows = [row for row in rows if row.get("rotulo") in CLASSES]
    if not rows:
        raise RuntimeError(f"nenhuma janela extraída em {out_dir / 'janelas'}")
    report = {
        "janelas": len(rows),
        "sujeitos": len({row["sujeito"] for row in rows}),
        "videos": len(videos),
        "aviso": "Janelas vizinhas se sobrepõem (60 s a cada 10 s): as métricas por janela são otimistas.",
        "regras_do_dispositivo": dict(rule_based(rows, level_threshold), limiar_nivel=level_threshold),
        "falsos_alarmes_por_hora": false_alarms_per_hour(videos),
        "latencia_do_alerta": alert_latency(videos),
    }
    if use_classifier:
        report["classificador"] = classifier(rows)
    return report


def print_report(report: dict) -> None:
    rules = report["regras_do_dispositivo"]
    print(f"{report['janelas']} janelas, {report['sujeitos']} sujeitos, {report['videos']} vídeos.")
    for label in CLASSES:
        item = rules[label]
        print(f"  Regras, {label}: precisão {item['precisao']}, recall {item['recall']}, F1 {item['f1']} (n={item['suporte']})")
    print(f"  Falsos alarmes por hora (vídeos alerta): {report['falsos_alarmes_por_hora']}")
    latency = report["latencia_do_alerta"]
    print(f"  Vídeos sonolentos com alarme: {latency['com_alarme']} de {latency['videos_sonolentos']}; "
          f"latência mediana {latency['latencia_mediana_s']} s")
    model = report.get("classificador")
    if model:
        if "erro" in model:
            print(f"  Classificador: {model['erro']}")
        else:
            for label in CLASSES:
                item = model[label]
                print(f"  Classificador, {label}: precisão {item['precisao']}, recall {item['recall']}, F1 {item['f1']}")
    print(f"  {report['aviso']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Avaliação em dataset rotulado, com validação por sujeito.")
    commands = parser.add_subparsers(dest="comando", required=True)
    extract_cmd = commands.add_parser("extrair", help="roda o detector nos vídeos e guarda as janelas")
    extract_cmd.add_argument("lista", help="CSV com video, sujeito, rotulo e calibracao")
    extract_cmd.add_argument("--saida", default="avaliacao")
    extract_cmd.add_argument("--calibracao", type=float, default=300.0, help="segundos de calibração (padrão 300)")
    extract_cmd.add_argument("--baixa-vigilancia", choices=CLASSES, default=None)
    extract_cmd.add_argument("--refazer", action="store_true", help="ignora o cache e extrai de novo")
    evaluate_cmd = commands.add_parser("avaliar", help="calcula as métricas a partir das janelas")
    evaluate_cmd.add_argument("pasta", help="pasta usada em --saida na extração")
    evaluate_cmd.add_argument("--limiar-nivel", type=int, default=2, choices=(1, 2, 3))
    evaluate_cmd.add_argument("--classificador", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    if args.comando == "extrair":
        return extract(Path(args.lista), Path(args.saida), args.calibracao, args.baixa_vigilancia, args.refazer)
    report = evaluate(Path(args.pasta), args.limiar_nivel, args.classificador)
    target = Path(args.pasta) / "relatorio.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print_report(report)
    print(f"Relatório completo em {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
