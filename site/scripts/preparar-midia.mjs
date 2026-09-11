import sharp from "sharp";
import {mkdir,copyFile} from "node:fs/promises";
import path from "node:path";
const root=path.resolve(import.meta.dirname,"..");
const originals=path.join(root,"../docs/site/midia/originais");
const source=process.argv[2] ? path.resolve(process.argv[2]) : originals;
const names=["onibus-rodoviario","caixa-conceito","caminhao-rodovia","motorista-rodoviario","chegada-garagem"];
await mkdir(path.join(root,"public/midia/rotaguard"),{recursive:true});
await mkdir(originals,{recursive:true});
for(const name of names){
const original=path.join(originals,name+".png");
if(source!==originals)await copyFile(path.join(source,name+".png"),original);
await sharp(original).resize({width:1536,withoutEnlargement:true}).webp({quality:85}).toFile(path.join(root,"public/midia/rotaguard",name+".webp"));
console.log("Preparada: "+name);
}
