# Mídia do RotaGuard · direção Boa chegada

A mídia desta versão foi gerada e está salva localmente. Nenhum crédito do Magnific foi utilizado.

| Peça | Original PNG | Publicado no site | Uso |
|---|---|---|---|
| Ônibus interestadual na serra | originais/onibus-rodoviario.png | /midia/rotaguard/onibus-rodoviario.webp | Hero e segmento de passageiros |
| Caixa conceitual | originais/caixa-conceito.png | /midia/rotaguard/caixa-conceito.webp | Hero, produto e acesso |
| Carreta na rodovia | originais/caminhao-rodovia.png | /midia/rotaguard/caminhao-rodovia.webp | Segmento de logística |
| Motorista de rodoviário | originais/motorista-rodoviario.png | /midia/rotaguard/motorista-rodoviario.webp | Cabine e compromisso com motorista |
| Coleta na garagem | originais/chegada-garagem.png | /midia/rotaguard/chegada-garagem.webp | Etapa da chegada |
| Giro e montagem 3D | video-local/estudo-engenharia.blend | /midia/rotaguard/estudo-engenharia.mp4 | Estudo local de engenharia |

## Prompts atuais

[05-direcao-boa-chegada.md](05-direcao-boa-chegada.md) contém os briefs de produção dos cinco assets e do vídeo.

Os arquivos 00 a 04 são briefs históricos extensos da direção anterior. Não são a fonte da mídia implementada nesta versão. Não reutilizar prescrições de mapas, Atos, tons de concreto ou ônibus urbano desses arquivos. Estão preservados para não perder pedidos e ideias ainda não produzidos.

## Origem e tratamento

Ferramenta de geração de imagens disponível nesta sessão; cinco imagens 1536 × 1024. A imagem de coleta usa a caixa gerada como referência para continuidade visual. Originais preservados em `originais/`; WebP em qualidade 85 com sharp, servidos com tamanhos responsivos por next/image.

As fotos são ilustrações de IA. A caixa fotográfica é uma proposta de design, enquanto o vídeo Blender é um estudo de componentes com geometria própria. Não representam hardware final validado. Os créditos públicos descrevem essas limitações.

## Reprodução do vídeo

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b -P '../../produto/3d/render_site.py' -- './video-local' video
ffmpeg -framerate 8 -i './video-local/frame-%04d.png' -vf 'fps=24' -c:v libx264 -crf 22 -pix_fmt yuv420p -movflags +faststart '../../../site/public/midia/rotaguard/estudo-engenharia.mp4'
```

Vídeo sem áudio e sem reprodução automática. Frames intermediários são arquivos de trabalho, não assets públicos.

## Em aberto

As tomadas em vídeo dentro das cabines de caminhão e ônibus descritas no briefing anterior ainda não foram geradas. A versão entregue usa fotos dessas situações e o vídeo 3D local. Não houve geração paga nem armazenamento no Magnific.
