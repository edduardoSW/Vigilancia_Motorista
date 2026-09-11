/**
 * Posição do ponto subsolar (onde o Sol está a pino) para desenhar a noite no mapa-múndi.
 * Fórmulas da NOAA (General Solar Position Calculations): fração do ano γ, equação do tempo e declinação.
 * Precisão de alguns décimos de grau, suficiente para um mapa em escala 1:40 000 000.
 */
export interface PontoSolar {
  /** Longitude em graus, de -180 a 180. */
  longitude: number;
  /** Latitude (declinação) em graus. */
  latitude: number;
}

const GRAU = 180 / Math.PI;

export function pontoSubsolar(data: Date): PontoSolar {
  const ano = data.getUTCFullYear();
  const inicioDoAno = Date.UTC(ano, 0, 1);
  const bissexto = (ano % 4 === 0 && ano % 100 !== 0) || ano % 400 === 0;
  const diasNoAno = bissexto ? 366 : 365;
  const horasUtc = data.getUTCHours() + data.getUTCMinutes() / 60 + data.getUTCSeconds() / 3600;
  const diaDoAno = Math.floor((data.getTime() - inicioDoAno) / 86_400_000) + 1;
  const gama = ((2 * Math.PI) / diasNoAno) * (diaDoAno - 1 + (horasUtc - 12) / 24);

  const equacaoDoTempoMin =
    229.18 *
    (0.000075 +
      0.001868 * Math.cos(gama) -
      0.032077 * Math.sin(gama) -
      0.014615 * Math.cos(2 * gama) -
      0.040849 * Math.sin(2 * gama));

  const declinacao =
    0.006918 -
    0.399912 * Math.cos(gama) +
    0.070257 * Math.sin(gama) -
    0.006758 * Math.cos(2 * gama) +
    0.000907 * Math.sin(2 * gama) -
    0.002697 * Math.cos(3 * gama) +
    0.00148 * Math.sin(3 * gama);

  let longitude = -15 * (horasUtc - 12 + equacaoDoTempoMin / 60);
  longitude = ((((longitude + 180) % 360) + 360) % 360) - 180;

  return { longitude, latitude: declinacao * GRAU };
}

/** Centro do círculo da noite: o ponto oposto ao subsolar. */
export function antipodaSolar(data: Date): [number, number] {
  const { longitude, latitude } = pontoSubsolar(data);
  const lon = longitude > 0 ? longitude - 180 : longitude + 180;
  return [lon, -latitude];
}
