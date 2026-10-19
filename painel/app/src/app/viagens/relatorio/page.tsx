import type { Metadata } from "next";
import { Suspense } from "react";
import { TripReport } from "@/components/trip/trip-report";

export const metadata: Metadata = { title: "Relatório da viagem · RotaGuard" };

// Relatório da viagem (spec 030): uma página só, que abre a viagem por ?id= (o export estático não tem página por
// registro). No export estático, useSearchParams precisa de Suspense em volta.
export default function TripReportPage() {
  return (
    <Suspense fallback={<section className="px-14 pt-[34px] font-titulo text-[30px] font-semibold">Relatório da viagem</section>}>
      <TripReport />
    </Suspense>
  );
}
