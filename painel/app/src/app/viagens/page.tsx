import type { Metadata } from "next";
import { TripsScreen } from "@/components/trips/trips-screen";

export const metadata: Metadata = { title: "Viagens · RotaGuard" };

// Viagens (spec 014): lista com "Para verificar", "Revisadas" e "Todas"; cada linha abre o relatório da viagem.
export default function TripsPage() {
  return <TripsScreen />;
}
