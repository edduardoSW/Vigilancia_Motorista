"""Configuração do servidor central, lida de variáveis de ambiente."""
import os

APP_VERSION = "0.3.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# SQLite por padrão. Para Postgres: postgresql+psycopg://usuario:senha@host:5432/drivesafe
DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(DATA_DIR, "drivesafe.db")

# Fuso usado para exibir datas e calcular "hoje". No banco tudo fica em UTC.
TIMEZONE = os.environ.get("DRIVESAFE_TIMEZONE", "America/Sao_Paulo")

# Sem contato há mais tempo que isso, o dispositivo aparece como offline.
DEVICE_ONLINE_SECONDS = int(os.environ.get("DRIVESAFE_DEVICE_ONLINE_SECONDS", "180"))

# De quanto em quanto tempo o dispositivo manda o estado ao vivo (risco, calibração, celular).
DEVICE_STATUS_INTERVAL_S = int(os.environ.get("DRIVESAFE_DEVICE_STATUS_INTERVAL_S", "15"))

# App instalável (PWA) servido pelo próprio servidor.
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp")

# Não há cadastro aberto: quem quer acesso fala com a equipe pelo celular, e a equipe cria o login.
# Ex.: DRIVESAFE_CONTATO_CELULAR="(11) 98765-4321". Sem valor, a tela de login só diz para procurar a equipe.
CONTACT_PHONE = os.environ.get("DRIVESAFE_CONTATO_CELULAR", "").strip()
CONTACT_WHATSAPP = os.environ.get("DRIVESAFE_CONTATO_WHATSAPP", "sim").strip().lower() not in ("0", "nao", "não", "false")

# Modo teste: vídeos enviados pelo app para análise e seus resultados.
ANALYSES_DIR = os.path.join(DATA_DIR, "analises")
MAX_UPLOAD_BYTES = int(os.environ.get("DRIVESAFE_MAX_UPLOAD_MB", "4096")) * 1024 * 1024
# Endereço que o modo teste usa para falar com o próprio servidor (padrão: 127.0.0.1 na porta em uso).
INTERNAL_URL = os.environ.get("DRIVESAFE_URL_INTERNA", "").strip().rstrip("/")
# O vídeo enviado é apagado depois da análise (fica só a planilha de medidas), a menos que isto esteja ligado.
KEEP_ANALYSIS_VIDEOS = os.environ.get("DRIVESAFE_MANTER_VIDEOS", "").strip().lower() in ("1", "true", "sim")
