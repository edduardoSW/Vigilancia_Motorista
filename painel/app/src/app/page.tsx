import { Icon } from "@/components/icons";
import { dados, dia, hora, motoristaDe, nomeDoVeiculo, veiculoDe } from "@/content";
import { cn } from "@/lib/utils";

// Caixa conectada (prévia 2): a leitura da viagem em passos simples, um por vez.
export default function ConnectedBoxPage() {
  const box = dados.coletas[0];

  if (!box) {
    return (
      <section className="max-w-[720px] px-14 pt-[70px]">
        <div className="grid size-14 place-items-center rounded-2xl bg-[#e4ebdf] text-verde">
          <Icon name="box" size={28} />
        </div>
        <h1 className="mt-[22px] font-titulo text-[38px] font-semibold leading-[1.1] tracking-[-0.01em]">Nenhuma caixa conectada</h1>
        <p className="mt-2 text-[16px] text-grafite">Conecte a caixa no computador. O painel reconhece sozinho e começa a ler a viagem.</p>
      </section>
    );
  }

  const vehicle = veiculoDe(box.veiculo);
  const driver = motoristaDe(box.motorista);
  const done = box.etapas.filter((step) => step.feita).length;

  return (
    <section className="max-w-[720px] px-14 pb-16 pt-[70px]">
      <div className="grid size-14 place-items-center rounded-2xl bg-[#e4ebdf] text-verde">
        <Icon name="box" size={28} />
      </div>
      <h1 className="mt-[22px] font-titulo text-[38px] font-semibold leading-[1.1] tracking-[-0.01em]">
        Caixa do {vehicle ? nomeDoVeiculo(vehicle.tipo, vehicle.prefixo) : box.caixa} conectada
      </h1>
      <p className="mt-2 text-[16px] text-grafite">
        Viagem de {dia(box.saida)} às {hora(box.saida)} até {dia(box.chegada)} às {hora(box.chegada)} · motorista {driver?.nome}
      </p>

      <ol className="mt-[34px]">
        {box.etapas.map((step, index) => {
          const state = step.feita ? "done" : index === done ? "now" : "later";
          return (
            <li key={step.nome} className="grid grid-cols-[34px_minmax(0,1fr)] gap-3.5 border-b border-fio py-3.5">
              <span
                className={cn(
                  "grid size-[30px] place-items-center rounded-full border-2 text-[14px] font-bold",
                  state === "done" && "border-verde bg-verde text-white",
                  state === "now" && "border-verde text-verde",
                  state === "later" && "border-fio text-grafite",
                )}
              >
                {state === "done" ? "✓" : index + 1}
              </span>
              <div>
                <b className={cn("block text-[16px]", state === "later" && "text-[#8b978f]")}>{step.nome}</b>
                <span className="text-[14px] text-grafite">{state === "now" ? `${box.progresso}% lido` : step.detalhe}</span>
                {state === "now" && (
                  <div
                    role="progressbar"
                    aria-label={step.nome}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={box.progresso}
                    className="mt-3 h-1.5 max-w-[420px] overflow-hidden rounded-[3px] bg-[#e5ebe1]"
                  >
                    <div className="h-full rounded-[3px] bg-verde" style={{ width: `${box.progresso}%` }} />
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      <div className="mt-[30px] flex items-center gap-4 text-[14px] text-grafite">
        <button type="button" disabled className="btn">
          Abrir viagem
        </button>
        <span>Fica pronto em cerca de 1 minuto. Enquanto isso, pode olhar as outras viagens.</span>
      </div>
    </section>
  );
}
