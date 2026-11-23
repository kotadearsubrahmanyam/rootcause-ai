import Incidents from "./incidents";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { options } from "../../lib/auth";

export default async function Workspace({ searchParams }: { searchParams: Promise<{ demo?: string, view?: string }> }) {
  const query = await searchParams;
  const guest = query.demo === "1";
  const session = guest ? null : await getServerSession(options);
  if (!guest && !session?.user) redirect("/");
  const tabs = ["Overview", "Incidents", "History"];
  const view = tabs.find(t => t.toLowerCase() === query.view) || "Overview";
  let project: { name: string } | null = null;
  try {
    const result = await fetch(process.env.API_URL + "/projects/demo", { cache: "no-store", signal: AbortSignal.timeout(3000) });
    if (result.ok) project = await result.json();
  } catch { /* Display the disconnected state below. */ }
  return <main className="workspace"><header><Link href="/">RootCause AI</Link>
    <nav aria-label="Workspace">{tabs.map(t => <Link key={t} aria-current={t === view ? "page" : undefined}
      href={`/workspace?${guest ? "demo=1&" : ""}view=${t.toLowerCase()}`}>{t}</Link>)}</nav>
    {guest ? <span>Guest</span> : <Link href="/api/auth/signout">Sign out</Link>}</header>
    <section className="glass panel"><small>{project?.name || "Project unavailable"}</small><h1>{view}</h1>
    {view === "Overview" ? <div className="grid"><article><h2>Project connection</h2><strong>{project ? "Connected" : "Unavailable"}</strong><p>{project ? "The API can read this project from PostgreSQL." : "Check the API and database connection."}</p></article>
    <article><h2>Application health</h2><strong>Awaiting telemetry</strong><p>Service health will appear after the first trace arrives.</p></article></div>
    : view === "Incidents" ? <Incidents/> : <article><h2>{view === "History" ? "No investigations yet" : "No incidents recorded"}</h2><p>{view === "History" ? "Completed investigations will appear here." : "Incidents will appear when the store sends failure data."}</p></article>}</section></main>;
}
