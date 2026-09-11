import { getTranslations } from "next-intl/server";

type Situacao = "testado" | "validacao" | "desenvolvimento" | "prototipo" | "teste";

// Situação de cada item conferida no código e no PRD (docs/produto/PRD.md, seção 6), não é marketing.
const linhas: { chave: string; situacao: Situacao }[] = [
  { chave: "caixa", situacao: "prototipo" },
  { chave: "sono", situacao: "testado" },
  { chave: "celular", situacao: "validacao" },
  { chave: "alarme", situacao: "testado" },
  { chave: "registro", situacao: "desenvolvimento" },
  { chave: "trechos", situacao: "desenvolvimento" },
  { chave: "coleta", situacao: "desenvolvimento" },
  { chave: "internet", situacao: "testado" },
  { chave: "camera", situacao: "teste" },
  { chave: "local", situacao: "testado" },
];

export async function FichaTecnica() {
  const t = await getTranslations("ficha");

  return (
    <section id="ficha" aria-labelledby="titulo-ficha" className="com-trilho border-t border-fio">
      <div className="shell py-20 lg:py-28">
        <h2 id="titulo-ficha" className="text-[clamp(2.6rem,5vw,4.8rem)]">
          {t("titulo")}
        </h2>
        <div className="mt-10 overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-left">
            <thead>
              <tr className="border-b-2 border-asfalto">
                <th scope="col" className="etiqueta py-3 pr-6 font-normal text-grafite">{t("colunaItem")}</th>
                <th scope="col" className="etiqueta py-3 pr-6 font-normal text-grafite">{t("colunaValor")}</th>
                <th scope="col" className="etiqueta py-3 font-normal text-grafite">{t("colunaSituacao")}</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((l) => (
                <tr key={l.chave} className="border-b border-fio align-baseline">
                  <th scope="row" className="py-4 pr-6 font-titulo text-[1.5rem] leading-tight font-bold">
                    {t(`linhas.${l.chave}.item`)}
                  </th>
                  <td className="py-4 pr-6 text-[1.05rem]">{t(`linhas.${l.chave}.valor`)}</td>
                  <td className="etiqueta py-4 whitespace-nowrap text-grafite">{t(`situacoes.${l.situacao}`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
