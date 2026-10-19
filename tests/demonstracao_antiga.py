"""Dados da demonstração antiga do painel (specs 012 e 014), que só existem nos testes desde a spec 030.

O painel não carrega mais nada fictício. Este módulo monta, numa pasta temporária, um banco igual ao que a ativação
"demonstração" gravava até 19/10/2026 (o painel do Matheus foi ativado assim em 15/09), para:
- testar a migração que apaga esses registros (`painel/desktop/demonstracao.py`, SDF-07 e SDF-08);
- os testes de regras que precisam de cadastros prontos (matrícula repetida, caixa trocada, termo antigo...).

Os identificadores (ref, matrícula, CNH, número, placa, código da caixa, momentos) vêm do módulo da migração: se um
lado mudar, o teste SDF-07 quebra. Os nomes e o resto ficam só aqui.
"""
from __future__ import annotations

import demonstracao
from atividades import Atividades
from configuracoes import Configuracoes
from contas import Contas

EMPRESA = demonstracao.DEMO_EMPRESA
# ref, nome, nome curto, matrícula, categoria, validade da CNH, data do termo (None: sem termo)
MOTORISTAS = (
    ("m-01", "Carlos Menezes", "Carlos M.", "0412", "D", "2028-03-31", "2026-09-02"),
    ("m-02", "Juliana Prado", "Juliana P.", "0388", "D", "2027-11-30", "2026-09-02"),
    ("m-03", "Rogério Lima", "Rogério L.", "0291", "E", "2026-09-26", "2026-09-03"),
    ("m-04", "Aline Costa", "Aline C.", "0455", "D", "2029-06-30", "2026-09-02"),
    ("m-05", "Marcos Teixeira", "Marcos T.", "0467", "D", "2030-01-15", None),
)
# número, tipo, transporta, placa, caixa, modelo
VEICULOS = (
    ("3302", "caminhao", "carga", "BRA2E19", "RG-0129", "Cavalo mecânico"),
    ("2258", "onibus", "passageiros", "BRA3F27", "RG-0139", "Rodoviário executivo"),
    ("2240", "onibus", "passageiros", "BRA1C84", "RG-0142", "Rodoviário 2 andares"),
    ("3310", "caminhao", "carga", "BRA5H02", "RG-0133", "Cavalo mecânico"),
    ("2251", "onibus", "passageiros", "BRA4D66", "RG-0150", "Rodoviário 2 andares"),
    ("2263", "onibus", "passageiros", "BRA7B31", "RG-0147", "Rodoviário leito"),
    ("1187", "onibus", "passageiros", "BRA8A12", "RG-0118", "Rodoviário executivo"),
)
CAIXA_LIVRE = "RG-0155"
DETALHE_RG_0129 = "A caixa esquentou demais na última viagem (passou de 70 °C). Vale conferir a instalação."
DECISOES = (("v-1187-e-202", "alarme_falso", False), ("v-1187-e-203", "confirmado", True))
DECISAO_POR, DECISAO_EM = "Marina (gestora)", "2026-09-14T06:58"


def cnh(indice: int) -> str:
    return demonstracao.cnh_demo(indice)


def carregar(banco) -> None:
    """O que `carregar_demonstracao` gravava: 5 motoristas (4 com termo), 7 veículos com caixa, 1 caixa livre e 2
    decisões, tudo com o mesmo jeito de antes (uid aleatório, "Demonstração" em quem registrou)."""
    with banco.transacao():
        for indice, (ref, nome, curto, matricula, categoria, validade, termo) in enumerate(MOTORISTAS, 1):
            motorista_id = banco.inserir("motoristas", {
                "ref": ref, "nome": nome, "nome_curto": curto, "matricula": matricula, "cpf": None, "telefone": None,
                "cnh_numero": cnh(indice), "cnh_categoria": categoria, "cnh_validade": validade, "situacao": "ativo",
                "observacoes": None})
            if termo:
                banco.inserir("termos", {"motorista_id": motorista_id, "assinado": 1, "data": termo, "versao": "1",
                                         "registrado_por": demonstracao.REGISTRADO_POR})
        for numero, tipo, transporta, placa, codigo, modelo in VEICULOS:
            veiculo_id = banco.inserir("veiculos", {"numero": numero, "placa": placa, "tipo": tipo,
                                                    "transporta": transporta, "modelo": modelo, "ano": None,
                                                    "situacao": "em_uso"})
            atencao = codigo == "RG-0129"
            caixa_id = banco.inserir("caixas", {"codigo": codigo, "veiculo_id": veiculo_id,
                                                "situacao": "atencao" if atencao else "ok",
                                                "detalhe": DETALHE_RG_0129 if atencao else None})
            banco.inserir("caixa_vinculos", {"caixa_id": caixa_id, "veiculo_id": veiculo_id, "de": banco.agora(),
                                             "ate": None, "por": demonstracao.REGISTRADO_POR})
        banco.inserir("caixas", {"codigo": CAIXA_LIVRE, "veiculo_id": None, "situacao": "ok", "detalhe": None})
        for momento_id, resultado, orientado in DECISOES:
            banco.inserir("decisoes", {"momento_id": momento_id, "resultado": resultado, "orientado": int(orientado),
                                       "por": DECISAO_POR, "funcao": "administrador", "em": DECISAO_EM, "ativa": 1})


def ativar_como_antes(banco, relogio, custo, admin: dict) -> dict:
    """Banco ativado em demonstração como até 19/10/2026: empresa fictícia, cadastros, administrador, `modo` e as
    linhas "ativou o painel" (detalhe "demonstração") e "entrou". Devolve a conta do administrador."""
    atividades = Atividades(banco)
    contas = Contas(banco, atividades, relogio, custo)
    with banco.transacao():
        Configuracoes(banco, atividades).iniciar(EMPRESA)
        carregar(banco)
        linha, _codigo = contas.criar_admin_inicial(admin)
        banco.meta_gravar("modo", "demonstracao")
        banco.meta_gravar("ativado", "1")
        atividades.registrar("ativou o painel", dict(linha), detalhe="demonstração")
    atividades.registrar("entrou", dict(linha))
    return dict(linha)


def carregar_na_ponte(ponte) -> None:
    """Para os testes de regras: painel já ativado (sem arquivo) recebe os cadastros fictícios de antes."""
    carregar(ponte._n().banco)  # noqa: SLF001 - fixture de teste
