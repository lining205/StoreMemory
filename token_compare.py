#!/usr/bin/env python3
"""Measure StoreMemory prompt-token savings from Meko retrieval.

Compares, for three StoreMemory tasks, a full-context prompt containing the
whole synthetic dataset against a retrieval prompt containing only the Meko
memory snippets relevant to that task. Each retrieval is run three times and
averaged. Token counts use tiktoken cl100k_base when available; otherwise a
transparent regex fallback is used and named in the output.
"""

import json
import re
import statistics
from pathlib import Path

from meko_loop import DATA_PATH, memory_search

ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "token_compare_20261127.json"
OUT_MD = ROOT / "token_compare_20261127.md"
SYSTEM = (
    "You are a StoreMemory agent for a local store. Use only the supplied store "
    "context, cite the basis for each decision, do not promise diagnosis or "
    "outcomes, and recommend an in-person checkup for symptoms."
)

try:
    import tiktoken

    ENCODING = tiktoken.get_encoding("cl100k_base")
    TOKEN_METHOD = "tiktoken cl100k_base"

    def count_tokens(text):
        return len(ENCODING.encode(text))

except Exception:
    TOKEN_METHOD = "regex fallback (words and punctuation)"

    def count_tokens(text):
        return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


def dedupe_snippets(results, kinds, max_items):
    seen = set()
    snippets = []
    for item in results:
        kind = item.get("metadata", {}).get("kind")
        text = item.get("memory", "").strip()
        if kind not in kinds or not text or text in seen:
            continue
        seen.add(text)
        snippets.append(text)
        if len(snippets) >= max_items:
            break
    return snippets


def retrieved_prompt(task, query, kinds, max_items):
    results = memory_search(query, limit=50)
    snippets = dedupe_snippets(results, kinds, max_items)
    if not snippets:
        raise RuntimeError(f"No Meko snippets retrieved for query: {query}")
    context = "\n".join(f"- {s}" for s in snippets)
    return f"{SYSTEM}\n\nRetrieved Meko memory:\n{context}\n\nTask: {task}", snippets


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    full_context = json.dumps(data, ensure_ascii=False, indent=2)
    tasks = [
        {
            "name": "topic_recommendation",
            "task": "Recommend the next two short-video topics for PawCare Demo Clinic and cite the basis.",
            "query": "StoreMemory content performance views precise_customer_signals learning conclusion",
            "kinds": {"content_performance", "learning_conclusion"},
            "max_items": 6,
        },
        {
            "name": "copy_draft",
            "task": "Draft one short-video hook for the topic 'Why a cat hides after moving to a new home' under the store brand rules.",
            "query": "StoreMemory synthetic store profile brand rules diagnosis outcomes content performance",
            "kinds": {"store_profile", "content_performance"},
            "max_items": 3,
        },
        {
            "name": "review_conclusion",
            "task": "Review PawCare Demo Clinic content performance and write the learning conclusion for the next topic round.",
            "query": "StoreMemory content performance views precise_customer_signals lesson",
            "kinds": {"content_performance"},
            "max_items": 5,
        },
    ]

    rows = []
    for spec in tasks:
        full_prompt = f"{SYSTEM}\n\nFull synthetic store dataset:\n{full_context}\n\nTask: {spec['task']}"
        full_tokens = count_tokens(full_prompt)
        retrieved_counts = []
        snippet_counts = []
        for _ in range(3):
            prompt, snippets = retrieved_prompt(
                spec["task"], spec["query"], spec["kinds"], spec["max_items"]
            )
            retrieved_counts.append(count_tokens(prompt))
            snippet_counts.append(len(snippets))
        retrieved_tokens = round(statistics.mean(retrieved_counts), 2)
        saved = round(full_tokens - retrieved_tokens, 2)
        pct = round(saved / full_tokens * 100, 2) if full_tokens else 0
        rows.append(
            {
                "task": spec["name"],
                "full_tokens": full_tokens,
                "retrieved_tokens_runs": retrieved_counts,
                "retrieved_tokens_avg": retrieved_tokens,
                "snippet_counts": snippet_counts,
                "tokens_saved_avg": saved,
                "savings_pct": pct,
            }
        )
        print(
            f"{spec['name']}: full={full_tokens}, retrieved_avg={retrieved_tokens}, "
            f"saved={saved} ({pct}%), snippets={snippet_counts}"
        )

    avg_full = round(statistics.mean(r["full_tokens"] for r in rows), 2)
    avg_retrieved = round(statistics.mean(r["retrieved_tokens_avg"] for r in rows), 2)
    avg_saved = round(avg_full - avg_retrieved, 2)
    avg_pct = round(avg_saved / avg_full * 100, 2) if avg_full else 0
    result = {
        "token_method": TOKEN_METHOD,
        "runs_per_task": 3,
        "tasks": rows,
        "average": {
            "full_tokens": avg_full,
            "retrieved_tokens": avg_retrieved,
            "tokens_saved": avg_saved,
            "savings_pct": avg_pct,
        },
        "note": "Synthetic PawCare Demo Clinic data only. Full prompt contains the whole synthetic dataset; retrieved prompt contains Meko memory snippets filtered by metadata kind for the task.",
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(
        "# StoreMemory token comparison (2026-11-27)\n\n"
        f"Method: {TOKEN_METHOD}; three retrieval runs per task, averaged.\n\n"
        "| Task | Full tokens | Retrieved tokens (avg) | Saved | Savings |\n"
        "|---|---:|---:|---:|---:|\n"
        + "\n".join(
            f"| {r['task']} | {r['full_tokens']} | {r['retrieved_tokens_avg']} | {r['tokens_saved_avg']} | {r['savings_pct']}% |"
            for r in rows
        )
        + f"\n| **Average** | **{avg_full}** | **{avg_retrieved}** | **{avg_saved}** | **{avg_pct}%** |\n\n"
        "Synthetic PawCare Demo Clinic data only. The full prompt contains the whole synthetic dataset; "
        "the retrieved prompt contains Meko memory snippets filtered by metadata kind for the task.\n",
        encoding="utf-8",
    )
    print(f"\nAverage: full={avg_full}, retrieved={avg_retrieved}, saved={avg_saved} ({avg_pct}%)")
    print(f"Wrote {OUT_JSON.name} and {OUT_MD.name}")


if __name__ == "__main__":
    main()
