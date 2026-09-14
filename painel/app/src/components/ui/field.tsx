// Campo de formulário: rótulo, "opcional", dica e erro em frase simples. Use as classes .input e .select no controle,
// com aria-invalid quando houver erro.
export function Field({
  label,
  optional,
  hint,
  error,
  htmlFor,
  children,
  className,
}: {
  label: React.ReactNode;
  optional?: boolean;
  hint?: React.ReactNode;
  error?: string | null;
  htmlFor?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className ?? "mb-4"}>
      <label htmlFor={htmlFor} className="mb-1.5 flex items-baseline gap-1.5 text-[13.5px] font-semibold">
        {label}
        {optional && <span className="text-[12.5px] font-normal text-grafite">opcional</span>}
      </label>
      {children}
      {error ? (
        <p role="alert" id={htmlFor ? `${htmlFor}-erro` : undefined} className="anim-enter mt-1.5 text-[13px] text-alarme">
          {error}
        </p>
      ) : (
        hint && <p className="mt-1.5 text-[12.5px] text-grafite">{hint}</p>
      )}
    </div>
  );
}
