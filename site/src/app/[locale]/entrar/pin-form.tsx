"use client";

import { useActionState } from "react";
import { entrar, type EstadoEntrar } from "./actions";

export function PinForm({
  locale,
  rotuloPin,
  rotuloBotao,
  erros,
}: {
  locale: string;
  rotuloPin: string;
  rotuloBotao: string;
  erros: { pin: string; bloqueio: string; config: string };
}) {
  const [estado, acao, enviando] = useActionState<EstadoEntrar, FormData>(entrar, { erro: null });

  return (
    <form action={acao} className="mt-10 grid max-w-sm gap-4">
      <input type="hidden" name="locale" value={locale} />
      <label htmlFor="pin" className="etiqueta">
        {rotuloPin}
      </label>
      <input
        id="pin"
        name="pin"
        type="password"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]*"
        minLength={4}
        maxLength={12}
        required
        aria-invalid={estado.erro ? "true" : undefined}
        aria-describedby="pin-erro"
        className="numero min-h-14 border border-asfalto bg-papel px-4 text-[1.6rem] tracking-[0.3em] focus:outline-2 focus:outline-asfalto"
      />
      <p id="pin-erro" aria-live="polite" className="min-h-6 text-alarme">
        {estado.erro ? erros[estado.erro] : ""}
      </p>
      <button type="submit" disabled={enviando} className="btn btn-primario">
        {rotuloBotao}
      </button>
    </form>
  );
}
