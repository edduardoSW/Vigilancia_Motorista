import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Tudo, menos API, arquivos internos do Next e arquivos com extensão (imagens, fontes, manifest).
  matcher: "/((?!api|trpc|_next|_vercel|.*\\..*).*)",
};
