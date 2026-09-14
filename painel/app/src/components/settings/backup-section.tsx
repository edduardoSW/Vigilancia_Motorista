"use client";

import { useState } from "react";
import { bridge } from "@/lib/bridge";
import { Field } from "@/components/ui/field";
import { SaveButton } from "@/components/ui/save-button";
import { useToast } from "@/components/ui/toast";
import { Section, type SaveState } from "./section";

const tamanho = (bytes: number) =>
  bytes >= 1_048_576 ? `${(bytes / 1_048_576).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

// Cópia de segurança (spec 016, decisão 5): um arquivo só, que só abre com a senha escolhida agora.
export function BackupSection() {
  const { toast } = useToast();
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [state, setState] = useState<SaveState>("idle");
  const [erro, setErro] = useState<{ texto: string; campo?: string } | null>(null);
  const [feita, setFeita] = useState<{ caminho: string; bytes: number } | null>(null);

  async function fazer(evento: React.FormEvent) {
    evento.preventDefault();
    if (!senha) return setErro({ texto: "Escolha uma senha para a cópia.", campo: "senha" });
    if (senha !== confirmacao) return setErro({ texto: "As duas senhas não são iguais.", campo: "confirmacao" });
    setErro(null);
    setState("saving");
    const resposta = await bridge.copia_fazer(senha);
    if (!resposta.ok) {
      setState("idle");
      return setErro({ texto: resposta.erro, campo: resposta.campo });
    }
    setSenha("");
    setConfirmacao("");
    setFeita(resposta.dados);
    setState("saved");
    window.setTimeout(() => setState("idle"), 2000);
    toast({ text: "Cópia de segurança pronta." });
  }

  return (
    <Section title="Cópia de segurança" summary="Um arquivo só com as viagens, as decisões, os cadastros, os vídeos no prazo e as configurações.">
      <form className="grid max-w-[560px] gap-5 pt-5" onSubmit={fazer} noValidate>
        <p className="text-[14px]">
          <b className="font-semibold">Sem esta senha, a cópia não abre.</b> Anote e guarde junto com o código de recuperação.
        </p>
        <Field label="Senha da cópia" htmlFor="copia-senha" error={erro?.campo === "senha" ? erro.texto : undefined}>
          <input id="copia-senha" className="input" type="password" autoComplete="new-password" value={senha} onChange={(e) => setSenha(e.target.value)} />
        </Field>
        <Field label="Repita a senha" htmlFor="copia-confirmacao" error={erro?.campo === "confirmacao" ? erro.texto : undefined}>
          <input
            id="copia-confirmacao"
            className="input"
            type="password"
            autoComplete="new-password"
            value={confirmacao}
            onChange={(e) => setConfirmacao(e.target.value)}
          />
        </Field>
        {erro && !["senha", "confirmacao"].includes(erro.campo ?? "") && (
          <p role="alert" className="text-[14px] text-alarme">
            {erro.texto}
          </p>
        )}
        <div>
          <SaveButton state={state}>Fazer cópia agora</SaveButton>
        </div>
        {feita && (
          <p className="anim-enter text-[14px] text-grafite">
            Cópia salva em <b className="break-all font-semibold text-tinta">{feita.caminho}</b> ({tamanho(feita.bytes)}). Leve para um pen drive ou
            uma pasta de rede, fora deste computador.
          </p>
        )}
      </form>
    </Section>
  );
}
