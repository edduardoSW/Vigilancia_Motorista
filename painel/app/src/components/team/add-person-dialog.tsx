"use client";

import { useState } from "react";
import { bridge, type Funcao } from "@/lib/bridge";
import { Choice } from "@/components/ui/choice";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { FRASE_FUNCAO, FUNCOES, NOME_FUNCAO, sugerirUsuario } from "./roles";
import { TempPassword } from "./temp-password";

interface Criada {
  nome: string;
  usuario: string;
  senha: string;
}

// Adicionar pessoa (spec 014): nome, usuário sugerido, função → senha temporária mostrada uma vez.
export function AddPersonDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [nome, setNome] = useState("");
  const [usuario, setUsuario] = useState("");
  const [usuarioEditado, setUsuarioEditado] = useState(false);
  const [funcao, setFuncao] = useState<Funcao>("supervisor");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<{ texto: string; campo?: string } | null>(null);
  const [criada, setCriada] = useState<Criada | null>(null);

  function fechar() {
    setNome("");
    setUsuario("");
    setUsuarioEditado(false);
    setFuncao("supervisor");
    setErro(null);
    setCriada(null);
    onClose();
  }

  async function adicionar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!nome.trim()) return setErro({ texto: "Escreva o nome da pessoa.", campo: "nome" });
    if (!usuario.trim()) return setErro({ texto: "Escreva o usuário para entrar.", campo: "usuario" });
    setEnviando(true);
    const resposta = await bridge.equipe_adicionar({ nome: nome.trim(), usuario: usuario.trim(), funcao });
    setEnviando(false);
    if (!resposta.ok) return setErro({ texto: resposta.erro, campo: resposta.campo });
    setErro(null);
    setCriada({ nome: resposta.dados.usuario.nome, usuario: resposta.dados.usuario.usuario, senha: resposta.dados.senha_temporaria });
    onCreated();
  }

  const erroDo = (campo: string) => (erro?.campo === campo ? erro.texto : undefined);

  return (
    <Dialog
      open={open}
      onClose={fechar}
      title={criada ? "Pessoa adicionada" : "Adicionar pessoa"}
      summary={criada ? undefined : "A pessoa entra com uma senha temporária e troca no primeiro acesso."}
      footer={
        criada ? (
          <button type="button" className="btn btn-primary" onClick={fechar}>
            Pronto, já passei a senha
          </button>
        ) : (
          <>
            <button type="button" className="btn" onClick={fechar}>
              Cancelar
            </button>
            <button type="submit" form="adicionar-pessoa" className="btn btn-primary" disabled={enviando}>
              {enviando ? "Adicionando…" : "Adicionar"}
            </button>
          </>
        )
      }
    >
      {criada ? (
        <TempPassword nome={criada.nome} usuario={criada.usuario} senha={criada.senha} />
      ) : (
        <form id="adicionar-pessoa" className="grid gap-5" onSubmit={adicionar} noValidate>
          <Field label="Nome" htmlFor="pessoa-nome" error={erroDo("nome")}>
            <input
              id="pessoa-nome"
              className="input"
              value={nome}
              autoComplete="off"
              autoFocus
              onChange={(e) => {
                setNome(e.target.value);
                if (!usuarioEditado) setUsuario(sugerirUsuario(e.target.value));
              }}
            />
          </Field>
          <Field label="Usuário para entrar" htmlFor="pessoa-usuario" hint="Sugerido pelo nome. Pode mudar." error={erroDo("usuario")}>
            <input
              id="pessoa-usuario"
              className="input"
              value={usuario}
              autoComplete="off"
              spellCheck={false}
              onChange={(e) => {
                setUsuario(e.target.value);
                setUsuarioEditado(true);
              }}
            />
          </Field>
          <fieldset className="grid gap-2">
            <legend className="mb-2 text-[14px] font-semibold">Função</legend>
            {FUNCOES.map((opcao) => (
              <Choice
                key={opcao}
                name="pessoa-funcao"
                value={opcao}
                checked={funcao === opcao}
                onChange={() => setFuncao(opcao)}
                title={NOME_FUNCAO[opcao]}
                description={FRASE_FUNCAO[opcao]}
              />
            ))}
          </fieldset>
          {erro && !["nome", "usuario"].includes(erro.campo ?? "") && (
            <p role="alert" className="text-[14px] text-alarme">
              {erro.texto}
            </p>
          )}
        </form>
      )}
    </Dialog>
  );
}
