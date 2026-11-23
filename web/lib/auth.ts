import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

export const googleReady = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET);
export const options: NextAuthOptions = {
  providers: googleReady ? [GoogleProvider({
    clientId: process.env.AUTH_GOOGLE_ID!,
    clientSecret: process.env.AUTH_GOOGLE_SECRET!,
  })] : [],
  session: { strategy: "jwt" },
};
