import { revalidatePath } from "next/cache";

type Span = { service: string; status: number | string; duration_ms: number; message: string; events: Record<string, string>[] };
type Incident = { trace: string; revision: string; count: number; spans: Span[]; previous: string | null; diff: string | null };

export default async function Incidents() {
  const api = process.env.API_URL;
  let incidents: Incident[] | null = null;
  try {
    const response = await fetch(api + "/demo/incidents", { cache: "no-store" });
    if (response.ok) incidents = await response.json();
  } catch { /* Show the service connection state. */ }
  async function replay() {
    "use server";
    const response = await fetch(process.env.API_URL + "/demo/checkout", { method: "POST", signal: AbortSignal.timeout(12000) });
    if (!response.ok) throw new Error("The demo store could not be reached.");
    revalidatePath("/workspace");
  }
  return <><form action={replay}><button disabled={incidents === null}>Run demo checkout</button></form>
    <form><button formAction={async () => { "use server"; revalidatePath("/workspace"); }}>Refresh evidence</button></form>
    {incidents === null ? <p>Evidence service unavailable.</p> : !incidents.length ? <article><h2>No incidents recorded</h2><p>Run checkout, then refresh after telemetry arrives.</p></article> :
      incidents.map(i => <details key={i.revision} open><summary>Checkout failure · {i.count} affected requests</summary>
        <p>Latest trace <code>{i.trace}</code></p>
        {i.spans.map(s => <article key={s.service}><h2>{s.service} · HTTP {s.status} · {s.duration_ms} ms</h2><p>{s.message}</p>
          {s.events.map((event,index) => <pre key={index}>{event["exception.message"] || event.fields}</pre>)}</article>)}
        {i.diff && <><h2>Deployment change</h2><p><code>{i.previous?.slice(0,8)} → {i.revision.slice(0,8)}</code></p><pre style={{overflowX:"auto"}}>{i.diff}</pre></>}
      </details>)}</>;
}
