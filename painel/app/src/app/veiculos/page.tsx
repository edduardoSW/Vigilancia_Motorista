import type { Metadata } from "next";
import { Suspense } from "react";
import { VehiclesScreen } from "@/components/vehicles/vehicles-screen";

export const metadata: Metadata = { title: "Veículos e caixas · RotaGuard" };

// Veículos e caixas (spec 015): cadastro, edição e troca de caixa pela `bridge`, num componente de cliente.
// A busca rápida abre um veículo por ?abrir=; no export estático, useSearchParams precisa de Suspense em volta.
export default function VehiclesPage() {
  return (
    <Suspense fallback={<section className="px-14 pt-[34px] font-titulo text-[30px] font-semibold">Veículos e caixas</section>}>
      <VehiclesScreen />
    </Suspense>
  );
}
