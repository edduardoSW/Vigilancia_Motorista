import { Glyph } from "@/components/ui/glyph";
import { cn } from "@/lib/utils";

// Botão de salvar que mostra "Salvando…" e depois "Salvo".
export function SaveButton({
  state,
  children,
  className,
  type = "submit",
  disabled,
  ...rest
}: { state: "idle" | "saving" | "saved" } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      aria-busy={state === "saving"}
      disabled={disabled || state === "saving"}
      className={cn("btn btn-primary save-button", className)}
      {...rest}
    >
      {state === "saving" ? (
        <span key="saving" className="anim-fade">Salvando…</span>
      ) : state === "saved" ? (
        <span key="saved" className="anim-fade inline-flex items-center gap-1.5">
          <Glyph name="check" size={16} stroke={2} />
          Salvo
        </span>
      ) : (
        <span key="idle">{children}</span>
      )}
    </button>
  );
}
