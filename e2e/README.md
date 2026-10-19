# Wellstride browser tests (Playwright)

Drives the real web build in Microsoft Edge (already on Windows, nothing to download) at a phone size (390x844), plus a
desktop pass (1280x800) over the flows tagged `@desktop`. Ten flows, one test each (plus 1b: backend unreachable).

## Run on Windows
1. Docker Desktop running, then `docker start nutrimitra-mongo`.
2. Once: `cd e2e` then `npm install`. (Optional: `npm run install-browser` and set `E2E_BROWSER=chromium` to use Playwright's Chromium.)
3. `cd e2e` then `npm run e2e` (alias `yarn e2e` also works if you use yarn here).
   The first run builds the web app (a few minutes); later runs reuse `e2e/.web`. Force a rebuild with `set E2E_REBUILD=1`.

Everything starts and stops itself (`stack.py`): a fake AI server (port 8103), the backend (8101) on its own database
`wellstride_e2e` (dropped afterwards, with its throwaway users), and the static web build (8102). Your real database,
`backend/.env` and AI keys are never touched or printed; the AI providers are replaced by `fake_ai.py`, so runs are
deterministic and never hit real rate limits. Override ports with `E2E_API_PORT`, `E2E_WEB_PORT`, `E2E_AI_PORT`.

## Output
Screenshots: `e2e/screenshots/<phone|desktop>/<flow number>-<name>.png`. HTML report: `npm run report`.
Logs: `e2e/.logs`. All of these are git-ignored.
