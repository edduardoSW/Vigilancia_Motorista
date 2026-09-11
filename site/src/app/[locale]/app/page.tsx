import type {Metadata} from "next";
import {DownloadArea} from "@/components/download-area";
export const metadata:Metadata={robots:{index:false,follow:false}};
export default function AppPage(){return <DownloadArea/>;}
