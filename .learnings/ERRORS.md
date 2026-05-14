# Errors

Command failures and integration errors.

---

## 2026-05-14 - pytest unavailable in local environment

- Command: `python -m pytest -q`
- Result: failed because the active Python environment does not have `pytest` installed.
- Fix: converted project tests to Python standard-library `unittest` so the initial project can be verified without external test dependencies.

## 2026-05-14 - tomllib unavailable in active Python

- Command: `python -m timepredict_agent --help`
- Result: failed because the active Python version does not provide `tomllib`.
- Fix: added a small TOML fallback parser for the project's simple `[agent]` config format.

## 2026-05-14 - arXiv HTTPS certificate verification failed

- Command: `python -m timepredict_agent collect --max-results 5 --recent-days 365`
- Result: failed with `SSLCertVerificationError` in the active Conda Python environment.
- Fix: switched the arXiv API endpoint to the official HTTP endpoint, then added a certificate-failure fallback because arXiv redirects HTTP to HTTPS in this environment.

## 2026-05-14 - arXiv public API rate-limited local validation

- Command: `python -m timepredict_agent collect --query "all:forecasting" --max-results 1 --recent-days 3650`
- Result: failed with `HTTP Error 429` from arXiv after repeated validation attempts.
- Fix: made CLI network failures concise and added offline parser/export tests so core behavior remains verifiable during public API throttling.

## 2026-05-14 - Browser plugin connection timed out during UI QA

- Tool: Browser runtime through Node REPL
- Result: two attempts to connect and open the local TimePredict UI timed out.
- Fix: switched to the Playwright MCP fallback for rendered UI verification and recorded the fallback reason.

## 2026-05-14 - Playwright fallback missing Chrome

- Tool: Playwright MCP
- Result: failed because Chrome was not found at `C:\Users\京康\AppData\Local\Google\Chrome\Application\chrome.exe`.
- Fix: continued with local HTTP/API and static JavaScript validation without installing browser dependencies.

## 2026-05-14 - Semantic Scholar public API rate-limited validation

- Command: `python -m timepredict_agent collect --sources semantic_scholar --query "time series forecasting" --max-results 3 --recent-days 3650`
- Result: Semantic Scholar returned `HTTP 429`.
- Fix: multi-source collection reports per-source errors without failing the whole run; users can set `SEMANTIC_SCHOLAR_API_KEY` for more reliable access.

## 2026-05-14 - PDF download error message was unclear

- Endpoint: `POST /api/papers/2605.13816v1/download`
- Result: failed with an empty-looking `PDF 下载失败：` message.
- Fix: improved exception formatting and added the same public-source certificate fallback used by arXiv metadata fetches.

## 2026-05-14 - LLM summary CLI printed traceback without token

- Command: `python -m timepredict_agent llm-summary 2605.13816v1`
- Result: correctly detected missing `ANTHROPIC_AUTH_TOKEN`, but exposed a traceback.
- Fix: CLI now exits with a concise user-facing error message for LLM runtime failures.

## 2026-05-14 - Local web refresh request aborted

- Endpoint: `POST /api/papers/2605.13816v1/local-summary`
- Result: PowerShell reported that the connection was aborted by the local host software, likely because the background web process exited.
- Fix: restart the local web service after code changes before re-testing UI endpoints.

## 2026-05-14 - Frontend app.js used smart quotes

- Symptom: Web UI stayed on `加载中` and paper counts stayed at zero.
- Command: `node --check timepredict_agent/static/app.js`
- Result: failed with `SyntaxError: Invalid or unexpected token` because `app.js` contained `“ ”` smart quotes in template markup.
- Fix: normalized smart quotes to standard ASCII quotes and re-ran `node --check`.
