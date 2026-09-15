"use client";

import { useState } from "react";
import { DetailList, DetailRow } from "@/components/drivers/detail-list";
import { bridge, type Funcao, type Usuario } from "@/lib/bridge";
import { Choice } from "@/components/ui/choice";
import { Dialog } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { FRASE_FUNCAO, FUNCOES, NOME_FUNCAO, quando, situacaoDe } from "./roles";
import { TempPassword } from "./temp-password";

type Confirmando = "senha" | "ativo" | null;

// Janela da pessoa, no centro (spec 014 decisões 8 e 9; spec 019 MOD-01): trocar função, criar senha nova, desativar
// ou reativar. Já é uma janela de ações: a função muda na hora, sem "Salvar". Ao fechar, o conteúdo desmonta (a senha
// nova não aparece de novo).
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
    <Dialog
      width={520}
      open={open && pessoa !== null}
      onClose={onClose}
      title={pessoa?.nome ?? ""}
      summary={pessoa ? `Usuário ${pessoa.usuario} · ${situacaoDe(pessoa)}` : undefined}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          Fechar
        </button>
      }
    >
      {pessoa && <PersonDetails key={pessoa.id} pessoa={pessoa} onChanged={onChanged} />}
    </Dialog>
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
      <DetailList>
        <DetailRow label="Último acesso">{quando(pessoa.ultimo_acesso)}</DetailRow>
        <DetailRow label="Situação">{situacaoDe(pessoa)}</DetailRow>
      </DetailList>

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
    <div className="anim-enter grid gap-3 rounded-[10px] border border-fio bg-superficie p-4">
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
