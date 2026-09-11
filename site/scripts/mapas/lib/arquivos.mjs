// Leitores mínimos de ZIP, Shapefile (.shp de linhas) e dBase (.dbf), só com módulos do Node.
// Evitam converter a base inteira do SNV (5 milhões de vértices) para GeoJSON só para medir comprimentos.
import { inflateRawSync } from 'node:zlib';

/** Lista as entradas de um ZIP (sem suporte a ZIP64, que estes arquivos não usam). */
export function listarZip(buf) {
  const inicioBusca = Math.max(0, buf.length - 65557);
  let eocd = -1;
  for (let i = buf.length - 22; i >= inicioBusca; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('ZIP inválido: fim do diretório central não encontrado');
  const total = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  const entradas = [];
  for (let k = 0; k < total; k++) {
    if (buf.readUInt32LE(p) !== 0x02014b50) throw new Error('ZIP inválido: diretório central corrompido');
    const metodo = buf.readUInt16LE(p + 10);
    const tamComprimido = buf.readUInt32LE(p + 20);
    const tamOriginal = buf.readUInt32LE(p + 24);
    const lenNome = buf.readUInt16LE(p + 28);
    const lenExtra = buf.readUInt16LE(p + 30);
    const lenComent = buf.readUInt16LE(p + 32);
    const offsetLocal = buf.readUInt32LE(p + 42);
    const nome = buf.toString('utf8', p + 46, p + 46 + lenNome);
    if (tamComprimido === 0xffffffff || offsetLocal === 0xffffffff) throw new Error(`ZIP64 não suportado (${nome})`);
    entradas.push({ nome, metodo, tamComprimido, tamOriginal, offsetLocal });
    p += 46 + lenNome + lenExtra + lenComent;
  }
  return entradas;
}

/** Extrai uma entrada do ZIP para um Buffer. */
export function extrairDoZip(buf, entrada) {
  const p = entrada.offsetLocal;
  if (buf.readUInt32LE(p) !== 0x04034b50) throw new Error(`ZIP inválido: cabeçalho local de ${entrada.nome}`);
  const inicio = p + 30 + buf.readUInt16LE(p + 26) + buf.readUInt16LE(p + 28);
  const dados = buf.subarray(inicio, inicio + entrada.tamComprimido);
  if (entrada.metodo === 0) return Buffer.from(dados);
  if (entrada.metodo === 8) return inflateRawSync(dados);
  throw new Error(`Método de compressão ${entrada.metodo} não suportado (${entrada.nome})`);
}

/** Lê um .dbf (dBase III) e devolve um array de objetos. Campos C viram string; N e F viram número ou null. */
export function lerDbf(buf, codificacao = 'utf8') {
  const nRegistros = buf.readUInt32LE(4);
  const tamCabecalho = buf.readUInt16LE(8);
  const tamRegistro = buf.readUInt16LE(10);
  const campos = [];
  let desloc = 1; // byte 0 de cada registro é a marca de exclusão
  for (let p = 32; buf[p] !== 0x0d && p < tamCabecalho; p += 32) {
    const nomeBruto = buf.subarray(p, p + 11);
    const fim = nomeBruto.indexOf(0);
    const nome = nomeBruto.toString('latin1', 0, fim < 0 ? 11 : fim);
    const tipo = String.fromCharCode(buf[p + 11]);
    const tamanho = buf[p + 16];
    campos.push({ nome, tipo, tamanho, desloc });
    desloc += tamanho;
  }
  const registros = new Array(nRegistros);
  for (let r = 0; r < nRegistros; r++) {
    const base = tamCabecalho + r * tamRegistro;
    const obj = {};
    for (const c of campos) {
      // Alguns .dbf (ex.: Natural Earth) completam o campo com bytes nulos em vez de espaços.
      const bruto = buf.toString(codificacao, base + c.desloc, base + c.desloc + c.tamanho).replace(/\0+/g, '').trim();
      if (c.tipo === 'N' || c.tipo === 'F') obj[c.nome] = bruto === '' ? null : Number(bruto);
      else obj[c.nome] = bruto;
    }
    registros[r] = obj;
  }
  return registros;
}

/**
 * Lê um .shp de linhas (tipos 3, 13 e 23) e devolve, por registro, um array de partes;
 * cada parte é um array de [lon, lat]. Registros nulos viram null.
 */
export function lerShpLinhas(buf) {
  const geometrias = [];
  let p = 100;
  while (p + 8 <= buf.length) {
    const tamConteudo = buf.readUInt32BE(p + 4) * 2;
    const c = p + 8;
    const tipo = buf.readInt32LE(c);
    if (tipo === 0) {
      geometrias.push(null);
    } else if (tipo === 3 || tipo === 13 || tipo === 23) {
      const nPartes = buf.readInt32LE(c + 36);
      const nPontos = buf.readInt32LE(c + 40);
      const inicioPontos = c + 44 + 4 * nPartes;
      const partes = [];
      for (let k = 0; k < nPartes; k++) {
        const de = buf.readInt32LE(c + 44 + 4 * k);
        const ate = k + 1 < nPartes ? buf.readInt32LE(c + 44 + 4 * (k + 1)) : nPontos;
        const parte = new Array(ate - de);
        for (let i = de; i < ate; i++) {
          const q = inicioPontos + 16 * i;
          parte[i - de] = [buf.readDoubleLE(q), buf.readDoubleLE(q + 8)];
        }
        partes.push(parte);
      }
      geometrias.push(partes);
    } else {
      throw new Error(`Tipo de geometria ${tipo} não suportado neste leitor (esperado: linhas)`);
    }
    p = c + tamConteudo;
  }
  return geometrias;
}
