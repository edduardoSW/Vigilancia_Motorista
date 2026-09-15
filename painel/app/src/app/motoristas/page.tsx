import type { Metadata } from "next";
import { Suspense } from "react";
import { DriversScreen } from "@/components/drivers/drivers-screen";

export const metadata: Metadata = { title: "Motoristas · RotaGuard" };

// Motoristas (spec 015): a tela conversa com o Python pela `bridge`, por isso fica num componente de cliente.
// A busca rápida abre um motorista por ?abrir=; no export estático, useSearchParams precisa de Suspense em volta.
export default function DriversPage() {
  return (
    <Suspense fallback={<section className="px-14 pt-[34px] font-titulo text-[30px] font-semibold">Motoristas</section>}>
      <DriversScreen />
    </Suspense>
  );
}
