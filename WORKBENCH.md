# React financial research workbench

The workbench uses the existing FastAPI financial services and LangGraph
research workflow. FinancialReports remains an HTTP dependency owned by its
own project. Do not expose model/provider credentials to the browser.

## Local development

Install the Python dependencies with `uv sync --extra dev --frozen`.
Configure `.env` using `.env.example`. For a producer running on this host use
`FINANCIAL_REPORTS_BASE_URL=http://127.0.0.1:8010`; the `financial-reports` alias
in the example is intended for the Docker configuration. Local JSON can be
selected explicitly with `DATA_PROVIDER=json`.

Start the API:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL (normally http://localhost:5173). Its proxy forwards `/api`
and `/health` to FastAPI. The browser does not call FinancialReports directly.

## Container preview

```bash
docker compose up -d --build
```

Open http://localhost:8080. This starts the API and the workbench -- both are
in the base compose file now, so there is no overlay to remember. It does not
start the companion FinancialReports project. The web port binds to loopback.
API port exposure follows the base compose file.
Nginx serves the SPA and proxies API requests on the same origin.

This is a local preview configuration, not an authenticated multi-user
deployment. Do not publish it to an untrusted network without adding the
identity, authorization and request-control layer appropriate for that network.

## Result semantics

- Financial values are computed by Python services, not duplicated in React.
- `null` or unavailable fields must remain absent, never interpreted as zero.
- Money, percentage points, ratios and confidence use distinct display units.
- A response belongs to its submitted company, period and query. Editing form
  controls does not change the identity of an already displayed report.
- Research history stored in a browser is local history, not server persistence
  or model conversational memory. Export full responses for portability.
- Cancelling a browser request stops waiting; it does not promise cancellation
  of a running backend research workflow.

## Validation

Backend tests use fixtures and disable LLM/telemetry. The five producer smoke
tests additionally need a running FinancialReports API and seeded filings.
`python -m evaluation` explicitly disables external LLM/telemetry settings;
its citation metric checks presence/locatability, not claim correctness.

Run the Python gates from `REACT_MIGRATION_PLAN.md` and the frontend's build,
typecheck and test scripts before switching any existing deployment. The
Streamlit entrypoint it replaced has been removed; `git log -- ui streamlit_app.py`
is the record if any of it is ever needed again.
