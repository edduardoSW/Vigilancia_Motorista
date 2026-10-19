"""Tela do RotaGuard Teste (spec 023): servidor local só em 127.0.0.1, estado ao vivo, resumo e a página em web/.

A página é HTML, CSS e JS sem build e sem nada da internet. A janela é do pywebview (WebView2 no Windows); sem ele,
abre no navegador padrão. O monitoramento roda numa thread deste processo (run_monitor.Monitoramento).
"""
from __future__ import annotations

from pathlib import Path

PASTA_WEB = Path(__file__).resolve().parent / "web"
