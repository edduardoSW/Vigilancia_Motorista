import { cn } from "@/lib/utils";

// Ver antes de editar (spec 019, INT-01): os dados em seções curtas, com rótulo à esquerda e valor à direita, sem
// formulário. Usado nas janelas do motorista e do veículo. Cor só quando pede ação (alarm).

export function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-fio pt-5 first:border-t-0 first:pt-0">
      <h3 className="font-titulo text-[15px] font-semibold">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function DetailList({ children }: { children: React.ReactNode }) {
  return <dl className="grid grid-cols-[150px_minmax(0,1fr)] gap-x-4 gap-y-2 text-[14px]">{children}</dl>;
}

export function DetailRow({
  label,
  children,
  alarm = false,
  muted = false,
}: {
  label: string;
  children: React.ReactNode;
  /** Vermelho só quando pede ação (CNH vencendo, caixa com problema). */
  alarm?: boolean;
  /** Valor que não foi informado ("Não informado"). */
  muted?: boolean;
}) {
  return (
    <>
      <dt className="text-grafite">{label}</dt>
      <dd className={cn("min-w-0 break-words", alarm && "font-semibold text-alarme", muted && "text-grafite")}>{children}</dd>
    </>
  );
}
