"""Avaliação: casamento de piscadas, métricas por classe, validação por sujeito e relatório do avaliar_dataset.

Só usa a biblioteca padrão:
    python tests/test_avaliacao.py
"""
import csv
import json
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "caixa"))
sys.path.insert(0, str(PROJECT / "ferramentas"))
import avaliar_dataset  # noqa: E402
import avaliar_piscadas  # noqa: E402
from vision.evaluation import (  # noqa: E402
    alert_latency,
    class_report,
    events_from_rows,
    false_alarms_per_hour,
    leave_one_subject_out,
    match_events,
    precision_recall_f1,
    read_csv_rows,
)

checks = 0
work = Path(tempfile.mkdtemp(prefix="drivesafe-avaliacao-"))


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


detected = [(1.0, 1.2), (3.0, 3.2), (5.0, 5.3)]
annotated = [(1.05, 1.25), (3.4, 3.6), (7.0, 7.2)]
pairs, extra, missed = match_events(detected, annotated, 0.25)
assert [(i, j) for i, j, _ in pairs] == [(0, 0)] and extra == [1, 2] and missed == [1, 2]
pairs, extra, missed = match_events(detected, annotated, 0.5)
assert [(i, j) for i, j, _ in pairs] == [(0, 0), (1, 1)] and extra == [2] and missed == [2]
pairs, extra, _ = match_events([(0.9, 1.0), (1.0, 1.1)], [(1.0, 1.1)], 0.25)
assert [(i, j) for i, j, _ in pairs] == [(1, 0)] and extra == [0]
ok("casamento de piscadas um para um, pelo par mais próximo e dentro da tolerância")

annotation = work / "anotacao.csv"
annotation.write_text("inicio_s;fim_s\n1,05;1,25\n", encoding="utf-8")
assert events_from_rows([{"inicio_s": "2.0", "fim_s": "2.2"}, {"tempo_s": "4.5"}]) == [(2.0, 2.2), (4.5, 4.5)]
assert events_from_rows([{"quadro_inicio": "30", "quadro_fim": "36"}], fps=30.0) == [(1.0, 1.2)]
annotation.write_text("inicio_s;fim_s\n1.05;1.25\n3.4;3.6\n7.0;7.2\n", encoding="utf-8")
assert read_csv_rows(annotation)[1] == {"inicio_s": "3.4", "fim_s": "3.6"}
detections = work / "video_piscadas.csv"
with open(detections, "w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["inicio_s", "fim_s", "duracao_ms", "completa"])
    writer.writerows([[1.0, 1.2, 200, 1], [3.0, 3.2, 200, 1], [5.0, 5.3, 300, 0]])
assert avaliar_piscadas.main([str(detections), str(annotation), "--tolerancia", "0.5"]) == 0
result = json.loads((work / "anotacao_comparacao.json").read_text(encoding="utf-8"))
assert (result["verdadeiros_positivos"], result["falsos_positivos"], result["falsos_negativos"]) == (2, 1, 1)
assert result["precisao"] == result["recall"] == 0.667
ok("avaliar_piscadas: lê CSV com ; ou , e grava precisão, recall e pares")

precision, recall, f1 = precision_recall_f1(8, 2, 2)
assert round(precision, 3) == round(recall, 3) == round(f1, 3) == 0.8
report = class_report(["alerta", "alerta", "sonolento", "sonolento"], ["alerta", "sonolento", "sonolento", "sonolento"],
                      ("alerta", "sonolento"))
assert report["sonolento"]["recall"] == 1.0 and report["sonolento"]["precisao"] == 0.667
assert report["matriz_confusao"]["alerta"] == {"alerta": 1, "sonolento": 1} and report["acuracia"] == 0.75
ok("precisão, recall, F1 por classe e matriz de confusão")

rows = [{"sujeito": s, "rotulo": "alerta"} for s in ("a", "b", "c") for _ in range(3)]
folds = list(leave_one_subject_out(rows))
assert len(folds) == 3 and all(not {r["sujeito"] for r in train} & {r["sujeito"] for r in test} for _, train, test in folds)
ok("validação deixando um sujeito de fora: treino e teste nunca compartilham motorista")

videos = [
    {"rotulo": "alerta", "segundos_avaliados": 1800.0, "alarmes_s": [100.0]},
    {"rotulo": "alerta", "segundos_avaliados": 1800.0, "alarmes_s": []},
    {"rotulo": "sonolento", "segundos_avaliados": 600.0, "alarmes_s": [120.0, 300.0]},
    {"rotulo": "sonolento", "segundos_avaliados": 600.0, "alarmes_s": [240.0]},
    {"rotulo": "sonolento", "segundos_avaliados": 600.0, "alarmes_s": []},
]
assert false_alarms_per_hour(videos) == 1.0
assert alert_latency(videos) == {"videos_sonolentos": 3, "com_alarme": 2, "latencia_mediana_s": 180.0, "latencia_max_s": 240.0}
ok("falsos alarmes por hora e latência do primeiro alarme")

manifest = work / "lista.csv"
manifest.write_text("video;sujeito;rotulo;calibracao\nv/0.mp4;01;0;sim\nv/5.mp4;01;5;\nv/10.mp4;01;10;\n", encoding="utf-8")
items = avaliar_dataset.read_manifest(manifest)
assert [(Path(i["video"]).name, i["rotulo"], i["calibracao"]) for i in items] == [("0.mp4", "alerta", True), ("10.mp4", "sonolento", False)]
assert Path(items[0]["video"]).resolve() == (work / "v" / "0.mp4").resolve()
assert len(avaliar_dataset.read_manifest(manifest, low_vigilance="sonolento")) == 3
ok("lista do dataset: rótulos 0/5/10 do UTA-RLDD, caminho relativo e vídeo de calibração")

cache = work / "extraido"
(cache / "janelas").mkdir(parents=True)
(cache / "videos").mkdir()
for subject in ("s1", "s2", "s3"):
    for label, levels in (("alerta", [0, 0, 0, 0, 1, 0]), ("sonolento", [2, 2, 0, 2, 3, 2])):
        name = f"{subject}__{label}"
        with open(cache / "janelas" / f"{name}.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["sujeito", "video", "rotulo", "tempo_s", "nivel_sonolencia",
                                                        "alarme", "perclos_60s", "z_perclos_60s"])
            writer.writeheader()
            for k, level in enumerate(levels):
                writer.writerow({"sujeito": subject, "video": f"{label}.mp4", "rotulo": label, "tempo_s": 60 + 10 * k,
                                 "nivel_sonolencia": level, "alarme": int(level >= 2),
                                 "perclos_60s": 0.02 + 0.05 * level, "z_perclos_60s": level * 1.5})
        (cache / "videos" / f"{name}.json").write_text(json.dumps(
            {"sujeito": subject, "rotulo": label, "segundos_avaliados": 120.0,
             "alarmes_s": [] if label == "alerta" else [65.0]}), encoding="utf-8")
report = avaliar_dataset.evaluate(cache, level_threshold=2, use_classifier=True)
rules = report["regras_do_dispositivo"]
assert report["janelas"] == 36 and report["sujeitos"] == 3
assert rules["sonolento"]["recall"] == 0.833 and rules["alerta"]["recall"] == 1.0
assert report["falsos_alarmes_por_hora"] == 0.0 and report["latencia_do_alerta"]["com_alarme"] == 3
model = report["classificador"]
if "erro" in model:
    print(f"-- classificador não testado ({model['erro']})")
else:
    assert model["validacao"].startswith("deixa um sujeito de fora") and model["sonolento"]["recall"] is not None
ok("avaliar_dataset: relatório por regras com recall por classe, falsos alarmes/hora e latência")

print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
