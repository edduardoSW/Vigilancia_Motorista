"""Política do servidor aplicada no dispositivo: motorista vinculado, consentimento do perfil e sinais de ativação.

Só usa a biblioteca padrão (não precisa de câmera, OpenCV nem MediaPipe):
    python tests/test_politica_remota.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))
from vision.calibration import Calibrator  # noqa: E402
from vision.drowsiness import DrowsinessMonitor  # noqa: E402
from vision.engine import DriverStateEngine  # noqa: E402
from vision.remote_policy import RemotePolicy, driver_key_for  # noqa: E402

checks = 0
work = Path(tempfile.mkdtemp(prefix="drivesafe-politica-"))


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def server_policy(driver_id, profile_consent, activation_mode):
    return {"driver_id": driver_id, "profile_consent": profile_consent, "activation_mode": activation_mode,
            "status_interval_s": 15}


try:
    assert driver_key_for(7, "qualquer") == "motorista-7"
    assert driver_key_for(None, "Caminhão ABC/1234") == "Caminh_o_ABC_1234"
    assert driver_key_for(None, "///") == "padrao"
    ok("chave do motorista: id do servidor, ou nome seguro para virar arquivo")

    calibrations = []

    def new_calibrator():
        calibrator = Calibrator(min_seconds=120, max_seconds=120, target_blinks=999)
        calibrations.append(calibrator)
        return calibrator

    drowsiness = DrowsinessMonitor(calibrator=new_calibrator())
    engine = DriverStateEngine(drowsiness, activation_mode="local", background_baseline=False)
    policy = RemotePolicy(engine, work, fallback_key="padrao", calibrator_factory=new_calibrator)

    assert policy.apply_pending() is False
    policy.submit(server_policy(1, True, "enviar"))
    assert policy.apply_pending() is True
    assert drowsiness.profile_path == work / "perfis" / "motorista-1.json"
    assert engine.baseline_store is not None and engine.activation_mode == "enviar" and engine.fusion.share_activation
    assert len(calibrations) == 1, "a primeira política não deve recalibrar"
    ok("com consentimento: perfil e linha de base do motorista 1 guardados; sinais de ativação podem ser enviados")

    policy.submit(server_policy(1, True, "enviar"))
    assert policy.apply_pending() is False
    ok("a mesma política de novo (heartbeat a cada 15 s) não mexe em nada")

    profile_file = work / "perfis" / "motorista-1.json"
    baseline_file = work / "linhas_de_base" / "motorista-1.json"
    for path in (profile_file, baseline_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    policy.submit(server_policy(1, False, "local"))
    assert policy.apply_pending() is True
    assert not profile_file.exists() and not baseline_file.exists()
    assert drowsiness.profile_path is None and engine.baseline_store is None
    assert engine.activation_mode == "local" and not engine.fusion.share_activation
    ok("consentimento revogado no app: perfil e linha de base apagados do dispositivo; sinais só locais")

    policy.submit(server_policy(2, False, "desligado"))
    assert policy.apply_pending() is True
    assert len(calibrations) == 2 and drowsiness.calibrator is calibrations[-1]
    assert engine.activation is None and engine.activation_mode == "desligado"
    ok("motorista trocado no servidor: nova calibração; empresa com sinais desligados desliga o monitor de ativação")

    policy.submit(server_policy(2, False, "valor-estranho"))
    assert policy.apply_pending() is True and engine.activation_mode == "local"
    ok("modo desconhecido vindo da rede não para o monitoramento: fica local")

    print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
finally:
    shutil.rmtree(work, ignore_errors=True)
