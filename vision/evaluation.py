"""Funções de avaliação sem dependências: leitura de CSV, casamento de piscadas, métricas por classe,
validação deixando um sujeito de fora, falsos alarmes por hora e latência do alerta."""
from __future__ import annotations

import bisect
import csv
import statistics
from pathlib import Path


def read_csv_rows(path) -> list[dict]:
    """Lê CSV separado por vírgula ou ponto e vírgula; nomes de coluna em minúsculas."""
    lines = [line for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not lines:
        return []
    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    return [{(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(lines, delimiter=delimiter)]


def to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def events_from_rows(rows, fps: float | None = None) -> list[tuple[float, float]]:
    """(início, fim) em segundos. Aceita inicio_s/fim_s, tempo_s, ou quadro / quadro_inicio e quadro_fim com fps."""
    events = []
    for row in rows:
        start, end = to_float(row.get("inicio_s")), to_float(row.get("fim_s"))
        if start is None and to_float(row.get("tempo_s")) is not None:
            start = end = to_float(row["tempo_s"])
        if start is None and fps:
            first = to_float(row.get("quadro_inicio", row.get("quadro")))
            last = to_float(row.get("quadro_fim", row.get("quadro")))
            if first is not None:
                start, end = first / fps, (last if last is not None else first) / fps
        if start is not None:
            events.append((start, end if end is not None else start))
    return sorted(events)


def match_events(detected, annotated, tolerance: float):
    """Casa detecções e anotações pelo centro, uma para uma, do par mais próximo ao mais distante.
    Retorna (pares (i, j, diferença em s), sobras detectadas, sobras anotadas)."""
    detected_centers = [(start + end) / 2.0 for start, end in detected]
    annotated_centers = [(start + end) / 2.0 for start, end in annotated]
    order = sorted(range(len(detected_centers)), key=detected_centers.__getitem__)
    ordered = [detected_centers[i] for i in order]
    candidates = []
    for j, center in enumerate(annotated_centers):
        low = bisect.bisect_left(ordered, center - tolerance)
        high = bisect.bisect_right(ordered, center + tolerance)
        candidates.extend((abs(detected_centers[order[k]] - center), order[k], j) for k in range(low, high))
    candidates.sort()
    used_detected, used_annotated, pairs = set(), set(), []
    for _, i, j in candidates:
        if i in used_detected or j in used_annotated:
            continue
        used_detected.add(i)
        used_annotated.add(j)
        pairs.append((i, j, detected_centers[i] - annotated_centers[j]))
    return (sorted(pairs), [i for i in range(len(detected)) if i not in used_detected],
            [j for j in range(len(annotated)) if j not in used_annotated])


def precision_recall_f1(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if precision is None or recall is None:
        return precision, recall, None
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _rounded(value, digits=3):
    return None if value is None else round(value, digits)


def class_report(y_true, y_pred, classes) -> dict:
    report = {}
    for label in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision, recall, f1 = precision_recall_f1(tp, fp, fn)
        report[label] = {"precisao": _rounded(precision), "recall": _rounded(recall), "f1": _rounded(f1), "suporte": tp + fn}
    report["matriz_confusao"] = {t: {p: sum(1 for a, b in zip(y_true, y_pred) if a == t and b == p) for p in classes}
                                 for t in classes}
    report["acuracia"] = _rounded(sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)) if y_true else None
    return report


def leave_one_subject_out(rows, key: str = "sujeito"):
    """Uma rodada por sujeito: ele fica só no teste e nunca no treino."""
    for subject in sorted({row[key] for row in rows}):
        yield subject, [row for row in rows if row[key] != subject], [row for row in rows if row[key] == subject]


def false_alarms_per_hour(videos) -> float | None:
    alert = [video for video in videos if video["rotulo"] == "alerta"]
    hours = sum(video["segundos_avaliados"] for video in alert) / 3600.0
    return round(sum(len(video["alarmes_s"]) for video in alert) / hours, 2) if hours > 0 else None


def alert_latency(videos) -> dict:
    drowsy = [video for video in videos if video["rotulo"] == "sonolento"]
    firsts = [video["alarmes_s"][0] for video in drowsy if video["alarmes_s"]]
    return {
        "videos_sonolentos": len(drowsy),
        "com_alarme": len(firsts),
        "latencia_mediana_s": round(statistics.median(firsts), 1) if firsts else None,
        "latencia_max_s": round(max(firsts), 1) if firsts else None,
    }
