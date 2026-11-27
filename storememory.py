#!/usr/bin/env python3
"""StoreMemory MVP scaffold (local mock, no Meko key required).

Three agents (topic / copy / review) share one memory object that mirrors
the Meko datapack concepts used in the ContextCon design:
conversations, memory, knowledge, artifacts, decision traces, learning.

This mock exists so the closed loop can be verified before the real Meko
MCP connection (https://mcp.mekodata.ai/mcp) is wired in. Replace
MockMemory with the Meko client once the API key is available; agent logic
and the demo narrative stay the same.

All demo data is fully synthetic (PawCare Demo Clinic). No real customer,
case, or account data is used.
"""
import json
from pathlib import Path

def _data_path():
    here = Path(__file__).resolve().parent
    for candidate in (
        here / "demo-data" / "synthetic_store.json",
        here.parent / "demo-data" / "synthetic_store.json",
    ):
        if candidate.exists():
            return candidate
    return here / "demo-data" / "synthetic_store.json"


DATA_PATH = _data_path()


class MockMemory:
    """Stand-in for one Meko datapack. Swap for the real MCP client later."""

    def __init__(self, data):
        self.conversations = list(data["comment_questions"])
        self.memory = {
            "store": data["demo_store"],
            "brand_rules": data["brand_rules"],
            "learned_conclusions": [],
        }
        self.knowledge = list(data["historical_content"])
        self.artifacts = []
        self.decision_traces = []

    def trace(self, agent, decision, cited):
        self.decision_traces.append({"agent": agent, "decision": decision, "cited": cited})

    def learn(self, conclusion):
        self.memory["learned_conclusions"].append(conclusion)


def topic_agent(memory, use_learning):
    """Pick next topics. Before learning: rank by views (flawed).
    After learning: rank by precise local-customer signals."""
    if use_learning:
        ranked = sorted(memory.knowledge, key=lambda c: c["precise_customer_signals"], reverse=True)
        basis = "precise_customer_signals (learned)"
    else:
        ranked = sorted(memory.knowledge, key=lambda c: c["views"], reverse=True)
        basis = "views only (no learning yet)"
    picks = [c["topic"] for c in ranked[:2]]
    memory.trace("topic", f"Recommended: {picks}", basis)
    return picks


def review_agent(memory, learning_event):
    """Read performance, write the learning conclusion back to shared memory."""
    conclusion = learning_event["new_review_conclusion"]
    memory.learn(conclusion)
    memory.trace("review", "Wrote learning conclusion to shared memory", "historical_content signals")
    return conclusion


def copy_agent(memory, topic):
    """Draft copy under the brand rules stored in memory (no medical promises)."""
    rules = memory.memory["brand_rules"]
    draft = (
        f"Hook: Owners keep asking this before booking. Topic: {topic}. "
        "We explain what to prepare and when an in-person checkup is the safer next step. "
        "No diagnosis or outcome is promised online."
    )
    artifact = {"type": "copy_draft", "topic": topic, "text": draft, "rules_applied": rules}
    memory.artifacts.append(artifact)
    memory.trace("copy", f"Drafted copy for: {topic}", "brand_rules in memory")
    return artifact


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    memory = MockMemory(data)

    print("=== BEFORE learning (topic agent ranks by views) ===")
    before = topic_agent(memory, use_learning=False)
    for p in before:
        print(" -", p)

    print("\n=== REVIEW agent writes learning conclusion ===")
    print(" -", review_agent(memory, data["learning_event"]))

    print("\n=== AFTER learning (topic agent ranks by customer signals) ===")
    after = topic_agent(memory, use_learning=True)
    for p in after:
        print(" -", p)
    print("Expected change:", data["learning_event"]["expected_agent_change"])

    print("\n=== COPY agent drafts under stored brand rules ===")
    art = copy_agent(memory, after[0])
    print(" -", art["text"])

    print("\n=== DECISION TRACES (replay) ===")
    for t in memory.decision_traces:
        print(f" - [{t['agent']}] {t['decision']}  <- {t['cited']}")

    assert before != after, "Learning must visibly change the recommendation"
    print("\nOK: learning visibly changed the topic recommendation.")


if __name__ == "__main__":
    main()
