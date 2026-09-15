"use client";

import { createPortal } from "react-dom";

// Painéis laterais e diálogos abrem na camada da janela (#camada-sobreposta, no auth-gate), fora da tela aberta.
// A animação de entrada da tela usa transform, e transform prende o `position: fixed` dentro dela: na captura de
// 15/09/2026 o painel do motorista terminava na altura da lista. A camada fica dentro do app, então o `inert` da tela
// bloqueada também vale para o que estiver aberto nela.
export function Camada({ children }: { children: React.ReactNode }) {
  if (typeof document === "undefined") return null;
  return createPortal(children, document.getElementById("camada-sobreposta") ?? document.body);
}
