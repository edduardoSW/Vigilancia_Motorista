import { cn } from "@/lib/utils";

// Atalho de teclado mostrado discreto dentro de botões e da busca rápida: <Kbd>Ctrl N</Kbd>.
export function Kbd({ children, className }: { children: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)} aria-label={`Atalho ${children.replace(/\s+/g, " + ")}`}>
      {children.split(/\s+/).map((tecla) => (
        <kbd
          key={tecla}
          aria-hidden="true"
          className="kbd inline-grid h-[18px] min-w-[18px] place-items-center rounded-[4px] border border-current/25 px-1 font-sans text-[11px] font-semibold leading-none opacity-70"
        >
          {tecla}
        </kbd>
      ))}
    </span>
  );
}
