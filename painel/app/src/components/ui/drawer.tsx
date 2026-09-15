"use client";

import { Dialog } from "@/components/ui/dialog";

// O painel lateral virou janela no centro (spec 019, MOD-01: "os modais devem abrir centralizado na tela com um blur no
// fundo"). O nome ficou para não mudar as telas que já usavam; por dentro é a mesma janela do Dialog, um pouco mais larga.
export function Drawer({ width = 600, ...props }: Parameters<typeof Dialog>[0]) {
  return <Dialog width={width} {...props} />;
}
