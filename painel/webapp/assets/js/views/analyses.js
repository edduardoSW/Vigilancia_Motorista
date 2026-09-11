/* Análise de vídeo (equipe). Nesta versão: caminho pelo Python enquanto a tela não fica pronta. */
import { h, pageHeader, panel } from "../dom.js";

export default function analysesView(ctx) {
  ctx.title("Análise de vídeo");
  return h("div", { class: "page" },
    pageHeader("Análise de vídeo", { lead: "Enviar um vídeo e ver piscadas, PERCLOS e eventos: tela em construção (ver PENDENCIAS.md)." }),
    panel({ title: "Enquanto isso", km: "01" },
      h("div", { class: "panel-body stack" },
        h("pre", { class: "code" }, "python ferramentas\\analisar_video.py viagem.mp4 --celular"),
        h("p", { class: "muted" }, "Gera _quadros.csv, _piscadas.csv, _janelas.csv, _eventos.csv, _grafico.png e _resumo.json ao lado do vídeo."))));
}
