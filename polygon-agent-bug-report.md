# Bug Report: `wallet create` — Session creation fails with `{"error":"not found"}`

**Date:** 2026-03-11  
**CLI version:** `@polygonlabs/agent-cli` v0.2.2 (via npx)  
**OS:** Ubuntu 22.04 (Linux, x64)  
**Node.js:** v22.22.0  
**Chain:** Polygon mainnet (chainId: 137)

---

## Summary

`polygon-agent wallet create` consistently fails at the browser approval step with:

```
Connection failed: InitializationError: Session creation failed: 
Error: Wallet responded with error: {"error":"not found"}
```

This happens every time the user opens the `approvalUrl` and attempts to approve the session in the browser. The CLI times out after 300s.

---

## Steps to Reproduce

1. Agent has a valid existing setup (`~/.polygon-agent/builder.json` present with `accessKey`, `projectId: 48072`)
2. Run:
   ```bash
   export SEQUENCE_PROJECT_ACCESS_KEY=<accessKey>
   npx @polygonlabs/agent-cli wallet create --native-limit 5
   ```
3. CLI outputs a `approvalUrl` at `agentconnect.polygon.technology/link?rid=...`
4. User opens URL in browser immediately (within seconds of generation)
5. User connects wallet in the browser connector UI
6. Browser returns: `Connection failed: InitializationError: Session creation failed: Error: Wallet responded with error: {"error":"not found"}`
7. CLI eventually times out: `{"ok": false, "error": "Timed out waiting for callback (300s)"}`

---

## Context

- The wallet at `0x779560988ef176d8e4d9e3dfff6678474eebbcb4` was successfully created in a previous session (confirmed via `polygon-agent balances` → 0.5 POL balance visible)
- The **existing wallet session expired** (`polygon-agent send-native` returned: `Error: Explicit session has expired (deadline 1772830672). Re-link wallet to mint a fresh session.`)
- Attempted `wallet create` 3+ times with fresh URLs — same `{"error":"not found"}` each time
- Attempted `wallet remove` + `wallet create` (full local reset) — same error
- `callbackMode: tunnel` (cloudflared working, tunnel URL reachable)
- The approval URL is opened immediately, well within the 5-minute expiry window (`expiresAt` ~2h ahead)

---

## CLI Output (last run)

```json
{
  "ok": true,
  "walletName": "main",
  "chain": "polygon",
  "rid": "7iyNX1RTCna3Y_Rwe7nO5Q",
  "callbackMode": "tunnel",
  "expiresAt": "2026-03-11T16:53:39.358Z"
}
```

Browser error returned to user:
```
Connection failed: InitializationError: Session creation failed: 
Error: Wallet responded with error: {"error":"not found"}
```

CLI final output:
```json
{
  "ok": false,
  "error": "Timed out waiting for callback (300s)"
}
```

---

## Hypothesis

The Sequence Ecosystem Wallet returns `{"error":"not found"}` for the given `rid`. This may indicate:

1. The `rid` or project session is not being found server-side in the Sequence Builder registry (possibly a project key issue — `projectId: 48072`)
2. The wallet being used in the browser is not recognized for this project
3. A server-side session expiry or project deactivation on Sequence's end

The issue does **not** appear to be:
- Tunnel connectivity (cloudflared working, callback URL reachable)
- URL expiry (opened immediately after generation)
- Local file corruption (reproduced after full `wallet remove`)

---

## Environment

```
Project Access Key: AQAAAAAAALvIH0UTtqfkd4oFw9nbZzp538k (first 10 chars: AQAAAAAAAA)
Project ID: 48072
EOA Address: 0x96E478B165405145Db94ba9D09910a3f83e17fb9
Wallet Address (on-chain): 0x779560988ef176d8e4d9e3dfff6678474eebbcb4
Connector URL: https://agentconnect.polygon.technology/
```

---

## Request

Is there a way to re-link an existing wallet (`0x779...bcb4`) to a new session when `wallet create` consistently returns `{"error":"not found"}` from the browser wallet? Is this a known issue with expired projects or a Sequence server-side problem?
