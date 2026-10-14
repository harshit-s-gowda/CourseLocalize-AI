# CourseLocalize AI

Streamlit prototype for translating English technical course content into Indian languages while preserving code and lesson structure.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string
- `cd courselocalize-ai && python3.11 -m streamlit run app.py --server.address 0.0.0.0 --server.port 5000` — run CourseLocalize AI

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `courselocalize-ai/app.py` — Streamlit pages and user flows
- `courselocalize-ai/modules/` — text extraction, translation, preservation, quality checks, and history
- `courselocalize-ai/data/terminology.json` — editable terminology rules
- `courselocalize-ai/data/history.json` — local job history; ignored by Git because it contains course text

## Architecture decisions

- Keep this product in its requested Python/Streamlit stack; run it as a dedicated workflow rather than replacing it with a different frontend.
- Use official IndicTrans2 local inference as the primary translation path, with an explicit compatible endpoint option. Never fall back to fabricated translations.
- Keep successful history local in JSON for the prototype; do not store source content for failed jobs.

## Product

- Localize English technical lessons into Kannada, Hindi, Tamil, and Telugu.
- Preserve code, identifiers, configured terms, and Markdown course structure.
- Review and download translations, manage terminology, revisit history, and optionally calculate reference-based BLEU and chrF++ scores.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
