import { spawnSync } from 'node:child_process';
import { createWriteStream, existsSync, mkdirSync, renameSync, statSync, unlinkSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';

export const MAPSHAPER = 'mapshaper@0.7.61';

export const kb = (bytes) => `${(bytes / 1024).toFixed(1)} KB`;

/**
 * Baixa uma URL para o cache. Se o arquivo já existe, reaproveita (a menos que atualizar = true).
 * Devolve { caminho, baixadoAgora, bytes }.
 */
export async function baixar(url, caminho, { atualizar = false } = {}) {
  mkdirSync(dirname(caminho), { recursive: true });
  if (!atualizar && existsSync(caminho) && statSync(caminho).size > 0) {
    return { caminho, baixadoAgora: false, bytes: statSync(caminho).size };
  }
  const tmp = `${caminho}.parcial`;
  const tentativas = 4;
  for (let n = 1; ; n++) {
    console.log(`  baixando ${url}${n > 1 ? ` (tentativa ${n})` : ''}`);
    try {
      const resp = await fetch(url, { redirect: 'follow', headers: { 'user-agent': 'rotaguard-site-mapas (script de dados)' } });
      if (!resp.ok) throw new Error(`HTTP ${resp.status} ao baixar ${url}`);
      await pipeline(Readable.fromWeb(resp.body), createWriteStream(tmp));
      renameSync(tmp, caminho);
      return { caminho, baixadoAgora: true, bytes: statSync(caminho).size };
    } catch (e) {
      if (existsSync(tmp)) unlinkSync(tmp);
      // Os servidores do IBGE e do DNIT às vezes fecham a conexão no meio; tenta de novo com espera crescente.
      if (n >= tentativas) throw new Error(`Falha ao baixar ${url}: ${e.message}${e.cause ? ` (${e.cause.message || e.cause.code})` : ''}`);
      console.log(`  falhou (${e.cause?.code || e.message}); nova tentativa em ${n * 3} s`);
      await new Promise((r) => setTimeout(r, n * 3000));
    }
  }
}

/** Lê JSON tolerando BOM (a API de localidades do IBGE devolve BOM). */
export function parseJson(texto) {
  return JSON.parse(texto.replace(/^﻿/, ''));
}

/**
 * Roda o mapshaper fixado em MAPSHAPER via npx, sem shell no Node.
 * No Windows, chamar npx.cmd exigiria shell e quebraria aspas e caminhos com espaço;
 * por isso chamamos o npx-cli.js que acompanha o Node, com o próprio executável do Node.
 */
export function mapshaper(args) {
  const candidatos = [
    join(dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npx-cli.js'),
    join(dirname(process.execPath), '..', 'lib', 'node_modules', 'npm', 'bin', 'npx-cli.js'),
  ];
  const cli = candidatos.find((c) => existsSync(c));
  const [cmd, pre] = cli ? [process.execPath, [cli]] : ['npx', []];
  const r = spawnSync(cmd, [...pre, '--yes', MAPSHAPER, ...args], { stdio: ['ignore', 'inherit', 'inherit'] });
  if (r.error) throw r.error;
  if (r.status !== 0) throw new Error(`mapshaper terminou com código ${r.status}`);
}
