"""Configuração do servidor central, lida de variáveis de ambiente."""
import os

APP_VERSION = "0.4.0"

# Raiz do repositório (este arquivo fica em servidor/backend/). Os dados continuam em data/ na raiz.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
CAIXA_DIR = os.path.join(BASE_DIR, "caixa")  # vision/, usado pelo modo teste
FERRAMENTAS_DIR = os.path.join(BASE_DIR, "ferramentas")  # analisar_video.py, usado pelo modo teste

# SQLite por padrão. Para Postgres: postgresql+psycopg://usuario:senha@host:5432/drivesafe
DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(DATA_DIR, "drivesafe.db")

# Fuso usado para exibir datas e calcular "hoje". No banco tudo fica em UTC.
TIMEZONE = os.environ.get("DRIVESAFE_TIMEZONE", "America/Sao_Paulo")

# Sem contato há mais tempo que isso, o dispositivo aparece como offline.
DEVICE_ONLINE_SECONDS = int(os.environ.get("DRIVESAFE_DEVICE_ONLINE_SECONDS", "180"))

# De quanto em quanto tempo o dispositivo manda o estado ao vivo (risco, calibração, celular).
DEVICE_STATUS_INTERVAL_S = int(os.environ.get("DRIVESAFE_DEVICE_STATUS_INTERVAL_S", "15"))

# App instalável (PWA) servido pelo próprio servidor.
WEBAPP_DIR = os.path.join(BASE_DIR, "painel", "webapp")

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

# ---------- central (spec 026): o script envia, o painel executável busca ----------

# Trechos de vídeo recebidos dos aparelhos: trechos/<uid da empresa>/<uid do trecho>.<formato>, fora de pasta pública.
CLIPS_DIR = os.environ.get("DRIVESAFE_TRECHOS_DIR", "").strip() or os.path.join(DATA_DIR, "trechos")
CLIP_MAX_BYTES = int(os.environ.get("DRIVESAFE_TRECHO_MAX_MB", "25")) * 1024 * 1024
CLIPS_PER_SESSION = 20
# Teto por aparelho em 24 h, mesmo trocando de sessão: um token vazado não enche o disco da VPS.
CLIPS_PER_DEVICE_DAY = int(os.environ.get("DRIVESAFE_TRECHOS_POR_DIA", "100"))
# Prazo de guarda padrão dos trechos (manage.py apagar-trechos-antigos).
CLIP_RETENTION_DAYS = 30

# Segredo do servidor para guardar os códigos de pareamento só como HMAC. Sem a variável, fica num arquivo da pasta de
# dados (criado na primeira vez, só o dono lê). Nunca vai para o banco: banco vazado não revela código.
SECRET = os.environ.get("DRIVESAFE_SEGREDO_CENTRAL", "").strip()
SECRET_FILE = os.environ.get("DRIVESAFE_SEGREDO_ARQUIVO", "").strip() or os.path.join(DATA_DIR, "segredo-central.key")

PAIRING_CODE_MINUTES = 30
# Trocas de código erradas por IP antes de responder 429.
PAIRING_MAX_FAILURES = 10
PAIRING_WINDOW_S = 60
# Códigos ainda válidos por empresa (evita gerar milhares).
PAIRING_MAX_ACTIVE = 20

# "Testando agora": último sinal de vida há menos disto e sessão aberta.
TESTING_WINDOW_S = 30

# Sessão do painel executável (token no cabeçalho): vale 30 dias desde o último uso.
PANEL_SESSION_DAYS = 30
