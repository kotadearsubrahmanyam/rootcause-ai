# RootCause AI

## Start locally on Windows

Install Docker Desktop with Linux containers. From this folder run:

```powershell
.\setup.ps1
docker compose up --build -d
```

Open http://localhost:3000 and select **Explore demo**. In Overview, **Connected** means Next.js fetched the seeded demo project from FastAPI and PostgreSQL. Incidents and History start empty. Only the web port is published. PostgreSQL uses a named volume.

## Explore a checkout failure

Start the Compose stack, open **Explore demo**, then **Incidents**, and select **Run demo checkout**. Select **Refresh evidence** after a moment. Each checkout calls Orders, which calls Inventory. The deployed Inventory returns `available_quantity` where Orders expects `quantity`. The panel displays the failed trace, statuses, recorded exception, and the diff from the two commits packaged in the demo image. Repeating the checkout increments the incident count and shows the latest trace.

Use Compose for this walkthrough. The standalone Windows web launcher supports login but needs a separately reachable API for incident evidence.

## Investigate with Groq

Add `GROQ_API_KEY` to the local root `.env` and run `docker compose up --build -d --wait`. Open Incidents, run checkout once on the rebuilt demo release, refresh evidence, and select **Investigate**. The worker sends demo evidence to Groq when requested. Expand each citation to inspect its source. History reopens the saved result. To reload a changed key, run `docker compose up -d worker`.

## Google login

Create a Google OAuth web application. Set the authorized JavaScript origin to `http://localhost:3000` and the redirect URI to `http://localhost:3000/api/auth/callback/google`. In the generated root `.env`, fill in `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET`. Keep the generated session secret. Run `docker compose up -d web` to reload the configuration, then choose **Continue with Google**. Signed-in users land in the demo workspace.

## Progress

| Phase | Status | Acceptance checkpoint |
| --- | --- | --- |
| 1 - Foundation | Complete | A fresh Compose start, guest dashboard and real Google sign-in |
| 2 - Evidence | Complete | A real failed request correlates with its deployed commit |
| 3 · AI investigator | Complete | Diagnosis cites logs and source lines |
| 4 · Patch validation | Planned | Same regression test runs before and after patch |
| 5 · Product workflow | Planned | History, graph and second project connection |
| 6 · Demo readiness | Planned | Three failure scenarios and recovery cases rehearsed |

### Phase 1 checklist

- [x] Add frontend, API, database, Compose and persistent volume.
- [x] Implement guest navigation, Google provider, and protected workspace entry.
- [x] Isolate local credentials from Git.
- [x] Verify Compose startup and guest navigation in GitHub Actions.
- [x] Verify Google login, session persistence and sign-out on localhost.
- [x] Set up the private repository and six phase tracking issues (#1 through #6).
