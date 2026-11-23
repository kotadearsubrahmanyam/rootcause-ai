"use client";
import { useEffect, useState } from "react";

type Report = {cause:string; proposed_patch:string; uncertainty:string; evidence: Record<string, unknown>};
type Job = {status:string; steps:string[]; error?:string; result?:Report};

export default function Investigator({trace}: {trace:string}) {
  const [job,setJob] = useState<Job>({status:"loading",steps:[]});
  const [error,setError] = useState("");
  const url = "/api/investigations/" + trace;
  useEffect(() => {
    let active = true;
    fetch(url).then(r => {if (!r.ok) throw Error(); return r.json()}).then(data => {
      if(active) setJob(data);
    }).catch(() => {if(active) setError("Could not read the saved investigation. Refresh to reconnect.")});
    return () => {active=false};
  }, [url]);
  const running = ["queued","running"].includes(job.status);
  useEffect(() => {
    if(!running) return;
    const stream = new EventSource(url + "?events=1");
    stream.onmessage = event => {
      const next = JSON.parse(event.data) as Job;
      setJob(next); setError("");
      if(["done","failed"].includes(next.status)) stream.close();
    };
    stream.onerror = () => setError("Reconnecting to investigation progress…");
    return () => stream.close();
  }, [running,url]);
  async function start() {
    setError(""); setJob({status:"starting",steps:[]});
    try {
      const r = await fetch(url,{method:"POST"});
      if(!r.ok) throw Error(r.status===409 ? "Trace still arriving. Refresh evidence and retry." : "Could not start the investigation.");
      setJob({status:"queued",steps:[]});
    } catch(e) {
      setJob({status:"idle",steps:[]}); setError(e instanceof Error ? e.message : "Request failed.");
    }
  }
  return <article><h2>AI investigation</h2>
    {["idle","failed"].includes(job.status) && <button onClick={start}>{job.status==="failed"?"Retry investigation":"Investigate"}</button>}
    <div aria-live="polite">{running && <p>Investigating…</p>}{job.error && <p>{job.error}</p>}{error && <p>{error}</p>}</div>
    {job.steps.length>0 && <ol>{job.steps.map((s,i)=><li key={i}>{s}</li>)}</ol>}
    {job.result && <><h3>Probable cause</h3><p>{job.result.cause}</p>
      {Object.entries(job.result.evidence).map(([id,value])=><details key={id}><summary>{id}</summary><pre style={{whiteSpace:"pre-wrap"}}>{typeof value==="string"?value:JSON.stringify(value,null,2)}</pre></details>)}
      {job.result.uncertainty && <p>{job.result.uncertainty}</p>}
      {job.result.proposed_patch && <><h3>Proposed patch · untested</h3><pre style={{overflowX:"auto"}}>{job.result.proposed_patch}</pre></>}</>}
  </article>;
}
