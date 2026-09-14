import type { Metadata } from "next";
import { VehiclesScreen } from "@/components/vehicles/vehicles-screen";

export const metadata: Metadata = { title: "Veículos e caixas · RotaGuard" };

// Veículos e caixas (spec 015): cadastro, edição e troca de caixa pela `bridge`, num componente de cliente.
export default function VehiclesPage() {
  return <VehiclesScreen />;
}
