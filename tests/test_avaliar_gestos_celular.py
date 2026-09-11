"""Etapa 2: avaliar_gestos.py e avaliar_celular.py com arquivos sintéticos, e as medidas do celular por quadro.

Só usa a biblioteca padrão:
    python tests/test_avaliar_gestos_celular.py
"""
import csv
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "caixa"))
sys.path.insert(0, str(PROJECT / "ferramentas"))
import analisar_video  # noqa: E402
import avaliar_celular  # noqa: E402
import avaliar_gestos  # noqa: E402

checks = 0
work = Path(tempfile.mkdtemp(prefix="drivesafe-etapa2-"))


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def write_csv(path, header, rows, delimiter=","):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(rows)
    return path


detected = write_csv(work / "video_gestos.csv", ["inicio_s", "fim_s", "gesto", "lado", "inversoes", "fracao_olho_encoberto"], [
    [10.0, 11.5, "olhos_esfregados", "direito", 4, 0.0],  # acerto
    [30.0, 32.0, "mao_no_rosto", "", "", ""],  # acerto
    [50.0, 51.5, "mao_no_rosto", "esquerdo", "", 0.5],  # anotado como esfregar: gesto trocado
    [70.2, 71.0, "mao_no_rosto", "", "", ""],  # em cima de ajustar os óculos: falso positivo
    [90.0, 91.0, "olhos_esfregados", "direito", 2, 0.0],  # sem anotação: falso positivo
])
annotation = write_csv(work / "anotacao_gestos.csv", ["inicio_s", "fim_s", "gesto"], [
    [10.2, 11.6, "olhos_esfregados"], [30.3, 32.1, "mao_no_rosto"], [50.1, 51.2, "olhos_esfregados"],
    [70.0, 71.0, "ajustar_oculos"], [110.0, 112.0, "olhos_esfregados"],
], delimiter=";")
assert avaliar_gestos.main([str(detected), str(annotation)]) == 0
result = json.loads((work / "anotacao_gestos_comparacao.json").read_text(encoding="utf-8"))
rub, touch, any_gesture = result["olhos_esfregados"], result["mao_no_rosto"], result["qualquer_gesto"]
assert (rub["acertos"], rub["falsos_positivos"], rub["perdidos"]) == (1, 1, 2), rub
assert (touch["acertos"], touch["falsos_positivos"], touch["perdidos"]) == (1, 2, 0), touch
assert (any_gesture["acertos"], any_gesture["falsos_positivos"], any_gesture["perdidos"]) == (3, 2, 1), any_gesture
assert result["anotado_x_detectado"]["olhos_esfregados"] == {"olhos_esfregados": 1, "mao_no_rosto": 1}
assert result["falsos_positivos_por_negativo"] == {"ajustar_oculos": 1, "sem_anotacao": 1}
pairs = list(csv.reader((work / "anotacao_gestos_pares.csv").open(encoding="utf-8")))
assert [row[0] for row in pairs[1:]].count("par") == 3 and [row[0] for row in pairs[1:]].count("perdido") == 1
ok("gestos: acertos por gesto e sem olhar o nome, gesto trocado, falso positivo em cima do negativo anotado")

assert avaliar_gestos.main([str(detected), str(annotation), "--inicio", "40"]) == 0
cut = json.loads((work / "anotacao_gestos_comparacao.json").read_text(encoding="utf-8"))["qualquer_gesto"]
assert (cut["acertos"], cut["falsos_positivos"], cut["perdidos"]) == (1, 2, 1), cut
empty = write_csv(work / "vazia.csv", ["inicio_s", "fim_s", "gesto"], [])
assert avaliar_gestos.main([str(detected), str(empty)]) == 1
ok("gestos: recorte por tempo e anotação vazia recusada")

results = work / "resultados"
results.mkdir()
header = ["tempo_s", "rosto", "celular", "celular_confianca", "celular_largura_rosto", "celular_altura_rosto",
          "celular_proporcao"]
write_csv(results / "galaxy_quadros.csv", header, [
    [f"{i / 10:.3f}", 1, "sem_celular", "", "", "", ""] if i < 50 else
    [f"{i / 10:.3f}", 1, "celular_na_mao", 0.6, 0.5, 0.9, 1.8] for i in range(100)])
write_csv(results / "iphone_quadros.csv", header, [
    [f"{i / 10:.3f}", 1, "celular_na_mao" if i < 25 else "celular_no_ouvido", 0.4, 0.35, 0.7, 2.0] for i in range(50)])
phones = write_csv(work / "anotacao_celular.csv", ["arquivo", "aparelho", "inicio_s", "fim_s", "estado", "situacao"], [
    ["gravacoes/galaxy.mp4", "galaxy_a54", 0.0, 4.95, "sem_celular", ""],
    ["gravacoes/galaxy.mp4", "galaxy_a54", 5.0, 9.95, "celular_na_mao", "peito"],
    ["iphone.mp4", "iphone_mini", 0.0, 4.95, "celular_no_ouvido", "ouvido"],
    ["sumiu.mp4", "dobravel", 0.0, 3.0, "celular_na_mao", "peito"],
], delimiter=";")
assert avaliar_celular.main([str(phones), "--resultados", str(results)]) == 0
report = json.loads((work / "anotacao_celular_celular.json").read_text(encoding="utf-8"))
devices = {entry["aparelho"]: entry for entry in report["aparelhos"]}
assert devices["galaxy_a54"]["quadros"] == 100 and devices["galaxy_a54"]["fracao_com_celular_detectado"] == 0.5
assert devices["galaxy_a54"]["confianca_mediana"] == 0.6 and devices["galaxy_a54"]["largura_rosto_mediana"] == 0.5
assert devices["iphone_mini"]["quadros"] == 50 and devices["iphone_mini"]["largura_rosto_mediana"] == 0.35
states = report["estados"]
assert states["celular_no_ouvido"]["recall"] == 0.5 and states["celular_na_mao"]["precisao"] == 0.667, states
assert states["matriz_confusao"]["celular_no_ouvido"]["celular_na_mao"] == 25
assert report["faixa_sugerida_em_larguras_de_rosto"]["largura_rosto"] == {"p5": 0.35, "p95": 0.5, "quadros": 100}
assert report["acerto_por_situacao"]["ouvido"] == {"quadros": 50, "acuracia": 0.5}
assert len(report["arquivos_faltando"]) == 1 and report["arquivos_faltando"][0].endswith("sumiu_quadros.csv")
assert (work / "anotacao_celular_aparelhos.csv").is_file()
ok("celular: tabela por aparelho, matriz de confusão por quadro, faixa sugerida de tamanho e arquivo faltando")

bad = write_csv(work / "ruim.csv", ["arquivo", "aparelho", "inicio_s", "fim_s", "estado"], [["a.mp4", "x", 0, 1, "no_bolso"]])
assert avaliar_celular.main([str(bad), "--resultados", str(results)]) == 1
old = results / "antigo_quadros.csv"
write_csv(old, ["tempo_s", "rosto", "celular"], [["0.000", 1, "sem_celular"]])
old_annotation = write_csv(work / "antiga.csv", ["arquivo", "aparelho", "inicio_s", "fim_s", "estado"],
                           [["antigo.mp4", "x", 0, 1, "sem_celular"]])
assert avaliar_celular.main([str(old_annotation), "--resultados", str(results)]) == 1
ok("celular: estado anotado inválido e _quadros.csv sem as medidas do celular são recusados")

face = SimpleNamespace(face_found=True, face_box=(270.0, 120.0, 370.0, 250.0))
state = SimpleNamespace(phone=SimpleNamespace(phone_score=0.7, boxes=[(300.0, 330.0, 340.0, 400.0)]), metrics=face)
assert analisar_video._phone_measures(state) == {"celular_confianca": 0.7, "celular_largura_rosto": 0.4,
                                                 "celular_altura_rosto": 0.7, "celular_proporcao": 1.75}
lost = SimpleNamespace(phone=state.phone, metrics=SimpleNamespace(face_found=False, face_box=None))
assert analisar_video._phone_measures(lost)["celular_largura_rosto"] is None
assert analisar_video._phone_measures(lost)["celular_confianca"] == 0.7
ok("analisar_video: caixa do celular em larguras de rosto; sem rosto, só a confiança")

print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
