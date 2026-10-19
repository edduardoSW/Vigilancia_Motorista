"""Remoção dos dados da demonstração antiga (spec 030, decisão 5).

Até 19/10/2026 o painel podia ser ativado em "demonstração", que gravava uma empresa, motoristas, veículos, caixas,
vínculos, termos e decisões fictícios. O painel não carrega mais nada disso. Ao abrir um banco com `meta.modo =
demonstracao`, a Ponte chama `remover()`: cópia `painel.db.antes-de-remover-demonstracao`, apaga só os registros da
demonstração, mantém contas, preferências, atividades e tudo que a pessoa cadastrou, registra a remoção e passa o modo
para `local`.

Os registros antigos nasceram com `uid` aleatório, então são reconhecidos pelo conjunto conhecido da demonstração:
motorista pela ref, matrícula e CNH (os três juntos); veículo pelo número e placa; caixa pelo código (sem dispositivo,
que só as caixas do arquivo da empresa têm); decisão pelo momento das viagens fictícias. Os nomes fictícios ficam só no
fixture dos testes (`tests/demonstracao_antiga.py`): aqui só o que identifica.

Módulo puro (sem pywebview). As consultas recebem uma função `todos(sql, parametros)`, para a mesma regra contar num
banco aberto só para leitura (`contar_demonstracao`).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from atividades import Atividades
from dados import Banco

DEMO_EMPRESA = "Viação Demonstração"
REGISTRADO_POR = "Demonstração"
MODO_ANTIGO, MODO_NOVO = "demonstracao", "local"
NOME_COPIA = "painel.db.antes-de-remover-demonstracao"
ACAO = "removeu os dados de demonstração"
QUEM = {"id": None, "nome": "RotaGuard Painel"}

# ref e matrícula; a CNH é cnh_demo(posição, de 1 a 5)
MOTORISTAS = (("m-01", "0412"), ("m-02", "0388"), ("m-03", "0291"), ("m-04", "0455"), ("m-05", "0467"))
# número e placa
VEICULOS = (("3302", "BRA2E19"), ("2258", "BRA3F27"), ("2240", "BRA1C84"), ("3310", "BRA5H02"), ("2251", "BRA4D66"),
            ("2263", "BRA7B31"), ("1187", "BRA8A12"))
CAIXAS = ("RG-0129", "RG-0139", "RG-0142", "RG-0133", "RG-0150", "RG-0147", "RG-0118", "RG-0155")
# Momentos das 3 viagens fictícias (as 8 que pediam verificação); decisão sobre eles não tem viagem de verdade.
MOMENTOS = ("v-1187-e-202", "v-1187-e-203", "v-2240-ep-1", "v-2240-e-102", "v-2240-e-104", "v-2240-e-109",
            "v-3310-e-302", "v-3310-e-303")

Consulta = Callable[..., list]


def cnh_demo(indice: int) -> str:
    """Número fictício e determinístico da demonstração antiga, válido pelo dígito verificador."""
    from cadastros import completar_cnh  # noqa: PLC0415 - cadastros não depende deste módulo

    base = 40_000_000 + indice * 7919
    while True:
        numero = completar_cnh(f"{base:09d}")
        if numero and len(set(numero)) > 1:
            return numero
        base += 1


def _marcas(quantidade: int) -> str:
    return ", ".join("?" for _ in range(quantidade))


def _ids(todos: Consulta, sql: str, parametros=()) -> list[int]:
    return [linha[0] for linha in todos(sql, tuple(parametros))]


def identificar(todos: Consulta) -> dict[str, list[int]]:
    """Ids de cada tabela que vieram da demonstração. Só lê."""
    motoristas = []
    for posicao, (ref, matricula) in enumerate(MOTORISTAS, 1):
        motoristas += _ids(todos, "SELECT id FROM motoristas WHERE ref = ? AND matricula = ? AND cnh_numero = ?",
                           (ref, matricula, cnh_demo(posicao)))
    veiculos = []
    for numero, placa in VEICULOS:
        veiculos += _ids(todos, "SELECT id FROM veiculos WHERE numero = ? AND placa = ?", (numero, placa))
    caixas = _ids(todos, f"SELECT id FROM caixas WHERE codigo IN ({_marcas(len(CAIXAS))}) AND dispositivo_id IS NULL",
                  CAIXAS)
    termos = _ids(todos, f"SELECT id FROM termos WHERE motorista_id IN ({_marcas(len(motoristas))})", motoristas) \
        if motoristas else []
    vinculos = _ids(todos, f"SELECT id FROM caixa_vinculos WHERE caixa_id IN ({_marcas(len(caixas))}) "
                           f"OR veiculo_id IN ({_marcas(len(veiculos))})", [*caixas, *veiculos]) \
        if caixas or veiculos else []
    decisoes = _ids(todos, f"SELECT id FROM decisoes WHERE momento_id IN ({_marcas(len(MOMENTOS))})", MOMENTOS)
    return {"motoristas": motoristas, "termos": termos, "veiculos": veiculos, "caixas": caixas,
            "caixa_vinculos": vinculos, "decisoes": decisoes}


def _nome_da_empresa(todos: Consulta) -> str | None:
    linhas = todos("SELECT valores FROM configuracoes WHERE secao = 'empresa'", ())
    if not linhas:
        return None
    try:
        return json.loads(linhas[0][0]).get("nome")
    except (ValueError, AttributeError):
        return None


def contar_demonstracao(todos: Consulta) -> dict:
    """Quantos registros sairiam e se o nome da empresa é o fictício, sem gravar nada (serve para banco só leitura)."""
    contagem = {tabela: len(ids) for tabela, ids in identificar(todos).items()}
    contagem["empresa"] = _nome_da_empresa(todos) == DEMO_EMPRESA
    return contagem


def precisa_remover(banco: Banco) -> bool:
    return banco.meta_ler("modo") == MODO_ANTIGO


def _caminho_da_copia(pasta: Path) -> Path:
    caminho = pasta / NOME_COPIA
    numero = 2
    while caminho.exists():  # uma cópia de uma tentativa que não terminou nunca é trocada
        caminho = pasta / f"{NOME_COPIA}-{numero}"
        numero += 1
    return caminho


def _gravar_copia(banco: Banco) -> Path:
    destino = _caminho_da_copia(banco.pasta)
    temporario = destino.with_name(destino.name + ".tmp")
    temporario.write_bytes(banco.serializar())
    os.replace(temporario, destino)
    return destino


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _detalhe(ids: dict[str, list[int]], empresa: str | None, copia: Path) -> str:
    partes = [_plural(len(ids["motoristas"]), "motorista", "motoristas"),
              _plural(len(ids["termos"]), "termo", "termos"),
              _plural(len(ids["veiculos"]), "veículo", "veículos"),
              _plural(len(ids["caixas"]), "caixa", "caixas"),
              _plural(len(ids["caixa_vinculos"]), "vínculo de caixa", "vínculos de caixa"),
              _plural(len(ids["decisoes"]), "decisão", "decisões")]
    texto = f"{', '.join(partes[:-1])} e {partes[-1]}"
    if empresa is not None:
        texto += f"; nome da empresa trocado pelo da central ({empresa})" if empresa else "; nome da empresa apagado"
    return f"{texto}; cópia em {copia.name}"


def _apagar(banco: Banco, tabela: str, ids: list[int]) -> None:
    for inicio in range(0, len(ids), 500):
        parte = ids[inicio:inicio + 500]
        banco.executar(f"DELETE FROM {tabela} WHERE id IN ({_marcas(len(parte))})", tuple(parte))


def remover(banco: Banco, atividades: Atividades, empresa_da_central: str | None = None) -> dict | None:
    """Faz a cópia e apaga a demonstração numa transação só. Devolve o que saiu, ou None se não era demonstração."""
    if not precisa_remover(banco):
        return None
    copia = _gravar_copia(banco)
    with banco.transacao():
        ids = identificar(banco.todos)
        # Termo nunca é apagado pelo painel (gatilho da spec 015); aqui sai só o termo de motorista fictício, e o
        # gatilho volta igual, na mesma transação.
        gatilho = banco.um("SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = 'termos_sem_apagar'")
        if gatilho is not None:
            banco.executar("DROP TRIGGER termos_sem_apagar")
        _apagar(banco, "termos", ids["termos"])
        if gatilho is not None:
            banco.executar(gatilho["sql"])
        _apagar(banco, "caixa_vinculos", ids["caixa_vinculos"])
        if ids["veiculos"]:  # caixa que não é da demonstração solta o veículo fictício antes dele sair
            banco.executar(f"UPDATE caixas SET veiculo_id = NULL, alterado_em = ? WHERE veiculo_id IN "
                           f"({_marcas(len(ids['veiculos']))})", (banco.agora(), *ids["veiculos"]))
        _apagar(banco, "caixas", ids["caixas"])
        _apagar(banco, "veiculos", ids["veiculos"])
        _apagar(banco, "motoristas", ids["motoristas"])
        _apagar(banco, "decisoes", ids["decisoes"])
        novo_nome = None
        linha = banco.um("SELECT valores FROM configuracoes WHERE secao = 'empresa'")
        if linha is not None:
            valores = json.loads(linha["valores"])
            if valores.get("nome") == DEMO_EMPRESA:
                novo_nome = (empresa_da_central or "").strip()
                valores["nome"] = novo_nome
                banco.atualizar("configuracoes", "secao", "empresa", {"valores": json.dumps(valores, ensure_ascii=False)})
        banco.meta_gravar("modo", MODO_NOVO)
        atividades.registrar(ACAO, QUEM, detalhe=_detalhe(ids, novo_nome, copia))
    return {"copia": str(copia), "empresa": novo_nome, **{tabela: len(lista) for tabela, lista in ids.items()}}
