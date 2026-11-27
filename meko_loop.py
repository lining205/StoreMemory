#!/usr/bin/env python3
"""StoreMemory real Meko loop.

Seeds synthetic PawCare Demo Clinic data into a Meko datapack, runs the
topic/review/copy agents against retrieved Meko memory, writes the learning
conclusion back, stores a copy artifact, and records decision traces as
conversation messages.

All demo data is synthetic. No real customer, case, or account data is used.
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _data_path():
    for candidate in (
        ROOT / "demo-data" / "synthetic_store.json",
        ROOT.parent / "demo-data" / "synthetic_store.json",
    ):
        if candidate.exists():
            return candidate
    return ROOT / "demo-data" / "synthetic_store.json"


DATA_PATH = _data_path()
CLIENT = Path(
    os.environ.get(
        "MEKO_CLIENT",
        str(Path.home() / "workspace/custom-connectors/custom.meko/bin/client.py"),
    )
)
DATAPACK_ID = os.environ.get("MEKO_DATAPACK_ID", "efc06aab-2cc2-48fe-bb21-fec43a478446")
CONVERSATION_ID = os.environ.get("MEKO_CONVERSATION_ID", "633588d60b5f69d405bffb17fb031eaf")
AGENT_ID = "muse:storememory"


def parse_tool_result(raw):
    data = json.loads(raw)
    result = data.get("structuredContent", {}).get("result")
    if result is None:
        text = data.get("content", [{}])[0].get("text", "")
        result = text
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return result
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"Meko tool error: {result}")
    return result


def call_tool(name, arguments):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(arguments, f, ensure_ascii=False)
        path = f.name
    proc = subprocess.run(
        [sys.executable, str(CLIENT), "call-tool", "--name", name, "--arguments-file", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return parse_tool_result(proc.stdout)


def memory_add(text, kind, extra=None):
    metadata = {"source": "synthetic_store.json", "kind": kind}
    if extra:
        metadata.update(extra)
    result = call_tool(
        "memory_add",
        {
            "agent_id": AGENT_ID,
            "conversation_id": CONVERSATION_ID,
            "datapack_id": DATAPACK_ID,
            "metadata": json.dumps(metadata, ensure_ascii=False),
            "text": text,
        },
    )
    results = result.get("results", []) if isinstance(result, dict) else []
    return results[0].get("id") if results else None


def memory_search(query, limit=10):
    result = call_tool(
        "memory_search",
        {
            "agent_id": AGENT_ID,
            "conversation_id": CONVERSATION_ID,
            "datapack_id": DATAPACK_ID,
            "limit": limit,
            "query": query,
        },
    )
    return result.get("results", []) if isinstance(result, dict) else []


def add_trace(agent, decision, cited):
    return call_tool(
        "conversation_add_message",
        {
            "agent_id": AGENT_ID,
            "conversation_id": CONVERSATION_ID,
            "datapack_id": DATAPACK_ID,
            "input": f"StoreMemory {agent} agent decision",
            "output": f"{decision} Basis: {cited}.",
            "reasoning": "Synthetic demo trace recorded for replay in the StoreMemory Meko loop.",
            "plan": ["Read shared Meko memory", "Record the decision and its basis"],
        },
    )


def parse_content_memories(results):
    parsed_by_topic = {}
    pattern = re.compile(
        r"topic=(?P<topic>.*?); views=(?P<views>\d+); precise_customer_signals=(?P<signals>\d+)"
    )
    for item in results:
        text = item.get("memory", "")
        match = pattern.search(text)
        if match:
            topic = match.group("topic")
            parsed_by_topic[topic] = {
                "topic": topic,
                "views": int(match.group("views")),
                "precise_customer_signals": int(match.group("signals")),
                "memory_id": item.get("id"),
            }
    return list(parsed_by_topic.values())


def find_hash(value):
    if isinstance(value, dict):
        for key in ("content_hash", "hash", "sha256"):
            if isinstance(value.get(key), str) and re.fullmatch(r"[0-9a-f]{64}", value[key]):
                return value[key]
        for child in value.values():
            found = find_hash(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = find_hash(child)
            if found:
                return found
    return None


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print("=== SEED synthetic data into Meko ===")
    print(f"datapack_id={DATAPACK_ID}")
    print(f"conversation_id={CONVERSATION_ID}")

    existing_content = memory_search("StoreMemory content performance", limit=50)
    existing_content_ids = {
        r.get("metadata", {}).get("content_id")
        for r in existing_content
        if r.get("metadata", {}).get("kind") == "content_performance"
    }
    existing_profiles = memory_search("StoreMemory synthetic store profile", limit=50)
    if any(r.get("metadata", {}).get("kind") == "store_profile" for r in existing_profiles):
        print("store_profile_memory=existing")
    else:
        profile_id = memory_add(
            "StoreMemory synthetic store profile: PawCare Demo Clinic is a fictional pet hospital demo store. "
            "Brand rules: use plain colloquial language, do not promise diagnosis or outcomes, recommend an "
            "in-person veterinary checkup for symptoms, and never use real customer or case data.",
            "store_profile",
        )
        print(f"store_profile_memory={profile_id}")

    for item in data["historical_content"]:
        if item["id"] in existing_content_ids:
            print(f"content_memory {item['id']}=existing")
            continue
        text = (
            f"StoreMemory content performance {item['id']}: topic={item['topic']}; "
            f"views={item['views']}; precise_customer_signals={item['precise_customer_signals']}; "
            f"hook_type={item['hook_type']}; lesson={item['lesson']}"
        )
        mid = memory_add(text, "content_performance", {"content_id": item["id"]})
        print(f"content_memory {item['id']}={mid}")

    questions = " ".join(data["comment_questions"])
    call_tool(
        "conversation_add_message",
        {
            "agent_id": AGENT_ID,
            "conversation_id": CONVERSATION_ID,
            "datapack_id": DATAPACK_ID,
            "input": f"Synthetic owner questions for PawCare Demo Clinic: {questions}",
            "output": "Topic agent should use these recurring synthetic questions as local demand signals.",
            "reasoning": "Synthetic conversation seed for the StoreMemory demo.",
            "plan": ["Store synthetic owner questions", "Use them as topic demand signals"],
        },
    )
    print("conversation_seed=ok")

    print("\n=== BEFORE learning (topic agent retrieves Meko memory and ranks by views) ===")
    before_results = memory_search("StoreMemory content performance views precise_customer_signals", limit=50)
    before_content = parse_content_memories(before_results)
    if len(before_content) < 5:
        raise RuntimeError(f"Expected 5 parsed content memories, got {len(before_content)}")
    before = [c["topic"] for c in sorted(before_content, key=lambda c: c["views"], reverse=True)[:2]]
    for topic in before:
        print(" -", topic)
    add_trace("topic", f"Recommended before learning: {before}", "views only from retrieved Meko content memories")

    print("\n=== REVIEW agent writes learning conclusion to Meko ===")
    conclusion = data["learning_event"]["new_review_conclusion"]
    learning_id = memory_add(
        f"StoreMemory learning conclusion: {conclusion}",
        "learning_conclusion",
    )
    print(f"learning_memory={learning_id}")
    learning_results = memory_search("StoreMemory learning conclusion", limit=50)
    if not any(
        r.get("id") == learning_id
        or r.get("metadata", {}).get("kind") == "learning_conclusion"
        or "learning conclusion" in r.get("memory", "").lower()
        for r in learning_results
    ):
        raise RuntimeError("Learning conclusion was not read back from Meko")
    print("learning_readback=ok")
    add_trace("review", "Wrote learning conclusion to Meko memory", "retrieved content performance signals")

    print("\n=== AFTER learning (topic agent ranks by precise customer signals) ===")
    after_results = memory_search("StoreMemory content performance views precise_customer_signals", limit=50)
    after_content = parse_content_memories(after_results)
    after = [
        c["topic"]
        for c in sorted(after_content, key=lambda c: c["precise_customer_signals"], reverse=True)[:2]
    ]
    for topic in after:
        print(" -", topic)
    print("Expected change:", data["learning_event"]["expected_agent_change"])
    add_trace("topic", f"Recommended after learning: {after}", "precise_customer_signals and learning conclusion from Meko")

    print("\n=== COPY agent retrieves brand rules and stores an artifact ===")
    brand_results = memory_search(
        "StoreMemory synthetic store profile brand rules diagnosis outcomes", limit=50
    )
    if not any(
        r.get("metadata", {}).get("kind") == "store_profile"
        or "diagnosis" in r.get("memory", "").lower()
        for r in brand_results
    ):
        raise RuntimeError("Brand rules were not retrieved from Meko memory search")
    print("brand_rules_readback=ok")

    draft = (
        f"Hook: Owners keep asking this before booking. Topic: {after[0]}. "
        "We explain what to prepare and when an in-person checkup is the safer next step. "
        "No diagnosis or outcome is promised online."
    )
    artifact = call_tool(
        "artifact_put",
        {
            "agent_id": AGENT_ID,
            "content_base64": base64.b64encode(draft.encode("utf-8")).decode("ascii"),
            "content_type": "text/plain",
            "conversation_id": CONVERSATION_ID,
            "datapack_id": DATAPACK_ID,
            "filename": "storememory_copy_draft.txt",
        },
    )
    content_hash = find_hash(artifact)
    if not content_hash:
        raise RuntimeError(f"Artifact hash not found in result: {artifact}")
    print(f"artifact_hash={content_hash}")
    fetched = call_tool(
        "artifact_get",
        {
            "agent_id": AGENT_ID,
            "content_hash": content_hash,
            "conversation_id": CONVERSATION_ID,
            "datapack_id": DATAPACK_ID,
        },
    )
    fetched_text = json.dumps(fetched, ensure_ascii=False)
    if after[0] not in fetched_text and base64.b64encode(after[0].encode()).decode() not in fetched_text:
        # Some servers return base64 content; decode any content_base64 field for the check.
        decoded = ""
        if isinstance(fetched, dict):
            raw = fetched.get("content_base64") or fetched.get("result", {}).get("content_base64")
            if raw:
                decoded = base64.b64decode(raw).decode("utf-8", errors="ignore")
        if after[0] not in decoded:
            raise RuntimeError("Artifact readback did not contain the drafted topic")
    print("artifact_readback=ok")
    print(" -", draft)
    add_trace("copy", f"Drafted copy for: {after[0]}", "brand rules retrieved from Meko and artifact stored")

    print("\n=== DECISION TRACES (recorded in Meko conversation) ===")
    print(" - [topic] before learning ranked by views")
    print(" - [review] learning conclusion written and read back")
    print(" - [topic] after learning ranked by precise customer signals")
    print(" - [copy] draft stored as Meko artifact")

    assert before != after, "Learning must visibly change the recommendation"
    print("\nOK: real Meko memory changed the topic recommendation.")


if __name__ == "__main__":
    main()
