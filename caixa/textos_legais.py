"""Privacidade, LGPD e termos de uso do RotaGuard Teste (spec 010, decisão 13; cardio e resumos: specs 022 e 023).

Ficam numa seção da tela de início, para consulta, sem aceite obrigatório para usar (pedido do Matheus em 14/09/2026).
O texto descreve o que o app faz de verdade: se mudar o que ele grava ou envia, atualize aqui e nos testes APT-21.
Rascunho a revisar por advogado antes de oferecer a clientes.
"""
from __future__ import annotations

from pathlib import Path

VERSAO_TEXTOS = "19/10/2026"
RESPONSAVEL = "RotaGuard"
# Canal para dúvidas de privacidade (e-mail ou telefone). Vazio enquanto não existir: o texto diz "em preparação".
CONTATO_PRIVACIDADE = ""


def contato(canal: str = CONTATO_PRIVACIDADE) -> str:
    if canal.strip():
        return canal.strip()
    return "canal de privacidade em preparação; até lá, fale com quem enviou o app para você"


def politica_de_privacidade(pasta: Path) -> str:
    return f"""POLÍTICA DE PRIVACIDADE · RotaGuard Teste
Versão de {VERSAO_TEXTOS}

1. O que é este app
O RotaGuard Teste roda neste computador o mesmo programa da caixa RotaGuard, para testar a detecção de sinais de sono e \
de uso de celular com a câmera do computador ou com um vídeo que você escolher. É um protótipo em validação e não é \
diagnóstico médico nem exame toxicológico.

2. O que o app usa
• Imagens da câmera ou do vídeo escolhido. Cada imagem é analisada na memória do computador para medir pontos do rosto \
(abertura dos olhos, piscadas, boca e posição da cabeça), as mãos e a presença de celular. Com câmera infravermelha, \
também a pupila.
• Sinais compatíveis com ativação atípica (a partir das piscadas e do olhar), calculados só neste computador.
• Frequência cardíaca estimada pela câmera, a partir de variações mínimas da cor da pele da testa e das bochechas, \
e a respiração estimada junto. A estimativa é feita só neste computador, aparece na tela e não é gravada nem \
enviada (a única exceção é o resumo que você decidir salvar, item 3). Não é medição médica nem diagnóstico. \
Por ser dado de saúde, recebe o cuidado dos dados pessoais sensíveis (art. 5º, II, e art. 11). Pode ser \
desligada nas opções do teste, em "Frequência cardíaca".
• As imagens não são gravadas em arquivo nem enviadas, a não ser nos trechos de vídeo do item 4, quando você conecta \
o app a uma empresa. A tela do teste só mostra a imagem ao vivo, com a malha de \
pontos do rosto. Ela é uma página servida só para este computador (endereço 127.0.0.1, com uma chave nova a \
cada abertura): nenhum outro aparelho da rede vê a câmera.
• O app não faz reconhecimento facial: não identifica quem aparece, não pede nome, e-mail ou documento e não usa \
localização.

3. O que fica gravado neste computador
Na pasta de dados do app:
{pasta}
• eventos.db: eventos do teste (tipo, nível, duração e horário) e medidas em números, como piscadas por minuto, tempo \
de olho fechado, confiança da detecção de celular e a calibração do olho feita no teste;
• registro-teste.log: registro técnico (início e fim, pasta de dados, câmera usada, desempenho e eventos);
• sirene_info.wav, sirene_distracao.wav, sirene_sonolencia.wav e sirene_critico.wav: os sons do alarme, um para cada tipo de aviso;
• em_execucao.json, só enquanto o teste está aberto: número do processo, horário de início, câmera usada e último \
sinal, para o painel da empresa neste computador reconhecer que o teste está aberto. É apagado quando o teste termina;
• resumos, só quando você clica em "Salvar resumo" no fim do teste: duração, eventos por tipo, PERCLOS médio, \
piscadas por minuto e a frequência cardíaca média, mínima e máxima do teste, em JSON e CSV;
• só com o app conectado a uma empresa (item 4): central.json (endereço da central, nome da empresa e a chave \
deste computador), a pasta central (fila do que ainda vai ser enviado) e a pasta trechos (os trechos de vídeo).
A calibração não é reaproveitada: cada teste calibra de novo, e nenhum perfil do rosto fica guardado.

4. O que sai deste computador
Sem conexão com uma empresa, nada: o app de teste não precisa de internet e não envia imagens, medidas, eventos ou \
registro para a {RESPONSAVEL} nem para terceiros.
Se você usar "Conectar à empresa" com um código gerado no painel de uma empresa, e enquanto "Enviar para a empresa" \
estiver ligado, vão para a central da {RESPONSAVEL}, para essa empresa ver no painel dela:
• os eventos do teste e o resumo de cada teste (duração, eventos por tipo, PERCLOS médio e piscadas por minuto);
• trechos de vídeo de cerca de 16 s (8 s antes e 8 s depois) dos momentos de alerta, com o rosto, a malha de pontos \
e a hora;
• o sinal de que o teste está aberto, com o nível de risco do momento.
A frequência cardíaca nunca sai deste computador. Tudo é gravado aqui antes de sair: sem internet, fica na fila e vai \
depois. Desligar o envio ou "Desconectar" para na hora; o que já foi enviado fica com a empresa, que define por \
quanto tempo guarda (o padrão da central é 30 dias para os trechos).

5. Por quanto tempo os dados ficam
Até você apagar. Use o botão "Apagar dados deste computador", nesta seção, ou apague a pasta acima.

6. Outras pessoas na imagem
Se outra pessoa aparecer na câmera ou no vídeo, avise-a antes do teste. Não use o app para observar alguém sem que a \
pessoa saiba.

7. Mudanças
Quando este texto mudar, a data da versão no topo muda junto.

8. Contato
{contato()}.
"""


def lgpd() -> str:
    return f"""LGPD · Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018)
Versão de {VERSAO_TEXTOS}

1. Quais dados pessoais estão envolvidos
A imagem do rosto e as medidas tiradas dela são dados pessoais de quem aparece na câmera. Por serem medidas do rosto, \
o app trata esses dados com o cuidado exigido para dados pessoais sensíveis (art. 5º, II, e art. 11), mesmo sem \
usá-los para identificar ninguém.

2. Onde e por quem os dados são tratados
Sem conexão com uma empresa, todo o tratamento acontece neste computador, sob o controle de quem usa o app, e a \
{RESPONSAVEL} não recebe esses dados. Conectado a uma empresa com um código, a empresa passa a ser a controladora do \
que é enviado (eventos, resumos e trechos de vídeo) e a {RESPONSAVEL} guarda esses dados por ela, na central. A \
frequência cardíaca nunca é enviada.

3. Princípios seguidos (art. 6º)
• Finalidade: medir sinais de sono e de uso de celular durante o teste e, se ligada, estimar a frequência cardíaca.
• Necessidade: só as medidas necessárias; as imagens não são gravadas.
• Transparência: esta seção explica o que é usado e o que fica gravado.
• Segurança e prevenção: tudo fica no computador; só sai o que está no item 4 da Privacidade, com o app conectado a \
uma empresa, por conexão protegida (HTTPS).
• Livre acesso: a pasta de dados abre pelo próprio app.

4. Seus direitos (art. 18)
• Confirmar e acessar os dados: botão "Abrir pasta de dados".
• Eliminar os dados: botão "Apagar dados deste computador".
• Como a {RESPONSAVEL} não recebe os dados do teste, esses pedidos são atendidos no próprio computador. Dúvidas: \
{contato()}.
• Você também pode procurar a Autoridade Nacional de Proteção de Dados (ANPD).

5. Uso por empresas
Se uma empresa usar o RotaGuard para acompanhar motoristas, ela passa a ser a controladora dos dados (art. 5º, VI): \
precisa de base legal, informar os motoristas de forma clara e cuidar dos dados sensíveis (art. 11). A caixa RotaGuard \
para frotas terá política e termos próprios. Este app de teste não deve ser usado para monitorar empregados.

6. Crianças e adolescentes
O app não é destinado a crianças e adolescentes.
"""


def termos_de_uso() -> str:
    return f"""TERMOS DE USO · RotaGuard Teste
Versão de {VERSAO_TEXTOS}

1. Sobre estes termos
Estes termos valem para o uso do RotaGuard Teste. Não é preciso aceitar nada para começar a usar: eles ficam nesta \
seção para consulta.

2. O que o app é
Um protótipo gratuito para testar e avaliar a detecção do RotaGuard. A {RESPONSAVEL} concede uma licença de uso \
pessoal, gratuita, não exclusiva e intransferível, que pode ser encerrada a qualquer momento.

3. Limites do teste
• Não é dispositivo médico, exame toxicológico nem equipamento de segurança certificado.
• Os alertas podem falhar: pode haver alerta falso ou sinal não detectado.
• A frequência cardíaca é estimativa pela câmera, não é medida médica.
• Não substitui descanso, pausas, atenção ao volante nem as regras de trânsito e de jornada do motorista.
• Não use o app de teste como proteção enquanto dirige.

4. Uso permitido
• Use em computador próprio ou com autorização de quem é responsável por ele.
• Não use para observar pessoas sem que elas saibam, nem para tomar decisões sobre empregados com base no teste.
• Não retire os avisos de licença de terceiros e não distribua versões modificadas com o nome RotaGuard.

5. Propriedade
O nome, a marca e o programa RotaGuard pertencem aos seus titulares. Componentes de terceiros seguem as próprias \
licenças (aba Licenças).

6. Garantia e responsabilidade
O app é oferecido como está, sem garantia de funcionamento contínuo ou de resultado. Na medida permitida pela lei \
brasileira, a {RESPONSAVEL} não responde por danos decorrentes do uso do teste, de decisões tomadas com base nos \
alertas ou de falhas do computador. Nada nestes termos afasta direitos garantidos pelo Código de Defesa do Consumidor, \
quando ele se aplicar.

7. Privacidade
O tratamento de dados está descrito nas abas Privacidade e LGPD.

8. Mudanças e lei aplicável
Estes termos podem mudar; a data da versão fica no topo. Aplica-se a legislação brasileira.

9. Contato
{contato()}.
"""


def licencas(avisos_de_terceiros: str = "") -> str:
    detalhes = avisos_de_terceiros.strip() or "Arquivo THIRD_PARTY_NOTICES.md não encontrado neste pacote."
    return f"""LICENÇAS DE TERCEIROS · RotaGuard Teste

O app inclui estes componentes, cada um com a própria licença:
• MediaPipe (Google): Apache 2.0, com os modelos Face Landmarker, Hand Landmarker e EfficientDet-Lite0 (Apache 2.0).
• OpenCV (opencv-contrib-python): Apache 2.0, com a FFmpeg (LGPL 2.1) para ler arquivos de vídeo. Detector de rosto \
YuNet: MIT.
• OCEC, classificador de olho aberto ou fechado (Katsuya Hyodo): MIT.
• NumPy: BSD-3-Clause. matplotlib: licença própria (estilo PSF). sounddevice: MIT. absl-py e flatbuffers: Apache 2.0.
• Janela da tela do teste: pywebview (BSD-3-Clause), que usa o WebView2 do Windows (componente do sistema, da \
Microsoft), com bottle (MIT), proxy_tools (MIT), typing_extensions (PSF), pythonnet (MIT), clr_loader (MIT), \
cffi (MIT-0) e pycparser (BSD-3-Clause).
• Python: licença PSF.
• Empacotado com PyInstaller (GPL 2.0 com exceção que permite distribuir programas gerados com ele).

Os textos completos das licenças das bibliotecas ficam dentro da pasta do app, em _internal, nas pastas terminadas em \
.dist-info. A da OpenCV traz o LICENSE-3RD-PARTY.txt, que inclui a FFmpeg.

Origem, versões, restrições de uso dos fabricantes e textos das licenças:

{detalhes}
"""


def secoes(pasta: Path, avisos_de_terceiros: str = "") -> list[tuple[str, str]]:
    return [
        ("Privacidade", politica_de_privacidade(pasta)),
        ("LGPD", lgpd()),
        ("Termos de uso", termos_de_uso()),
        ("Licenças", licencas(avisos_de_terceiros)),
    ]
