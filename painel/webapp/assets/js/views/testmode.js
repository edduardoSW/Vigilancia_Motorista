/* Modo teste (equipe). Nesta versão: explica como testar a câmera hoje e o que vem a seguir. */
import { IS_LOCAL } from "../config.js";
import { h, pageHeader, panel } from "../dom.js";

export default function testModeView(ctx) {
  ctx.title("Modo teste");
  return h("div", { class: "page" },
    pageHeader("Modo teste", {
      lead: IS_LOCAL
        ? "Teste com a câmera direto no navegador, sem servidor: em construção (ver PENDENCIAS.md)."
        : "Câmera deste computador, calibração e gráficos ao vivo pelo servidor: em construção nesta tela (ver PENDENCIAS.md).",
    }),
    panel({ title: "Como testar a detecção hoje", km: "01" },
      h("div", { class: "panel-body stack" },
        h("p", null, "A detecção completa (sonolência, celular, sinais de ativação) já funciona pelo Python, com a câmera do computador:"),
        h("pre", { class: "code" }, "python caixa\\run_monitor.py --camera 0\npython ferramentas\\analisar_video.py caminho\\do\\video.mp4 --celular"),
        h("p", { class: "muted" }, "Os resultados saem na janela da câmera e em planilhas (CSV) com piscadas, janelas e eventos."))),
    panel({ title: "Próxima etapa", km: "02" },
      h("div", { class: "panel-body" },
        h("ul", { class: "muted" },
          h("li", null, "Modo local: rodar o detector no navegador com MediaPipe Tasks Vision 1.0.1 (arquivos locais, sem internet) e mandar os eventos para a revisão."),
          h("li", null, "Modo servidor: iniciar/parar a câmera, vídeo ao vivo, marcação de piscadas com a barra de espaço e conferência de precisão (a API /api/test-mode já existe e tem testes).")))));
}
