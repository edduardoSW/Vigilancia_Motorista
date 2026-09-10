"""Analisa um vídeo gravado: piscadas, sonolência, sinais de ativação, celular e desempenho.

Exemplos:
  python analisar_video.py video.mp4
  python analisar_video.py video.mp4 --calibracao 120 --saida resultados/
  python analisar_video.py video.mp4 --perfil ~/.drivesafe/perfis/joao.json --celular
  python analisar_video.py video_ir.mp4 --camera-ir sim

Gera (ao lado do vídeo ou em --saida), em CSV com vírgula e ponto decimal:
  <nome>_quadros.csv   medidas quadro a quadro
  <nome>_piscadas.csv  cada piscada: início, fim, duração, amplitude, velocidades da pálpebra e AVR
  <nome>_janelas.csv   uma linha por segundo: métricas de janela, z-scores, sinais de ativação e nível de risco
  <nome>_eventos.csv   alertas que o dispositivo teria disparado
  <nome>_grafico.png   EAR, abertura do olho e nível de risco ao longo do tempo
  <nome>_resumo.json   perfil calibrado, estatísticas gerais e por trecho, desempenho
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

RISK_NAMES = ("normal", "atenção", "alto", "crítico")


def _stats(durations):
    if not durations:
        return {"piscadas": 0}
    result = {
        "piscadas": len(durations),
        "duracao_mediana_ms": round(statistics.median(durations) * 1000),
        "duracao_media_ms": round(statistics.mean(durations) * 1000),
    }
    if len(durations) >= 10:
        result["duracao_p90_ms"] = round(statistics.quantiles(durations, n=10)[-1] * 1000)
    return result


def _fmt(value, digits: int = 3):
    if value is None:
        return ""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return value


def _percentile(ordered, fraction: float) -> float:
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def _window_row(t: float, state) -> dict:
    row = {"tempo_s": round(t, 2)}
    row.update({key: value for key, value in state.window.items() if value is None or isinstance(value, (int, float, str))})
    row.update({f"z_{key}": value for key, value in state.zscores.items()})
    if state.activation is not None:
        row.update(ativacao_indice=state.activation.index, ativacao_confianca=state.activation.confidence,
                   ativacao_estado=state.activation.state, ativacao_sinais=";".join(state.activation.signals))
    row.update(nivel_sonolencia=state.drowsiness.level, nivel_risco=state.risk.level,
               motivos=";".join(state.risk.reasons), linha_de_base=state.baseline_source or "")
    if state.phone is not None:
        row["celular"] = state.phone.state
    return row


def save_plot(path: Path, times, ears, openness, risk_levels, blinks, calibration_end, threshold) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib não instalado: gráfico não gerado.")
        return False

    nan = float("nan")
    figure, (ax_ear, ax_open, ax_risk) = plt.subplots(3, 1, figsize=(14, 8), sharex=True,
                                                      gridspec_kw={"height_ratios": [3, 2, 1]})
    ax_ear.plot(times, [nan if value is None else value for value in ears], lw=0.6, color="tab:blue")
    for blink in blinks:
        ax_ear.axvspan(blink.start, blink.end, color="tab:orange", alpha=0.3, lw=0)
    ax_ear.set_ylabel("EAR")
    ax_ear.set_title("EAR ao longo do tempo (faixas laranja: piscadas detectadas)")
    ax_open.plot(times, [nan if value is None else value for value in openness], lw=0.6, color="tab:green")
    ax_open.axhline(threshold, color="gray", ls="--", lw=0.8)
    ax_open.set_ylim(-0.05, 1.3)
    ax_open.set_ylabel("abertura\n(1 = normal da pessoa)")
    ax_risk.step(times, risk_levels, where="post", color="tab:red", lw=1.0)
    ax_risk.set_yticks([0, 1, 2, 3], list(RISK_NAMES))
    ax_risk.set_ylim(-0.3, 3.3)
    ax_risk.set_xlabel("tempo (s)")
    if calibration_end is not None:
        for axis in (ax_ear, ax_open, ax_risk):
            axis.axvline(calibration_end, color="gray", ls=":", lw=1.0)
    figure.tight_layout()
    figure.savefig(path, dpi=110)
    plt.close(figure)
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extrai piscadas, sonolência, sinais de ativação e celular de um vídeo.")
    parser.add_argument("video")
    parser.add_argument("--calibracao", type=float, default=None,
                        help="segundos de calibração no início (padrão: 300, ou 1/3 do vídeo se ele for curto)")
    parser.add_argument("--perfil", help="usa um perfil salvo em vez de calibrar com o próprio vídeo")
    parser.add_argument("--saida", help="pasta dos resultados (padrão: pasta do vídeo)")
    parser.add_argument("--trecho", type=float, default=None,
                        help="tamanho em segundos de cada trecho do resumo (padrão: 300, ou 60 em vídeos curtos)")
    parser.add_argument("--camera-ir", choices=("auto", "sim", "nao"), default="auto",
                        help="vídeo de câmera infravermelha (libera a medida da pupila)")
    parser.add_argument("--celular", action="store_true", help="também detecta uso de celular (mais lento)")
    parser.add_argument("--sem-grafico", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    import cv2

    from vision import __version__
    from vision.calibration import COMPLETE_BLINK_OPENNESS, MAX_BLINK_S, SHORT_CLOSURE_S, Calibrator
    from vision.drowsiness import DrowsinessMonitor
    from vision.engine import DriverStateEngine
    from vision.eye_state import EyeStateClassifier
    from vision.eyes import (
        MAX_FRAME_GAP_S,
        MIN_FPS_FOR_VELOCITY,
        P80_OPENNESS,
        DriverProfile,
        EyeStateTracker,
        OpennessModel,
        Sample,
    )
    from vision.face import FaceAnalyzer
    from vision.visibility import mask_eye_signals

    video = Path(args.video)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        print(f"Não foi possível abrir o vídeo {video}.")
        return 1
    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    if fps <= 1 or fps > 1000:
        print(f"FPS do arquivo inválido ({fps}); assumindo 30.")
        fps = 30.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if total_frames else 0.0

    profile = None
    calibrator = None
    if args.perfil:
        profile = DriverProfile.load(Path(args.perfil).expanduser())
        if profile is None:
            print(f"Perfil {args.perfil} não encontrado ou inválido.")
            return 1
    else:
        seconds = args.calibracao if args.calibracao else (300.0 if duration >= 900 else max(30.0, duration / 3))
        calibrator = Calibrator(min_seconds=seconds, max_seconds=seconds, target_blinks=10 ** 9)
        print(f"Calibrando com os primeiros {seconds:.0f} s de rosto visível.")

    segment = args.trecho if args.trecho else (300.0 if duration >= 1200 else 60.0)
    output = Path(args.saida) if args.saida else video.parent
    output.mkdir(parents=True, exist_ok=True)
    base = output / video.stem

    analyzer = FaceAnalyzer(classifier=EyeStateClassifier(), infrared=args.camera_ir)
    phone = None
    if args.celular:
        from vision.phone import PhoneDetector, PhoneMonitor

        phone = PhoneMonitor(PhoneDetector(), background=False)
    engine = DriverStateEngine(DrowsinessMonitor(profile=profile, calibrator=calibrator), activation_mode="local",
                               phone=phone, background_baseline=False)

    samples, frame_info, window_rows, events, latencies = [], [], [], [], []
    last_window = None
    calibration_end = None
    index = 0
    next_report = 0.1
    started_all = time.perf_counter()
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            t = index / fps
            started = time.perf_counter()
            metrics = analyzer.analyze(frame, timestamp=t)
            state = engine.update(metrics, frame)
            latencies.append((time.perf_counter() - started) * 1000.0)

            measured = metrics if state.visibility.eyes_ok else mask_eye_signals(metrics)
            samples.append(Sample.from_metrics(measured))
            if calibrator is not None and calibration_end is None and not state.drowsiness.calibrating:
                calibration_end = t
            frame_info.append({
                "olhos_visiveis": state.visibility.eyes_ok, "iris_px": metrics.iris_diameter_px,
                "pupila_iris": metrics.pupil_ratio, "pupila_qualidade": metrics.pupil_quality,
                "infravermelho": metrics.infrared, "luminancia_olho": metrics.eye_luminance,
                "olhar_x": metrics.gaze_x, "olhar_y": metrics.gaze_y, "nivel_sonolencia": state.drowsiness.level,
                "nivel_risco": state.risk.level, "celular": state.phone.state if state.phone is not None else "",
                "latencia_ms": latencies[-1],
            })
            if state.window and state.window is not last_window:
                last_window = state.window
                window_rows.append(_window_row(t, state))
            events.extend((t, event) for event in state.events)
            index += 1
            if total_frames and index / total_frames >= next_report:
                print(f"  {int(next_report * 100)}%")
                next_report += 0.1
    finally:
        capture.release()
        analyzer.close()
        engine.close()
    processing_s = time.perf_counter() - started_all

    if not samples:
        print("O vídeo não tem quadros legíveis.")
        return 1
    final_profile = engine.drowsiness.profile
    if final_profile is None:
        print("Não houve rosto suficiente para calibrar; nada a medir.")
        return 1

    # Segunda passada com o perfil final: piscadas e abertura coerentes do início ao fim.
    model = OpennessModel(final_profile)
    tracker = EyeStateTracker()
    openness_values, blinks = [], []
    closed_by_segment, valid_by_segment = {}, {}
    pending, last_t = 0.0, None
    for sample in samples:
        openness, _ = model.openness(sample)
        openness_values.append(openness)
        dt = sample.timestamp - last_t if last_t is not None and 0 < sample.timestamp - last_t <= MAX_FRAME_GAP_S else 0.0
        last_t = sample.timestamp
        key = int(sample.timestamp // segment)
        if openness is not None:
            valid_by_segment[key] = valid_by_segment.get(key, 0.0) + dt
        blink = tracker.update(sample.timestamp, openness)
        if openness is not None and openness <= P80_OPENNESS:
            pending += dt
            if tracker.closed_for >= SHORT_CLOSURE_S:
                closed_by_segment[key] = closed_by_segment.get(key, 0.0) + pending
                pending = 0.0
        elif openness is not None:
            pending = 0.0
        if blink is not None:
            blinks.append(blink)

    with open(f"{base}_quadros.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        extra = list(frame_info[0].keys())
        writer.writerow(["tempo_s", "rosto", "ear", "abertura", "pontuacao_piscada", "prob_olho_aberto",
                         "boca_aberta", "pitch", "yaw", "distancia_olhos_px", *extra])
        for sample, openness, info in zip(samples, openness_values, frame_info):
            writer.writerow([
                f"{sample.timestamp:.3f}", int(sample.face_found), _fmt(sample.ear, 4), _fmt(openness),
                _fmt(sample.blink_score), _fmt(sample.eye_open_prob), _fmt(sample.jaw_open),
                _fmt(sample.pitch, 1), _fmt(sample.yaw, 1), _fmt(sample.eye_distance_px, 1),
                *(_fmt(info[name], 1 if name in ("iris_px", "luminancia_olho", "latencia_ms") else 3) for name in extra),
            ])

    with open(f"{base}_piscadas.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["inicio_s", "fim_s", "duracao_ms", "fechado_80_ms", "menor_abertura", "amplitude",
                         "vel_fechamento", "vel_abertura", "avr_fechamento_ms", "avr_abertura_ms", "completa"])
        for blink in blinks:
            complete = blink.min_openness <= COMPLETE_BLINK_OPENNESS and blink.duration <= MAX_BLINK_S
            writer.writerow([
                f"{blink.start:.3f}", f"{blink.end:.3f}", round(blink.duration * 1000), round(blink.closed_duration * 1000),
                f"{blink.min_openness:.3f}", _fmt(blink.amplitude), _fmt(blink.closing_velocity, 2),
                _fmt(blink.opening_velocity, 2), "" if blink.closing_avr is None else round(blink.closing_avr * 1000, 1),
                "" if blink.opening_avr is None else round(blink.opening_avr * 1000, 1), int(complete),
            ])

    columns = list(dict.fromkeys(key for row in window_rows for key in row))
    with open(f"{base}_janelas.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns or ["tempo_s"])
        writer.writeheader()
        writer.writerows({key: _fmt(value) for key, value in row.items()} for row in window_rows)

    with open(f"{base}_eventos.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tempo_s", "tipo", "risco", "duracao_s", "detalhes"])
        for t, event in events:
            writer.writerow([f"{t:.2f}", event.alert_type, event.risk_level, event.duration,
                             json.dumps(event.details, ensure_ascii=False)])

    plot = None
    if not args.sem_grafico:
        plot_path = Path(f"{base}_grafico.png")
        if save_plot(plot_path, [s.timestamp for s in samples], [s.ear for s in samples], openness_values,
                     [info["nivel_risco"] for info in frame_info], blinks, calibration_end, P80_OPENNESS):
            plot = plot_path.name

    complete = [b for b in blinks if b.min_openness <= COMPLETE_BLINK_OPENNESS and b.duration <= MAX_BLINK_S]
    segments = []
    for key in sorted(set(valid_by_segment) | {int(b.end // segment) for b in complete}):
        valid = valid_by_segment.get(key, 0.0)
        in_segment = [b.duration for b in complete if int(b.end // segment) == key]
        entry = {"inicio_s": key * segment, "fim_s": (key + 1) * segment, "rosto_visivel_s": round(valid, 1)}
        entry.update(_stats(in_segment))
        if valid > 0:
            entry["piscadas_por_min"] = round(len(in_segment) / (valid / 60), 1)
            entry["perclos"] = round(closed_by_segment.get(key, 0.0) / valid, 4)
        entry["fechamentos_500ms"] = sum(1 for b in blinks if int(b.end // segment) == key and b.closed_duration >= 0.5)
        segments.append(entry)

    frames = len(samples)
    ordered = sorted(latencies)
    avr = [b.closing_avr for b in complete if b.closing_avr is not None]
    indices = [row["ativacao_indice"] for row in window_rows if row.get("ativacao_indice") is not None]
    pupil_reasons = Counter(info["pupila_qualidade"] for info in frame_info if info["pupila_qualidade"])
    valid_total = sum(valid_by_segment.values())
    warnings = []
    if fps < 24:
        warnings.append("Duração da piscada abaixo de ~25 fps é imprecisa (Navascues-Cornago et al., 2026).")
    if fps < MIN_FPS_FOR_VELOCITY:
        warnings.append("Velocidade da pálpebra e AVR precisam de ~28 fps ou mais.")
    summary = {
        "video": str(video),
        "fps": round(fps, 2),
        "quadros": frames,
        "duracao_s": round(frames / fps, 1),
        "quadros_com_rosto": round(sum(1 for s in samples if s.face_found) / frames, 3),
        "versao_drivesafe": __version__,
        "perfil": final_profile.summary(),
        "perfil_origem": "arquivo" if args.perfil else "calibracao_do_video",
        "fim_da_calibracao_s": None if calibration_end is None else round(calibration_end, 1),
        "geral": dict(_stats([b.duration for b in complete]),
                      piscadas_por_min=round(len(complete) / (valid_total / 60), 1) if valid_total else None,
                      perclos=round(sum(closed_by_segment.values()) / valid_total, 4) if valid_total else None,
                      fechamentos_500ms=sum(1 for b in blinks if b.closed_duration >= 0.5),
                      maior_fechamento_ms=round(max((b.closed_duration for b in blinks), default=0.0) * 1000),
                      avr_fechamento_mediana_ms=round(statistics.median(avr) * 1000, 1) if avr else None),
        "trechos": segments,
        "eventos": dict(Counter(event.alert_type for _, event in events)),
        "nivel_de_risco_s": {RISK_NAMES[level]: round(sum(1 for info in frame_info if info["nivel_risco"] == level) / fps, 1)
                             for level in range(4)},
        "olhos_nao_visiveis_s": round(sum(1 for info in frame_info if not info["olhos_visiveis"]) / fps, 1),
        "camera_infravermelha": round(sum(1 for info in frame_info if info["infravermelho"]) / frames, 3),
        "pupila": {"quadros_com_medida": round(sum(1 for info in frame_info if info["pupila_iris"] is not None) / frames, 3),
                   "motivo_mais_comum": pupil_reasons.most_common(1)[0][0] if pupil_reasons else None},
        "sinais_de_ativacao": {
            "aviso": "Sinais compatíveis com ativação atípica não são diagnóstico de uso de substância.",
            "indice_max": max(indices) if indices else None,
            "segundos_com_sinais_compativeis": sum(1 for row in window_rows
                                                   if row.get("ativacao_estado") == "sinais_compativeis"),
            "linha_de_base_janelas": len(engine.trip_baseline.windows) if engine.trip_baseline is not None else 0,
        },
        "desempenho": {
            "latencia_media_ms": round(statistics.fmean(latencies), 1),
            "latencia_p50_ms": round(_percentile(ordered, 0.5), 1),
            "latencia_p95_ms": round(_percentile(ordered, 0.95), 1),
            "latencia_max_ms": round(ordered[-1], 1),
            "quadros_processados_por_segundo": round(frames / processing_s, 1) if processing_s > 0 else None,
        },
        "grafico": plot,
        "avisos": warnings,
    }
    if phone is not None:
        summary["celular_s"] = {name: round(count / fps, 1) for name, count in Counter(info["celular"] for info in frame_info).items()}
    Path(f"{base}_resumo.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    general = summary["geral"]
    performance = summary["desempenho"]
    print(f"Pronto: {frames} quadros, rosto em {summary['quadros_com_rosto']:.0%}, "
          f"{general.get('piscadas', 0)} piscadas, duração mediana {general.get('duracao_mediana_ms', '?')} ms, "
          f"PERCLOS {general.get('perclos')}.")
    print(f"Desempenho: {performance['latencia_media_ms']} ms por quadro (p95 {performance['latencia_p95_ms']} ms).")
    print(f"Arquivos em {output}: {video.stem}_quadros.csv, _piscadas.csv, _janelas.csv, _eventos.csv, "
          f"{'_grafico.png, ' if plot else ''}_resumo.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
