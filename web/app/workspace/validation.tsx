"use client";
import { useState } from "react";

type TestRun = {exit_code:number; output:string};
export type ValidationResult = {status:string; message?:string; before?:TestRun; after?:TestRun};

export default function Validation({url, saved}: {url:string; saved?:ValidationResult}) {
  const [result,setResult]=useState(saved);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  async function validate() {
    setBusy(true); setError("");
    try {
      const response=await fetch(url+"?validate=1",{method:"POST"});
      if(!response.ok) throw Error(response.status===409?"Runner busy or patch unavailable.":"Runner unavailable. Retry after checking Compose.");
      setResult(await response.json());
    } catch(e) {setError(e instanceof Error?e.message:"Could not run tests.");}
    finally {setBusy(false);}
  }
  const labels: Record<string,string> = {passed:"Both checks passed",failed:"Patch failed validation",unapplied:"Patch could not be applied",inconclusive:"Baseline inconclusive",unavailable:"Release unavailable"};
  return <section><h3>Patch validation</h3>
    {(!result || ["unavailable","unapplied"].includes(result.status)) && <button disabled={busy} onClick={validate}>{busy?"Running checkout tests…":result?.status==="unapplied"?"Retry validation":"Validate patch"}</button>}
    <div aria-live="polite">{error && <p>{error}</p>}{result && <><strong>{labels[result.status] || result.status}</strong>
      {result.message && <p>{result.message}</p>}
      {(["before","after"] as const).map(stage=>{const run=result[stage];return run && <details key={stage} open><summary>{stage==="before"?"Before patch":"After patch"} · {run.exit_code===0?"Pass":"Fail"}</summary><pre style={{whiteSpace:"pre-wrap"}}>{run.output}</pre></details>;})}</>}</div></section>;
}
