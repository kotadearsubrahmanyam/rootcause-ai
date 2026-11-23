import Investigator from "./investigator";

export default async function History() {
  let jobs: {trace:string;status:string}[];
  try {
    const response=await fetch(process.env.API_URL+"/investigations",{cache:"no-store"});
    if(!response.ok) throw Error();
    jobs=await response.json();
  } catch {
    return <p>Investigation history unavailable.</p>;
  }
  if(!jobs.length) return <article><h2>No investigations yet</h2><p>Start an investigation from an incident.</p></article>;
  return <>{jobs.map(j=><details key={j.trace}><summary>{j.trace} · {j.status}</summary><Investigator trace={j.trace}/></details>)}</>;
}
