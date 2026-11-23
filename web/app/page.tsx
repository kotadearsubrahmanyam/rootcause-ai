import Link from "next/link";
import { googleReady } from "../lib/auth";
import LoginButton from "./login-button";
export const dynamic = "force-dynamic";

export default function Home() {
  return <main className="entry"><article className="glass login">
    <div className="mark" aria-hidden="true">⌁</div><h1>RootCause AI</h1>
    <p>Follow a software failure from its first trace to a tested fix.</p>
    <LoginButton ready={googleReady}/><Link className="action" href="/workspace?demo=1">Explore demo <span>↗</span></Link>
    {!googleReady && <small>Google sign-in is awaiting local setup.</small>}
  </article></main>;
}
