"use client";

import { useState, type FormEvent } from "react";
import { Choice } from "@/components/ui/choice";
import { Field } from "@/components/ui/field";
import { bridge, type Motorista } from "@/lib/bridge";
import { diasAte, formatarData, hojeIso, nomeCurto, situacaoCnh, soDigitos, validarCnh, validarCpf } from "@/lib/validators";

// Formulário do motorista (prévia 5 e spec 015, decisão 1): o mesmo para cadastrar e editar, dentro do painel lateral.
// Valida ao sair do campo; o Python confere de novo e o erro dele volta marcado no campo certo (`campo`).

export type SaveState = "idle" | "saving" | "saved";

interface Campos {
  nome: string;
  nome_curto: string;
  matricula: string;
  telefone: string;
  cpf: string;
  cnh_numero: string;
  cnh_categoria: Motorista["cnh_categoria"];
  cnh_validade: string;
  situacao: Motorista["situacao"];
  termo: "assinado" | "pendente";
  termo_data: string;
  observacoes: string;
}
type NomeCampo = keyof Campos;
type Erros = Partial<Record<NomeCampo, string>>;

export const SITUACAO_MOTORISTA: Record<Motorista["situacao"], string> = {
  ativo: "Ativo",
  afastado: "Afastado",
  desligado: "Desligado",
};

const ORDEM: NomeCampo[] = ["nome", "matricula", "nome_curto", "telefone", "cpf", "cnh_numero", "cnh_categoria", "cnh_validade", "termo_data"];

function camposDe(motorista: Motorista | null): Campos {
  if (!motorista) {
    return {
      nome: "",
      nome_curto: "",
      matricula: "",
      telefone: "",
      cpf: "",
      cnh_numero: "",
      cnh_categoria: "D",
      cnh_validade: "",
      situacao: "ativo",
      termo: "pendente",
      termo_data: "",
      observacoes: "",
    };
  }
  return {
    nome: motorista.nome,
    nome_curto: motorista.nome_curto,
    matricula: motorista.matricula,
    telefone: motorista.telefone ?? "",
    cpf: motorista.cpf ?? "",
    cnh_numero: motorista.cnh_numero,
    cnh_categoria: motorista.cnh_categoria,
    cnh_validade: motorista.cnh_validade,
    situacao: motorista.situacao,
    termo: motorista.termo.assinado ? "assinado" : "pendente",
    termo_data: motorista.termo.data ?? "",
    observacoes: motorista.observacoes ?? "",
  };
}

function validar(campos: Campos, outros: Motorista[]): Erros {
  const erros: Erros = {};
  const nome = campos.nome.trim();
  if (!nome) erros.nome = "Informe o nome completo.";
  else if (nome.split(/\s+/).length < 2) erros.nome = "Informe nome e sobrenome.";
  if (!campos.nome_curto.trim()) erros.nome_curto = "Informe como o nome aparece nos relatórios.";
  const matricula = campos.matricula.trim();
  if (!matricula) erros.matricula = "Informe a matrícula.";
  else if (outros.some((outro) => outro.matricula === matricula)) erros.matricula = "Já existe um motorista com esta matrícula.";
  const cnh = validarCnh(campos.cnh_numero);
  if (cnh) erros.cnh_numero = cnh;
  else if (outros.some((outro) => outro.cnh_numero === soDigitos(campos.cnh_numero))) erros.cnh_numero = "Já existe um motorista com esta CNH.";
  const cpf = validarCpf(campos.cpf);
  if (cpf) erros.cpf = cpf;
  if (!campos.cnh_validade) erros.cnh_validade = "Informe até quando a CNH vale.";
  if (campos.termo === "assinado") {
    if (!campos.termo_data) erros.termo_data = "Informe a data em que assinou.";
    else if (campos.termo_data > hojeIso()) erros.termo_data = "A data não pode ser depois de hoje.";
  }
  return erros;
}

/** O Python marca `campo` com o nome da propriedade; "termo" e "termo.data" caem na data do termo. */
function campoDoServidor(campo: string | undefined): NomeCampo | null {
  if (!campo) return null;
  if (campo.startsWith("termo")) return "termo_data";
  return campo in camposDe(null) ? (campo as NomeCampo) : null;
}

function avisoValidade(validade: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(validade)) return undefined;
  const situacao = situacaoCnh(validade, hojeIso());
  if (situacao === "vencida") return `CNH vencida em ${formatarData(validade)}. O painel salva e mostra o aviso.`;
  if (situacao === "vence_em_breve") {
    const dias = diasAte(validade, hojeIso());
    return dias === 0 ? "Vence hoje. O painel avisa no Início e na lista." : `Vence em ${dias} dias. O painel avisa no Início e na lista.`;
  }
  return undefined;
}

export function DriverForm({
  formId,
  motorista,
  outros,
  readOnly,
  onSaved,
  onStateChange,
}: {
  formId: string;
  motorista: Motorista | null;
  /** Os outros motoristas, para avisar matrícula e CNH repetidas antes de salvar. */
  outros: Motorista[];
  readOnly: boolean;
  onSaved: (motorista: Motorista) => void;
  onStateChange: (state: SaveState) => void;
}) {
  const [campos, setCampos] = useState(() => camposDe(motorista));
  const [tocados, setTocados] = useState<Set<NomeCampo>>(() => new Set());
  const [tentou, setTentou] = useState(false);
  const [doServidor, setDoServidor] = useState<Erros>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [nomeCurtoEditado, setNomeCurtoEditado] = useState(Boolean(motorista));

  const locais = validar(campos, outros);
  const erro = (nome: NomeCampo) => doServidor[nome] ?? (tentou || tocados.has(nome) ? locais[nome] : undefined);
  const id = (nome: NomeCampo) => `${formId}-${nome}`;

  function mudar<K extends NomeCampo>(nome: K, valor: Campos[K]) {
    onStateChange("idle");
    setDoServidor((atual) => ({ ...atual, [nome]: undefined }));
    setCampos((atual) => {
      const novo = { ...atual, [nome]: valor };
      if (nome === "nome" && !nomeCurtoEditado) novo.nome_curto = nomeCurto(String(valor));
      return novo;
    });
    if (nome === "nome_curto") setNomeCurtoEditado(true);
  }

  const tocar = (nome: NomeCampo) => setTocados((atual) => (atual.has(nome) ? atual : new Set(atual).add(nome)));

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (readOnly) return;
    setTentou(true);
    setErroGeral(null);
    const primeiro = ORDEM.find((nome) => locais[nome]);
    if (primeiro) {
      document.getElementById(id(primeiro))?.focus();
      return;
    }
    onStateChange("saving");
    const assinado = campos.termo === "assinado";
    const resposta = await bridge.motorista_salvar({
      ...(motorista ? { id: motorista.id } : {}),
      nome: campos.nome.trim(),
      nome_curto: campos.nome_curto.trim(),
      matricula: campos.matricula.trim(),
      telefone: campos.telefone.trim() || null,
      cpf: soDigitos(campos.cpf) || null,
      cnh_numero: soDigitos(campos.cnh_numero),
      cnh_categoria: campos.cnh_categoria,
      cnh_validade: campos.cnh_validade,
      situacao: campos.situacao,
      termo: { assinado, data: assinado ? campos.termo_data : null, versao: motorista?.termo.versao ?? null },
      observacoes: campos.observacoes.trim() || null,
    });
    if (!resposta.ok) {
      onStateChange("idle");
      const campo = campoDoServidor(resposta.campo);
      if (campo) {
        setDoServidor((atual) => ({ ...atual, [campo]: resposta.erro }));
        document.getElementById(id(campo))?.focus();
      } else {
        setErroGeral(resposta.erro);
      }
      return;
    }
    onStateChange("saved");
    onSaved(resposta.dados);
  }

  const texto = (nome: "nome" | "nome_curto" | "matricula" | "telefone" | "cpf" | "cnh_numero", extra?: React.InputHTMLAttributes<HTMLInputElement>) => (
    <input
      id={id(nome)}
      className="input"
      value={campos[nome]}
      onChange={(evento) => mudar(nome, evento.target.value)}
      onBlur={() => tocar(nome)}
      aria-invalid={Boolean(erro(nome))}
      autoComplete="off"
      {...extra}
    />
  );

  return (
    <form id={formId} onSubmit={enviar} noValidate>
      <fieldset disabled={readOnly} className="m-0 min-w-0 border-0 p-0">
        <h3 className="font-titulo text-[15px] font-semibold">Dados do motorista</h3>
        <div className="mt-3 grid grid-cols-2 gap-x-4">
          <div className="col-span-2">
            <Field label="Nome completo" htmlFor={id("nome")} error={erro("nome")}>
              {texto("nome", { autoFocus: !motorista })}
            </Field>
          </div>
          <Field label="Matrícula" htmlFor={id("matricula")} error={erro("matricula")}>
            {texto("matricula")}
          </Field>
          <Field
            label="Nome nos relatórios"
            htmlFor={id("nome_curto")}
            hint={nomeCurtoEditado ? undefined : "Sugerido pelo nome. Pode mudar."}
            error={erro("nome_curto")}
          >
            {texto("nome_curto")}
          </Field>
          <Field label="Telefone" optional htmlFor={id("telefone")} error={erro("telefone")}>
            {texto("telefone", { inputMode: "tel", placeholder: "(11) 98765-4321" })}
          </Field>
          <Field label="CPF" optional htmlFor={id("cpf")} error={erro("cpf")}>
            {texto("cpf", { inputMode: "numeric", placeholder: "Só se a empresa precisar" })}
          </Field>
        </div>

        <h3 className="mt-2 border-t border-fio pt-5 font-titulo text-[15px] font-semibold">Carteira de motorista</h3>
        <div className="mt-3 grid grid-cols-2 gap-x-4">
          <div className="col-span-2">
            <Field label="Número da CNH" htmlFor={id("cnh_numero")} error={erro("cnh_numero")}>
              {texto("cnh_numero", { inputMode: "numeric", maxLength: 14 })}
            </Field>
          </div>
          <Field label="Categoria" htmlFor={id("cnh_categoria")}>
            <select
              id={id("cnh_categoria")}
              className="select"
              value={campos.cnh_categoria}
              onChange={(evento) => mudar("cnh_categoria", evento.target.value as Campos["cnh_categoria"])}
            >
              <option value="C">C</option>
              <option value="D">D</option>
              <option value="E">E</option>
            </select>
          </Field>
          <Field label="Vale até" htmlFor={id("cnh_validade")} hint={avisoValidade(campos.cnh_validade)} error={erro("cnh_validade")}>
            <input
              id={id("cnh_validade")}
              type="date"
              className="input"
              value={campos.cnh_validade}
              onChange={(evento) => mudar("cnh_validade", evento.target.value)}
              onBlur={() => tocar("cnh_validade")}
              aria-invalid={Boolean(erro("cnh_validade"))}
            />
          </Field>
        </div>

        <h3 className="mt-2 border-t border-fio pt-5 font-titulo text-[15px] font-semibold">Termo de ciência do monitoramento</h3>
        <div className="mb-4 mt-3 grid grid-cols-2 gap-3">
          <Choice
            name={`${formId}-termo`}
            value="assinado"
            checked={campos.termo === "assinado"}
            onChange={() => mudar("termo", "assinado")}
            title="Já assinou"
            description="Informe a data em que assinou o termo."
          />
          <Choice
            name={`${formId}-termo`}
            value="pendente"
            checked={campos.termo === "pendente"}
            onChange={() => mudar("termo", "pendente")}
            title="Ainda não assinou"
            description="Os vídeos das viagens dele ficam trancados até registrar."
          />
        </div>
        {campos.termo === "assinado" && (
          <div className="anim-enter grid grid-cols-2 gap-x-4">
            <Field label="Assinou em" htmlFor={id("termo_data")} error={erro("termo_data")}>
              <input
                id={id("termo_data")}
                type="date"
                className="input"
                value={campos.termo_data}
                max={hojeIso()}
                onChange={(evento) => mudar("termo_data", evento.target.value)}
                onBlur={() => tocar("termo_data")}
                aria-invalid={Boolean(erro("termo_data"))}
              />
            </Field>
          </div>
        )}

        {motorista && (
          <>
            <h3 className="mt-2 border-t border-fio pt-5 font-titulo text-[15px] font-semibold">Situação</h3>
            <div className="mt-3 grid grid-cols-2 gap-x-4">
              <Field
                label="Situação"
                htmlFor={id("situacao")}
                hint={campos.situacao === "desligado" ? "Sai da lista do dia a dia e continua nas viagens antigas." : undefined}
              >
                <select
                  id={id("situacao")}
                  className="select"
                  value={campos.situacao}
                  onChange={(evento) => mudar("situacao", evento.target.value as Campos["situacao"])}
                >
                  {Object.entries(SITUACAO_MOTORISTA).map(([valor, rotulo]) => (
                    <option key={valor} value={valor}>
                      {rotulo}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="col-span-2">
                <Field label="Observações" optional htmlFor={id("observacoes")}>
                  <textarea
                    id={id("observacoes")}
                    className="input min-h-[72px] py-2"
                    maxLength={280}
                    value={campos.observacoes}
                    onChange={(evento) => mudar("observacoes", evento.target.value)}
                  />
                </Field>
              </div>
            </div>
          </>
        )}

        {erroGeral && (
          <p role="alert" className="mt-5 text-[13.5px] font-semibold text-alarme">
            {erroGeral}
          </p>
        )}
      </fieldset>
    </form>
  );
}
