# StoreMemory — ContextCon: Remember Everything

One shared memory per local store. Topic, copy, and review agents read and
write the same Meko datapack, so what one agent learns, the next one uses —
no re-briefing the store rules every session.

- Theme: 04 Agentic marketing — Campaigns That Know the Customer
- Demo store: PawCare Demo Clinic (fully fictional; all demo data synthetic)
- Status: local demo verified; real Meko loop verified on the
  `StoreMemory PawCare Demo` datapack

## Run the local demo (no key, no dependencies)

```bash
python3 storememory.py
```

Expected output: the topic agent first recommends by views alone, the review
agent writes a learning conclusion into shared memory, and the topic agent's
recommendation visibly changes to preparation / symptom-to-checkup topics.
Copy drafting applies the brand rules stored in memory, and every decision
prints a replayable trace.

## Real Meko loop

`meko_loop.py` seeds the synthetic PawCare data into a Meko datapack,
retrieves content memories before and after the review agent writes its
learning conclusion, stores a copy draft as a Meko artifact, and records
decision traces in the Meko conversation.

The verified run used the Muse Meko connector client. To run it elsewhere,
point `MEKO_CLIENT` at an MCP client helper that exposes the same
`call-tool --name <tool> --arguments-file <json>` interface, and set:

```bash
export MEKO_DATAPACK_ID=<your datapack id>
export MEKO_CONVERSATION_ID=<your conversation id>
python3 meko_loop.py
```

Evidence from the verified run is in `results/demo_run_meko_20261127.log`.

## Token comparison

```bash
python3 -m pip install tiktoken
python3 token_compare.py
```

Measured result (`results/token_compare_20261127.md`): across three tasks,
retrieval prompts averaged 305.33 tokens versus 874.33 tokens for
full-dataset prompts — 65.08% fewer prompt tokens.

## How the three agents share memory

1. **Topic agent** reads the store profile, historical content performance,
   and recurring comment questions, then proposes topics with cited sources.
2. **Copy agent** drafts under the brand rules held in memory (plain
   language, no diagnosis or outcome promises, in-person checkup guidance)
   and stores each draft as an artifact.
3. **Review agent** records post-publish signals (booking/location
   questions = precise local-customer intent), concludes which hooks work,
   and writes that conclusion back so the next topic round changes.

## Meko usage mapped to the rubric

- conversations: operator dialogue and comment questions
- memory: store profile, brand rules, learned hook conclusions
- knowledge: services and FAQ knowledge base
- artifacts: versioned topics, drafts, and review reports
- decision traces: why each topic/copy choice was made, replayable
- learning: review conclusions change later recommendations (demo shows
  before vs after)

## Data notice

`demo-data/synthetic_store.json` is fully synthetic. The store, people,
metrics, and comments are fictional and must not be presented as real
customer or medical records.

## License

MIT
