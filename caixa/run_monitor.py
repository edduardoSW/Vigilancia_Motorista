"""Agente de monitoramento do motorista: Raspberry Pi, Linux, macOS e Windows.

Exemplo:
  python run_monitor.py --server-url http://192.168.0.10:8000

Todas as opções aceitam variáveis de ambiente DRIVESAFE_* (recomendado para o token).
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import signal
import socket
import sys
from pathlib import Path

# Reduz o log interno do MediaPipe / TensorFlow Lite; precisa vir antes de importá-los.
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

logger = logging.getLogger("drivesafe")

ACTIVATION_LOG = {
    "desligado": "Sinais de ativação atípica desligados.",
    "local": "Sinais de ativação atípica: calculados só neste dispositivo; entram no nível de risco e não vão ao servidor.",
    "enviar": "Sinais de ativação atípica: enviados ao servidor. São dado pessoal sensível (LGPD, art. 11): "
              "exigem base legal e consentimento do motorista.",
}


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return default if value is None or not value.strip() else value.strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name)
    return default if value is None else value.lower() in ("1", "true", "sim", "yes", "on")


def display_available() -> bool:
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "padrao"


def parse_args(argv=None):
    from vision.engine import ACTIVATION_MODES

    parser = argparse.ArgumentParser(description="DriveSafe AI: monitoramento de sonolência e distração do motorista.")
    parser.add_argument("--server-url", "--api-url", dest="server_url",
                        default=env("DRIVESAFE_SERVER_URL", "http://localhost:8000"),
                        help="endereço do servidor central (DRIVESAFE_SERVER_URL)")
    parser.add_argument("--token", default=env("DRIVESAFE_DEVICE_TOKEN", ""),
                        help="token do dispositivo; prefira a variável DRIVESAFE_DEVICE_TOKEN")
    parser.add_argument("--camera", default=env("DRIVESAFE_CAMERA", "0"),
                        help="índice da webcam (0), /dev/video0, arquivo de vídeo, URL ou 'picamera2'")
    parser.add_argument("--width", type=int, default=int(env("DRIVESAFE_WIDTH", "640")))
    parser.add_argument("--height", type=int, default=int(env("DRIVESAFE_HEIGHT", "480")))
    parser.add_argument("--camera-ir", choices=("auto", "sim", "nao"), default=env("DRIVESAFE_CAMERA_IR", "auto"),
                        help="câmera infravermelha: libera a medida da pupila (DRIVESAFE_CAMERA_IR)")
    parser.add_argument("--data-dir", default=env("DRIVESAFE_DATA_DIR", str(Path.home() / ".drivesafe")),
                        help="fila de eventos, perfis de calibração e sirene (DRIVESAFE_DATA_DIR)")
    parser.add_argument("--driver-key", default=env("DRIVESAFE_DRIVER_KEY", "padrao"),
                        help="nome do perfil de calibração; use um por motorista (DRIVESAFE_DRIVER_KEY)")
    parser.add_argument("--consentimento-perfil", action="store_true", default=env_bool("DRIVESAFE_CONSENTIMENTO_PERFIL"),
                        help="o motorista consentiu: guarda perfil de calibração e linha de base entre viagens "
                             "(DRIVESAFE_CONSENTIMENTO_PERFIL)")
    parser.add_argument("--calibration-min", type=float, default=float(env("DRIVESAFE_CALIBRATION_MIN_S", "300")),
                        help="segundos mínimos de calibração com o rosto visível (padrão 300 = 5 min)")
    parser.add_argument("--calibration-max", type=float, default=float(env("DRIVESAFE_CALIBRATION_MAX_S", "600")),
                        help="segundos máximos de calibração (padrão 600 = 10 min)")
    parser.add_argument("--no-calibration", action="store_true", default=env_bool("DRIVESAFE_NO_CALIBRATION"),
                        help="não recalibra ao iniciar; usa o perfil salvo do motorista (precisa de consentimento)")
    parser.add_argument("--sinais-ativacao", choices=ACTIVATION_MODES, default=env("DRIVESAFE_SINAIS_ATIVACAO", "local"),
                        help="sinais compatíveis com ativação atípica: desligado, local ou enviar (DRIVESAFE_SINAIS_ATIVACAO)")
    phone = parser.add_mutually_exclusive_group()
    phone.add_argument("--celular", dest="celular", action="store_true", default=env_bool("DRIVESAFE_CELULAR", True),
                       help="detecta uso de celular (padrão; DRIVESAFE_CELULAR)")
    phone.add_argument("--sem-celular", dest="celular", action="store_false", help="desliga a detecção de celular")
    parser.add_argument("--telemetria", default=env("DRIVESAFE_TELEMETRIA_ARQUIVO"),
                        help="arquivo JSON com a velocidade do veículo, escrito por outro processo (DRIVESAFE_TELEMETRIA_ARQUIVO)")
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--window", dest="window", action="store_true", default=None, help="mostra a janela da câmera")
    window.add_argument("--no-window", dest="window", action="store_false", help="roda sem janela (Raspberry Pi sem tela)")
    buzzer = env("DRIVESAFE_BUZZER_PIN")
    parser.add_argument("--buzzer-pin", type=int, default=int(buzzer) if buzzer else None,
                        help="pino GPIO (BCM) de um buzzer no Raspberry Pi, no lugar do alto-falante")
    parser.add_argument("--mute", action="store_true", default=env_bool("DRIVESAFE_MUTE"), help="desliga o som")
    parser.add_argument("--log-level", default=env("DRIVESAFE_LOG_LEVEL", "INFO"))
    return parser.parse_args(argv)


def resolve_window(args) -> bool:
    if args.window is not None:
        return args.window
    choice = env("DRIVESAFE_WINDOW", "auto").lower()
    return display_available() if choice == "auto" else choice in ("1", "true", "sim", "yes", "on")


def create_phone_monitor():
    from vision.phone import PhoneDetector, PhoneMonitor

    try:
        return PhoneMonitor(PhoneDetector())
    except (RuntimeError, ValueError) as exc:
        logger.warning("Detecção de celular desligada: %s", exc)
        return None


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from vision import __version__
    from vision.alarm import Alarm
    from vision.baseline import BaselineStore
    from vision.calibration import Calibrator
    from vision.camera import open_camera
    from vision.context import DrivingContext
    from vision.driver_monitor import DriverMonitor
    from vision.drowsiness import DrowsinessMonitor
    from vision.engine import DriverStateEngine
    from vision.event_queue import EventStore
    from vision.eyes import DriverProfile
    from vision.face import create_face_analyzer
    from vision.sync import ServerClient, SyncWorker
    from vision.visibility import EyeVisibility

    data_dir = Path(args.data_dir).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("DriveSafe AI %s em %s. Dados locais em %s.", __version__, socket.gethostname(), data_dir)
    if not args.token:
        logger.warning("Sem token do dispositivo: os eventos ficam na fila local até configurar DRIVESAFE_DEVICE_TOKEN.")

    store = EventStore(data_dir / "eventos.db")
    analyzer = sync = engine = None
    try:
        alarm = Alarm(data_dir / "sirene.wav", buzzer_pin=args.buzzer_pin, muted=args.mute)
        # DRIVESAFE_FACE_BACKEND: auto (MediaPipe e, se faltar, YuNet), mediapipe ou yunet.
        analyzer = create_face_analyzer(backend=env("DRIVESAFE_FACE_BACKEND", "auto").lower(),
                                        use_classifier=not env_bool("DRIVESAFE_NO_EYE_CLASSIFIER"),
                                        infrared=args.camera_ir)

        key = safe_key(args.driver_key)
        profile_path = data_dir / "perfis" / f"{key}.json"
        profile = None
        if args.consentimento_perfil and analyzer.supports_calibration:
            profile = DriverProfile.load(profile_path)
            if profile is not None:
                logger.info("Perfil de calibração '%s' carregado (criado em %s).", args.driver_key, profile.created_at)
        elif profile_path.exists():
            logger.info("Existe perfil salvo de '%s', mas sem consentimento (DRIVESAFE_CONSENTIMENTO_PERFIL) ele não é usado.",
                        args.driver_key)
        logger.info("Perfil e linha de base entre viagens: %s.",
                    "guardados neste dispositivo (com consentimento)" if args.consentimento_perfil
                    else "não guardados; a calibração vale só para esta viagem")

        def new_calibrator():
            if not analyzer.supports_calibration:
                return None
            return Calibrator(min_seconds=args.calibration_min, max_seconds=args.calibration_max)

        if args.no_calibration and profile is None and analyzer.supports_calibration:
            logger.warning("--no-calibration precisa de perfil salvo com consentimento para '%s': calibrando mesmo assim.",
                           args.driver_key)
        calibrator = None if (args.no_calibration and profile is not None) else new_calibrator()
        if calibrator is not None:
            def as_text(seconds):
                return f"{seconds / 60:.0f} min" if seconds >= 60 else f"{seconds:.0f} s"

            logger.info("Calibrando por %s a %s com o rosto visível. Microssono já é detectado nesse período.",
                        as_text(args.calibration_min), as_text(args.calibration_max))

        drowsiness = DrowsinessMonitor(profile=profile, calibrator=calibrator,
                                       profile_path=profile_path if args.consentimento_perfil else None)
        baseline_store = BaselineStore(data_dir / "linhas_de_base" / f"{key}.json") if args.consentimento_perfil else None
        engine = DriverStateEngine(
            drowsiness,
            activation_mode=args.sinais_ativacao,
            baseline_store=baseline_store,
            context=DrivingContext(args.telemetria),
            visibility=EyeVisibility(detect_sunglasses=env_bool("DRIVESAFE_DETECTAR_OCULOS_ESCUROS", True)),
            phone=create_phone_monitor() if args.celular else None,
        )
        logger.info(ACTIVATION_LOG[args.sinais_ativacao])
        monitor = DriverMonitor(analyzer, engine, alarm, store, calibrator_factory=new_calibrator)

        policy = None
        if args.token:
            from vision.remote_policy import RemotePolicy

            # Com servidor, motorista vinculado, consentimento e modo dos sinais de ativação vêm do app.
            policy = RemotePolicy(engine, data_dir, fallback_key=args.driver_key, calibrator_factory=new_calibrator)
            monitor.policy = policy
            logger.info("Consentimentos e motorista vinculado passam a seguir o cadastro no app do servidor.")
        sync = SyncWorker(store, ServerClient(args.server_url, args.token),
                          status_provider=lambda: {"camera_ok": monitor.camera_ok, "status": monitor.live_status()},
                          heartbeat_interval=float(env("DRIVESAFE_HEARTBEAT_S", "15")),
                          policy_handler=policy.submit if policy is not None else None)
        sync.start()
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, lambda *_: monitor.stop())

        camera = open_camera(args.camera, args.width, args.height)
        monitor.run(camera, resolve_window(args))
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário.")
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    finally:
        if sync is not None:
            sync.stop()
            sync.join(timeout=15)
        if engine is not None:
            engine.close()
        if analyzer is not None:
            analyzer.close()
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
