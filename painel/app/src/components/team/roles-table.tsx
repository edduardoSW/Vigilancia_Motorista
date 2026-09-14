import { FUNCOES, NOME_FUNCAO, TABELA_PERMISSOES } from "./roles";

// "O que cada função pode fazer" (prévia 7): marca para sim e a palavra "não".
export function RolesTable() {
  return (
    <section className="mt-12" aria-labelledby="funcoes-titulo">
      <h2 id="funcoes-titulo" className="font-titulo text-[20px] font-semibold">
        O que cada função pode fazer
      </h2>
      <table className="mt-4 w-full border-collapse text-[14px]">
        <thead>
          <tr className="border-b border-fio text-grafite">
            <th scope="col" className="py-2.5 text-left font-medium">
              <span className="sr-only">O que pode fazer</span>
            </th>
            {FUNCOES.map((funcao) => (
              <th key={funcao} scope="col" className="w-[130px] py-2.5 text-center font-medium">
                {NOME_FUNCAO[funcao]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {TABELA_PERMISSOES.map((linha) => (
            <tr key={linha.texto} className="h-11 border-b border-fio">
              <th scope="row" className="text-left font-normal">
                {linha.texto}
              </th>
              {FUNCOES.map((funcao) => (
                <td key={funcao} className="text-center">
                  {linha.funcoes.includes(funcao) ? (
                    <svg className="inline-block text-verde" width="16" height="16" viewBox="0 0 24 24" fill="none" role="img" aria-label="sim">
                      <path d="m5 12.5 4.2 4.2L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : (
                    <span className="text-[13px] text-grafite">não</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
