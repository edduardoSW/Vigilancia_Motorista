import { cn } from "@/lib/utils";

// Escolha única com título e explicação curta (função da pessoa, prazo de guarda...). Sem pílula, sem ícone.
export function Choice({
  name,
  value,
  checked,
  onChange,
  title,
  description,
  disabled,
}: {
  name: string;
  value: string;
  checked: boolean;
  onChange: (value: string) => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-[10px] border px-3.5 py-3 transition-colors",
        checked ? "border-verde bg-escolha" : "border-fio bg-superficie hover:border-verde/30",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        disabled={disabled}
        onChange={() => onChange(value)}
        className="mt-[3px] size-4 accent-verde"
      />
      <span className="min-w-0">
        <span className="block text-[14px] font-semibold">{title}</span>
        {description && <span className="mt-0.5 block text-[13px] text-grafite">{description}</span>}
      </span>
    </label>
  );
}
