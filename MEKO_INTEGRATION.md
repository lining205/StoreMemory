# Meko integration — verified steps and remaining work

Verified against official Meko docs on 2026-11-26 (see project plan
`../项目方案_20261126.md`):

1. Log in at mekodata.ai and create a datapack.
2. Settings > API Keys > Generate API key (shown once; deliver via the
   secure link, never in chat).
3. MCP entry point: https://mcp.mekodata.ai/mcp
4. Free tier is metered; usage is visible under Settings > Usage.

## Remaining work now that the key is connected

- [x] Connect the MCP client and verify the default datapack with reads.
- [x] Write one synthetic memory and read it back against the PawCare datapack.
- [x] Run the topic/review/copy loop on real Meko memory with `meko_loop.py`,
      keeping the same decision-trace format.
- [x] Re-run the before/after learning demo on real Meko memory and keep
      `demo_run_meko_20261127.log` as demo evidence.
- [x] Measure the token comparison (full-context prompt vs retrieved
      snippets, 3 runs averaged). Result: `token_compare_20261127.md`
      (average 65.08% fewer prompt tokens with retrieval).
- [ ] Record any Meko API limits hit (quota, latency) for the presentation.

## Guardrails

- Synthetic data only; never load real customer, case, or account data.
- The key goes through the secure link into secure storage; it is never
  pasted into chat, code, or this repository.
