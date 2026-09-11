export function Arrow({ diagonal = false, className = "" }: { diagonal?: boolean; className?: string }) {
return <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d={diagonal ? "M6 18 18 6M6 6h12v12" : "M4 12h16m-6-6 6 6-6 6"} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function Symbol({ kind }: { kind: string }) {
const paths: Record<string, string> = {
eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
sound: "M11 4 5 9H2v6h3l6 5V4Zm4 4a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14",
log: "M6 3h12v18H6V3Zm3 5h6m-6 4h6m-6 4h3",
offline: "M4 4 20 20M2 8a16 16 0 0 1 4-2m4-1a16 16 0 0 1 12 3M5 12a11 11 0 0 1 5-2m5 1 4 1M9 16a5 5 0 0 1 6 0m-3 4h.01",
shield: "m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Zm-4 10 3 3 5-6",
bus: "M5 3h14v15H5V3Zm0 10h14M8 6h8M8 16h.01M16 16h.01M7 18v3m10-3v3",
truck: "M2 5h12v13H2V5Zm12 5h4l4 5v3h-8M6 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4m12 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4"
};
return <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d={paths[kind] || paths.log} stroke="currentColor" strokeWidth="1.35" strokeLinejoin="round" strokeLinecap="round" /></svg>;
}
