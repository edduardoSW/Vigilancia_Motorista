"use client";

import { useState } from "react";
import { bridge, type Funcao, type Usuario } from "@/lib/bridge";
import { Choice } from "@/components/ui/choice";
import { Drawer } from "@/components/ui/drawer";
import { useToast } from "@/components/ui/toast";
import { FRASE_FUNCAO, FUNCOES, NOME_FUNCAO, quando, situacaoDe } from "./roles";
import { TempPassword } from "./temp-password";

type Confirmando = "senha" | "ativo" | null;

// Painel lateral da pessoa: trocar função, criar senha nova, desativar ou reativar (spec 014, decisões 8 e 9).
// A pessoa continua no painel enquanto ele desliza para fora; ao fechar, o conteúdo desmonta (senha nova não volta).
export function PersonDrawer({
  open,
  pessoa,
  onClose,
  onChanged,
}: {
  open: boolean;
  pessoa: Usuario | null;
  onClose: () => void;
  onChanged: () => void;
}) {
  return (
    <Drawer
      open={open && pessoa !== null}
      onClose={onClose}
      title={pessoa?.nome ?? ""}
      summary={pessoa ? `Usuário ${pessoa.usuario} · ${situacaoDe(pessoa)}` : undefined}
    >
      {pessoa && <PersonDetails key={pessoa.id} pessoa={pessoa} onChanged={onChanged} />}
    </Drawer>
  );
}

function PersonDetails({ pessoa, onChanged }: { pessoa: Usuario; onChanged: () => void }) {
  const { toast } = useToast();
  const [funcao, setFuncao] = useState<Funcao>(pessoa.funcao);
  const [confirmando, setConfirmando] = useState<Confirmando>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [senha, setSenha] = useState<string | null>(null);

  async function trocarFuncao(nova: Funcao) {
    if (nova === pessoa.funcao) return setFuncao(nova);
    const anterior = funcao;
    setFuncao(nova);
    setErro(null);
    const resposta = await bridge.equipe_alterar(pessoa.id, { funcao: nova });
    if (!resposta.ok) {
      setFuncao(anterior);
      return setErro(resposta.erro);
    }
    toast({ text: `${pessoa.nome} agora é ${NOME_FUNCAO[nova]}.` });
    onChanged();
  }

  async function criarSenha() {
    setOcupado(true);
    setErro(null);
    const resposta = await bridge.equipe_nova_senha(pessoa.id);
    setOcupado(false);
    setConfirmando(null);
    if (!resposta.ok) return setErro(resposta.erro);
    setSenha(resposta.dados.senha_temporaria);
    onChanged();
  }

  async function mudarAtivo() {
    setOcupado(true);
    setErro(null);
    const resposta = await bridge.equipe_alterar(pessoa.id, { ativo: !pessoa.ativo });
    setOcupado(false);
    setConfirmando(null);
    if (!resposta.ok) return setErro(resposta.erro);
    toast({ text: pessoa.ativo ? `${pessoa.nome} não entra mais no painel.` : `${pessoa.nome} pode entrar de novo.` });
    onChanged();
  }

  if (senha) return <TempPassword nome={pessoa.nome} usuario={pessoa.usuario} senha={senha} />;

  return (
    <div className="grid gap-8">
      <dl className="grid grid-cols-[130px_minmax(0,1fr)] gap-y-2 text-[14px]">
        <dt className="text-grafite">Último acesso</dt>
        <dd>{quando(pessoa.ultimo_acesso)}</dd>
        <dt className="text-grafite">Situação</dt>
        <dd>{situacaoDe(pessoa)}</dd>
      </dl>

      <fieldset className="grid gap-2" disabled={!pessoa.ativo}>
        <legend className="mb-2 text-[14px] font-semibold">Função</legend>
        {FUNCOES.map((opcao) => (
          <Choice
            key={opcao}
            name={`funcao-${pessoa.id}`}
            value={opcao}
            checked={funcao === opcao}
            onChange={() => void trocarFuncao(opcao)}
            title={NOME_FUNCAO[opcao]}
            description={FRASE_FUNCAO[opcao]}
          />
        ))}
      </fieldset>

      {erro && (
        <p role="alert" className="text-[14px] text-alarme">
          {erro}
        </p>
      )}

      <section className="grid gap-3 border-t border-fio pt-6">
        <h3 className="text-[14px] font-semibold">Senha esquecida</h3>
        {confirmando === "senha" ? (
          <Confirm
            texto="A senha atual deixa de valer agora. Criar uma senha nova?"
            acao="Criar senha nova"
            ocupado={ocupado}
            onConfirm={criarSenha}
            onCancel={() => setConfirmando(null)}
          />
        ) : (
          <button type="button" className="btn w-fit" disabled={!pessoa.ativo} onClick={() => setConfirmando("senha")}>
            Criar senha nova
          </button>
        )}
      </section>

      <section className="grid gap-3 border-t border-fio pt-6">
        <h3 className="text-[14px] font-semibold">{pessoa.ativo ? "Saiu da empresa?" : "Voltou para a empresa?"}</h3>
        <p className="text-[13.5px] text-grafite">Ninguém é apagado. O nome continua nas verificações que a pessoa fez.</p>
        {confirmando === "ativo" ? (
          <Confirm
            texto={pessoa.ativo ? `${pessoa.nome} não vai mais conseguir entrar. Desativar?` : `${pessoa.nome} vai poder entrar de novo. Reativar?`}
            acao={pessoa.ativo ? "Desativar" : "Reativar"}
            perigo={pessoa.ativo}
            ocupado={ocupado}
            onConfirm={mudarAtivo}
            onCancel={() => setConfirmando(null)}
          />
        ) : (
          <button type="button" className="btn w-fit" onClick={() => setConfirmando("ativo")}>
            {pessoa.ativo ? "Desativar" : "Reativar"}
          </button>
        )}
      </section>
    </div>
  );
}

function Confirm(props: { texto: string; acao: string; perigo?: boolean; ocupado: boolean; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="anim-enter grid gap-3 rounded-[10px] border border-fio bg-white p-4">
      <p className="text-[14px]">{props.texto}</p>
      <div className="flex gap-2">
        <button
          type="button"
          className={props.perigo ? "btn btn-small border-alarme text-alarme" : "btn btn-small btn-primary"}
          disabled={props.ocupado}
          onClick={props.onConfirm}
        >
          {props.ocupado ? "Um momento…" : props.acao}
        </button>
        <button type="button" className="btn btn-small" onClick={props.onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
