import type { Metadata } from "next";
import { Suspense } from "react";
import { LiveScreen } from "@/components/live/live-screen";

const NA_WEB = process.env.NEXT_PUBLIC_PAINEL_TRANSPORTE === "servidor";

export const metadata: Metadata = { title: NA_WEB ? "Teste com a câmera · RotaGuard" : "Teste neste computador · RotaGuard" };

// Spec 018: o script da caixa rodando neste computador aparece aqui sozinho, com os eventos que ele registrar.
// Spec 025: o teste com a câmera do aparelho, no navegador (na web, é o único). A aba vem de ?aba=; no export estático,
// useSearchParams precisa de Suspense em volta.
export default function LivePage() {
  return (
    <Suspense fallback={<section className="px-14 pt-[34px] font-titulo text-[30px] font-semibold">{NA_WEB ? "Teste com a câmera" : "Teste neste computador"}</section>}>
      <LiveScreen />
    </Suspense>
  );
}
