import Image from "next/image";
import {getTranslations} from "next-intl/server";
export default async function CreditosPage(){
const t=await getTranslations("creditos");const h=await getTranslations("home");
const images=[["onibus-rodoviario","busAlt"],["caixa-conceito","deviceAlt"],["caminhao-rodovia","truckAlt"],["motorista-rodoviario","driverAlt"],["chegada-garagem","arrivalAlt"]];
return <section className="inner-page shell"><h1>{t("titulo")}</h1><p className="lead">{t("texto")}</p><div className="credits-grid">{images.map(([src,alt])=><figure key={src}><Image src={`/midia/rotaguard/${src}.webp`} alt={h(alt)} width={1536} height={1024} sizes="(max-width:640px) 90vw,45vw"/><figcaption>{h(alt)}</figcaption></figure>)}</div></section>;
}
