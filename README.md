# DriveSafe AI

Sistema inteligente de monitoramento de motoristas para detectar distrações e uso de celular durante a direção.

## Funcionalidades

- 👁️ **Detecção em Tempo Real**: Monitoramento contínuo do motorista usando visão computacional
- 📱 **Detecção de Celular**: Identifica quando o motorista está usando o celular
- 👀 **Análise de Atenção**: Detecta quando o motorista olha para baixo ou fecha os olhos
- 🔊 **Alarme Sonoro**: Emite alertas sonoros no veículo quando há risco
- 📊 **Dashboard Administrativo**: Painel web para acompanhamento em tempo real
- 📈 **Histórico de Alertas**: Registro completo de todas as ocorrências

## Tecnologias Utilizadas

- **Python 3.8+**
- **OpenCV**: Captura e processamento de vídeo
- **MediaPipe**: Detecção de rosto, olhos e mãos
- **YOLO**: Detecção de objetos (celular)
- **FastAPI**: Backend API
- **SQLite**: Banco de dados
- **HTML/CSS/JavaScript**: Dashboard web

## Instalação

1. Clone o repositório e entre no diretório:

```bash
cd Cam_Motorista
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Como Usar

### 1. Iniciar o servidor web (Dashboard)

```bash
uvicorn backend.main:app --reload
```

Acesse o dashboard em: `http://localhost:8000`

### 2. Iniciar o monitoramento do motorista

Em outro terminal:

```bash
python run_monitor.py --driver 1 --vehicle 1 --camera 0
```

Parâmetros:
- `--driver`: ID do motorista (padrão: 1)
- `--vehicle`: ID do veículo (padrão: 1)
- `--camera`: ID da câmera (padrão: 0)
- `--api-url`: URL da API (padrão: http://localhost:8000)

## Estrutura do Projeto

```
Cam_Motorista/
├── backend/
│   ├── __init__.py
│   ├── database.py          # Modelos do banco de dados
│   ├── main.py              # API FastAPI
│   └── schemas.py           # Schemas Pydantic
├── vision/
│   ├── __init__.py
│   └── driver_monitor.py    # Módulo de visão computacional
├── dashboard/
│   ├── index.html           # Página principal
│   └── static/
│       ├── css/
│       │   └── style.css    # Estilos
│       └── js/
│           └── app.js       # JavaScript do dashboard
├── data/                    # Banco de dados SQLite
├── requirements.txt         # Dependências
├── run_monitor.py           # Script de monitoramento
└── README.md
```

## Tipos de Alertas

| Tipo | Descrição | Nível de Risco |
|------|-----------|----------------|
| `looking_down` | Olhando para baixo | 1 |
| `eyes_closed` | Olhos fechados | 2 |
| `both_hands_off_wheel` | Ambas as mãos fora do volante | 2 |
| `phone_usage` | Uso de celular | 3 |

## Configurações

As configurações podem ser ajustadas no arquivo `vision/driver_monitor.py`:

- `alert_threshold`: Tempo mínimo (segundos) para disparar alerta (padrão: 3.0)
- `look_down_threshold`: Limiar para detecção de olhar para baixo (padrão: 0.4)
- `phone_detection_confidence`: Confiança mínima para detecção de celular (padrão: 0.7)

## Segurança e Privacidade

- As imagens são processadas localmente
- Nenhuma imagem é armazenada permanentemente
- Apenas metadados dos alertas são salvos
- Sistema de consentimento transparente

## Contribuição

Este projeto está em desenvolvimento contínuo. Para contribuir, entre em contato.

## Licença

MIT License
