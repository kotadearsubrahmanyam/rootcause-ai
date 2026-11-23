# RootCause AI prototype handover

**From Subbu to the Phase 5 and 6 developer · 24 November 2026**

Start by reproducing one verified fix on your laptop. A checkout should fail, the AI should explain which service broke the response contract, and the same checkout test should pass after its proposed patch. That working loop is the baseline for your changes. Four of six planned phases are complete. Phase 5 makes the workflow usable across two projects. Phase 6 proves it works across three kinds of failure.

[Private repository](https://github.com/kotadearsubrahmanyam/rootcause-ai) · [Verified Phase 4 baseline](https://github.com/kotadearsubrahmanyam/rootcause-ai/commit/9eb8080b220344259b356fb90fe17f998241240a) · [Phase 5 issue](https://github.com/kotadearsubrahmanyam/rootcause-ai/issues/5) · [Phase 6 issue](https://github.com/kotadearsubrahmanyam/rootcause-ai/issues/6)

## What you are taking over

| Phase | Status | What you can demonstrate |
| --- | --- | --- |
| 1 · Foundation | Complete | Start the stack with Compose, enter as a guest or sign in with Google, and load the seeded project from PostgreSQL. |
| 2 · Evidence | Complete | Trigger a real request across Checkout, Orders and Inventory. Inspect the shared trace, timings, HTTP results, exception and deployed Git diff. Repeated failures on a release increment its incident count. |
| 3 · Investigation | Complete | Request a Groq diagnosis, watch progress, expand its evidence citations, inspect the proposed diff and reopen the saved investigation in History. |
| 4 · Validation | Complete for the stock demo | Apply a supported proposal to a temporary copy of the matching release. Read pytest output from before and after. Subbu confirmed the working loop locally, and GitHub Actions passed on the baseline linked above. |
| 5 · Product workflow | Open · issue #5 | Integrate a health chart, service graph, evidence drawer and saved history. Connect a second FastAPI project. |
| 6 · Demo readiness | Open · issue #6 | Rehearse the field rename, a timeout and an incorrect total. Exercise missing evidence, a failed fix, a rate limit and first-time setup. |

The current workspace has basic health information, incident details and history. The broader product idea includes general log and metric analysis, arbitrary repositories and automated fixes. Today the evidence comes from instrumented demo services, and validation runs a supported patch against a packaged release. The live demo keeps its original failure so another person can reproduce it.

## The stack we actually use

| Layer | Implemented choice | Where to look |
| --- | --- | --- |
| Web and sign-in | Next.js 15 App Router, React 19, TypeScript, custom CSS, Node 22 container, NextAuth v4 with Google OAuth and guest entry | `web/package.json`, `web/app/workspace/`, `web/lib/auth.ts` |
| API and storage | Python 3.12, FastAPI, Uvicorn, HTTPX, psycopg, PostgreSQL 16. A named Docker volume persists evidence and investigations on each machine. | `api/main.py`, `api/evidence.py`, `api/investigations.py`, `compose.yaml` |
| AI worker | Groq Python SDK calling `openai/gpt-oss-120b` through Groq. The worker takes queued jobs from PostgreSQL, calls evidence tools and saves the structured result. Server-sent events stream progress to the UI. | `api/worker.py`, `web/app/workspace/investigator.tsx` |
| Telemetry and release evidence | OpenTelemetry spans exported over OTLP/HTTP to Collector 0.123.0. Each demo image packages a two-commit Git history used to identify the deployed code change. | `collector.yaml`, `demo/service.py`, `demo/Dockerfile` |
| Validation | Dedicated Python runner, temporary source copy, restricted diff and syntax checks, pytest and in-process HTTP responses for downstream services. | `demo/validation.py`, `demo/test_checkout.py` |
| Delivery and tracking | Docker Compose, private GitHub repository, six phase issues, README progress table and GitHub Actions. The workflow file still carries its original Phase 1 name and covers Phases 1–4. | `.github/workflows/phase1.yml`, `README.md` |

The graph and chart libraries remain implementation choices for Phase 5. Keep the existing top navigation, warm glass panels and readable evidence. Subbu specifically wants smooth feedback and no left sidebar. Use short transitions for opening evidence, switching views and updating results, and respect reduced-motion preferences.

## First run on a Windows laptop

| Get this | When you need it | Quick check |
| --- | --- | --- |
| Git for Windows and private repo access | To clone and contribute. Subbu grants access to your GitHub account. | `git --version` and a successful clone |
| WSL 2 and Docker Desktop with Linux containers | For the recommended Windows Compose setup. Start Docker Desktop before running the project. | `wsl --status`, `docker version` showing a Server section, `docker compose version` |
| A Groq API key and internet access | For a fresh live AI investigation. The first build also downloads dependencies and images. | Set `GROQ_API_KEY` in the local root `.env`. |
| Google OAuth web client | Only for testing Google sign-in. Guest entry is available for the demo. | Set the two Google values below. |
| Node.js 22 and npm | Optional for editing/building the web app directly on the host. The container already includes Node. | `node -v`, `npm -v` |
| Python 3.12 and an editor such as VS Code | Host Python is optional for running Python code outside Docker. Compose supplies Python, PostgreSQL, the Collector and pytest. | `py -3.12 --version` if developing outside Docker |

Downloads and setup guides: [Git for Windows](https://git-scm.com/download/win) · [WSL installation](https://learn.microsoft.com/windows/wsl/install) · [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) · [Node.js](https://nodejs.org/en/download) · [Groq keys](https://console.groq.com/keys).

1. On a Windows machine missing WSL, open PowerShell as administrator, run `wsl --install`, and restart if prompted. Install Docker Desktop, select the WSL 2 backend and start its Linux engine. Use ordinary PowerShell for the project commands.
2. From your chosen projects folder, run:

~~~powershell
git clone https://github.com/kotadearsubrahmanyam/rootcause-ai.git
cd rootcause-ai
.\setup.ps1
notepad .env
~~~

3. The setup script generates `NEXTAUTH_SECRET` and `POSTGRES_PASSWORD` for this machine. Fill in your own `GROQ_API_KEY`. For Google login, add `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET`. Register the exact JavaScript origin `http://localhost:3000` and redirect URI `http://localhost:3000/api/auth/callback/google`. Keep credentials in the ignored local file. The repository transfers code and tracking history. Each laptop builds its own database of traces.
4. Save the file, then start and inspect the stack:

~~~powershell
docker compose up --build -d --wait
docker compose ps
~~~

5. Open [the local app](http://localhost:3000). Choose **Explore demo → Incidents → Run demo checkout**. Wait for telemetry, choose **Refresh evidence**, then **Investigate** on the newest trace. Expand a citation and choose **Validate patch**. Reopen the result in **History**. With Google configured, separately check sign-in, refresh and sign-out.

## How to read a run

| Step | What the application does | What you should see |
| --- | --- | --- |
| Capture | Checkout calls Orders, which calls Inventory. Inventory returns HTTP 200 with `available_quantity`. Orders expects `quantity`, raises a KeyError and propagates HTTP 502 to Checkout. | All three services share one trace. Inventory can report success even though checkout failed. |
| Investigate | The worker reads the saved trace, compares the two releases and requests numbered inventory source lines for the captured revision. | A probable cause, clickable evidence and a proposed diff when supported by the evidence. |
| Validate | The runner checks the release and runs two tests before and after applying the diff to a temporary copy. | Before the patch, normal checkout fails and the missing-field regression check passes. A verified fix passes both tests afterward. |
| Reopen | The database stores the report and test outcomes. | The result remains available in History after refresh. |

**Reference incident.** On Subbu’s machine, trace `5d044571d36f453188972fa2d5cee28f` showed release `841833a3 → f14921e3`. The fix returned both field names from the same stock value. Earlier iterations exposed two runner problems: the model could invent a path such as `store/service.py`, and the runner rejected a valid local assignment `qty = 5`. The worker now checks proposed inventory paths and source context. The runner accepts the supported integer assignment, and an unapplied proposal can be retried. Your laptop will generate its own trace IDs.

## If the first run gets stuck

| Symptom | What to do |
| --- | --- |
| Docker cannot bind port 3000 | Use `Get-NetTCPConnection -LocalPort 3000 -State Listen` and `Get-Process -Id <PID>` to identify the owner. Close the conflicting app if appropriate, then rerun Compose. Keeping port 3000 preserves the registered OAuth URLs. |
| Google reports a redirect mismatch | Check the actual callback against the registered URI, including scheme, port and path. Use localhost consistently. After changing local OAuth values, run `docker compose up -d web`. |
| Missing key or rate limit | For a missing key, fill in the root environment file and run `docker compose up -d worker`. For a rate limit, wait and retry. Use the same saved report to view an existing diagnosis without another model call. |
| Release unavailable | The report belongs to another demo revision. Run a fresh checkout on the current stack, refresh evidence and investigate that trace. |
| Patch could not be applied or after-patch tests fail | Read the reason and the before/after outputs. Use **Retry validation** for an unapplied patch after a relevant runner update. A failed regression test is a real failed fix and should remain visible in History. |
| No evidence yet | Wait briefly and refresh. Check `docker compose ps` and `docker compose logs --tail=50 collector api worker`. For a routine shutdown use `docker compose down` to retain the named database volume. |

## How we track the work

The README gives the milestone status. Issues #1–#6 hold the phase checklists. GitHub Actions runs startup, navigation, evidence, investigation and validation checks. The database holds demo runs. Use GitHub for development progress and the app’s History for investigation results.

**Suggested handover routine.** Work on one phase branch at a time. Link its pull request to the relevant issue. In the issue, record completed items, a reproducible command or UI path, the CI run, a trace or screenshot, and anything still blocked. Update the README status only after the acceptance check passes. Keep secrets out of commits and screenshots. Finish #5 before starting #6.

## Phase 5 prompt to paste into your coding assistant

~~~text
Take over Phase 5 of the private RootCause AI repo. Read HANDOVER.md, README.md, issue #5, compose.yaml, api/evidence.py, api/investigations.py and the existing workspace views. First reproduce the Phase 4 checkout, diagnosis and validation flow. Record the baseline result.

Implement a project selector and connect a second instrumented FastAPI project. Give each project an explicit identity and scope its ingestion, incident queries, dashboard and history. The current receiver filters for demo.store and three specific service names, and the investigator expects checkout-specific evidence. Address these assumptions where needed. Make each project's supported investigation and validation capabilities clear in the UI.

Build a health chart from actual recorded requests and a dependency graph from observed trace relationships. Show the time range, empty states and downstream failures. Selecting a service or incident should open an evidence drawer with trace, release and citations. Reuse saved History so a reopened report shows the same evidence and validation outcome. Preserve top navigation, warm glass styling, keyboard access, reduced motion and smooth transitions.

Acceptance: generate real traffic in both projects. Switch between them and show that their charts, graph, incidents and saved history stay separate. Reopen a saved investigation after refresh. Re-run the original checkout validation and the existing CI checks. Update issue #5 and the README with the commands, results and any remaining limitations.
~~~

## Phase 6 prompt to paste after Phase 5 is accepted

~~~text
Take over Phase 6. Read HANDOVER.md, the accepted Phase 5 changes, issue #6 and the existing acceptance workflow. Start with a fresh clone and a separate Compose project and database so existing developer evidence is preserved. Follow the documented first-run instructions and record any missing step.

Keep the field-rename scenario. Add two repeatable scenarios: a downstream timeout and an incorrect order total. Give each a trigger, an expected failure, observable evidence, and a regression test defining correct behavior. For the incorrect total, demonstrate detection even when HTTP status is 200. Declare the demo timeout threshold and make the test deterministic. Extend source reading and validation only as needed for each supported scenario, while retaining release matching and isolation.

Exercise three recovery cases: incomplete evidence, a plausible patch that fails a regression test, and a provider rate limit. Simulate rate limiting for repeatable tests; verify the user sees an actionable state and can recover. Preserve the failed attempt and its output where applicable. Demonstrate one live Groq investigation separately from deterministic CI.

Deliver a short presenter script with the exact clicks, expected outcomes and reset steps, plus a results table for the three scenarios and three recovery cases. Rehearse from a clean setup, run CI, and record manual checks, known limitations and links in issue #6 and the README. Only mark the phase complete after another developer can follow the script.
~~~

**Final handback to Subbu.** Send the two phase PR links, CI results, a clean-machine startup result, the presenter script and the results table. Include one trace for each scenario and list any case that still requires a manual workaround.
