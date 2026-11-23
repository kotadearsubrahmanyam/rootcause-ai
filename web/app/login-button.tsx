"use client";
import { signIn } from "next-auth/react";

export default function LoginButton({ ready }: { ready: boolean }) {
  return <button disabled={!ready} onClick={() => signIn("google", { callbackUrl: "/workspace" })}>Continue with Google</button>;
}
