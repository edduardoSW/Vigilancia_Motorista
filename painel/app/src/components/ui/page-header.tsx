import Link from "next/link";
import { Glyph } from "@/components/ui/glyph";

// Cabeçalho de tela: título, resumo com número real ("5 ativos · 1 CNH vence em 12 dias"), ações e o link discreto do guia.
export function PageHeader({
  title,
  summary,
  actions,
  guide,
}: {
  title: React.ReactNode;
  summary?: React.ReactNode;
  actions?: React.ReactNode;
  guide?: { capitulo: string; passo?: string };
}) {
  const href = guide ? `/guia/?capitulo=${encodeURIComponent(guide.capitulo)}${guide.passo ? `&passo=${encodeURIComponent(guide.passo)}` : ""}` : null;
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 pb-6">
      <div className="min-w-0">
        <h1 className="font-titulo text-[30px] font-semibold leading-[1.15] tracking-[-0.01em]">{title}</h1>
        {summary && <p className="mt-1.5 text-[14.5px] tabular-nums text-grafite">{summary}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {href && (
          <Link
            href={href}
            className="no-print mr-1 inline-flex h-9 items-center gap-1.5 rounded-[8px] px-2 text-[13px] font-medium text-grafite transition-colors hover:bg-lateral hover:text-tinta"
          >
            <Glyph name="book" size={16} />
            Guia
          </Link>
        )}
        {actions}
      </div>
    </header>
  );
}
