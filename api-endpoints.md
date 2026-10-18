# FreeLLMAPI — Public Access Details

OpenAI-compatible LLM proxy, publicly reachable (used by the Leon4gr45/hedge HF Space
and Horizon GitHub Actions — anything running off-tailnet).

## Endpoint
- **Public base URL:** `https://debian-devil.tail3f341b.ts.net/v1`
  (Tailscale Funnel :443 → host :80 → `desk_agent_20-caddy-1` Caddy, Host-routed to
  `100.98.105.55:5173`. Config: `/home/leon/development/desk_agent_2.0/Caddyfile`.)
- **Tailnet-only base URL:** `http://100.98.105.55:5173/v1`
- **API key:** `freellmapi-28c5d289998928c4bdbdaceab7c8c70f22487122a12a381b`
- Auth header: `Authorization: Bearer <key>`
- ⚠️ `proxyapi.qd.je` is NOT live (no public DNS) — do not use it.

## Models
- Must pass `model: "auto"` (router picks best) — arbitrary model names 400 with
  `model_not_found`. Other catalog ids: `fusion`, `kimi-k2.6`, … (GET `/v1/models`).
- Context window advertised: ~1,048,576.

## How the HF Space uses it (Leon4gr45/hedge)
Set as Space secrets/vars (both dexter's helmholtz provider and hedge-fund's openai provider):
- `HELMHOLTZ_BASE_URL = https://debian-devil.tail3f341b.ts.net/v1`
- `HELMHOLTZ_API_KEY  = <key>`
- `OPENAI_API_BASE    = https://debian-devil.tail3f341b.ts.net/v1`
- `OPENAI_API_KEY     = <key>`
- `DEXTER_DEFAULT_PROVIDER = helmholtz`, `DEXTER_DEFAULT_MODEL = helmholtz:auto`
- In the hedge-fund UI, pick OpenAI provider + model `auto`.

## Reliability
Depends on debian-devil (home server) + tailscaled + `desk_agent_20-caddy-1` + the
freellmapi container all being up. The server is thermally limited and idle sessions are
reaped — if the Space's LLM calls fail, check these are running.

_Saved 2026-07-07T08:10:47Z._
