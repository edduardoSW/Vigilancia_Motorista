// Junta classes condicionais (padrão da casa: sem clsx nem tailwind-merge).
export function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
