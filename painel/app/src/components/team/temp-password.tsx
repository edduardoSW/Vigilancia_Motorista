"use client";

import { useState } from "react";

// Senha temporária mostrada uma vez só (spec 014, decisão 8).
export function TempPassword({ nome, usuario, senha }: { nome: string; usuario: string; senha: string }) {
  const [copiada, setCopiada] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(senha);
      setCopiada(true);
    } catch {
      setCopiada(false);
    }
  }

  return (
    <div className="anim-enter">
      <p className="text-[14px] text-grafite">
        Acesso de <b className="font-semibold text-tinta">{nome}</b>, usuário <b className="font-semibold text-tinta">{usuario}</b>.
      </p>
      <div className="mt-3 flex items-center gap-3 rounded-[10px] border border-fio bg-white px-4 py-3">
        <span className="min-w-0 flex-1 select-all break-all font-titulo text-[20px] font-semibold tracking-[0.02em]">{senha}</span>
        <button type="button" className="btn btn-small" onClick={copiar}>
          {copiada ? "Copiada" : "Copiar"}
        </button>
      </div>
      <p className="mt-3 text-[14px]">Passe esta senha para a pessoa. Ela vai trocar no primeiro acesso.</p>
      <p className="mt-1 text-[13px] text-grafite">Depois de fechar, a senha não aparece de novo.</p>
    </div>
  );
}
