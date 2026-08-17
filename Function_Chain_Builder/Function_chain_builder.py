#!/usr/bin/env python3
"""Build temporal, semantic, causal, and reference-guided function chains.

The script consumes SCA event files and, depending on the selected mode, writes
candidate connections between events to a plain-text report.
"""

from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional

from openai import OpenAI
from tqdm import tqdm

BLOCK_SEPARATOR = "============================================================"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-reasoner"
DEFAULT_SIMILARITY_FILE = "./similarity.txt"
PLACEHOLDER_PREFIXES = (
    "not specified",
    "not explicitly",
    "unknown",
    "not applicable",
    "n/a",
)
REFERENCE_PATTERN = re.compile(
    r"(?:clause|subclause|section)\s+(\d+(?:\.\d+)+)",
    re.IGNORECASE,
)


@dataclass
class Node:
    """Parsed SCA node used for downstream connection analysis."""

    node_id: int
    section: str
    sentence: str
    start: str
    condition: str
    action: str
    end: str



def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Build function chains from SCA nodes.")
    parser.add_argument(
        "--run",
        choices=["temporal", "semantic", "causal", "reference", "all"],
        default="all",
        help="Connection type to build. Defaults to all.",
    )
    parser.add_argument("--input", required=True, help="Path to the SCA event file.")
    parser.add_argument(
        "--out",
        default="./function_chain_connections.txt",
        help="Path to the output report.",
    )
    parser.add_argument(
        "--similarity-file",
        default=DEFAULT_SIMILARITY_FILE,
        help="Path to the similarity report used by semantic/reference modes.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DEEPSEEK_API_KEY"),
        help="DeepSeek API key. Defaults to the DEEPSEEK_API_KEY environment variable.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        help=f"DeepSeek API base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
        help=f"Model used for semantic/causal/reference reasoning. Defaults to {DEFAULT_MODEL}.",
    )
    return parser.parse_args()



def validate_args(args: argparse.Namespace) -> None:
    """Validate file paths and required credentials before expensive work starts."""
    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")

    tasks = expand_tasks(args.run)
    if any(task in {"semantic", "reference"} for task in tasks):
        if not os.path.isfile(args.similarity_file):
            raise FileNotFoundError(
                f"Similarity file not found: {args.similarity_file}"
            )

    if any(task in {"semantic", "causal", "reference"} for task in tasks):
        if not args.api_key:
            raise ValueError(
                "Missing DeepSeek API key. Set DEEPSEEK_API_KEY or pass --api-key."
            )



def expand_tasks(run_mode: str) -> list[str]:
    """Expand the selected run mode into a concrete task list."""
    return [run_mode] if run_mode != "all" else ["temporal", "semantic", "causal", "reference"]



def read_field(block: str, label: str) -> str:
    """Extract a single line field from an SCA event block."""
    match = re.search(rf"{re.escape(label)}:\s*(.*)", block)
    return match.group(1).strip() if match else ""



def is_placeholder_text(text: str) -> bool:
    """Return True when the field has no useful protocol semantics."""
    normalized = text.strip().lower()
    return not normalized or normalized.startswith(PLACEHOLDER_PREFIXES)



def parse_nodes(file_path: str) -> list[Node]:
    """Parse all SCA event blocks from a text file."""
    with open(file_path, "r", encoding="utf-8") as input_file:
        data = input_file.read()

    nodes: list[Node] = []
    for raw_block in data.split(BLOCK_SEPARATOR):
        block = raw_block.strip()
        if not block:
            continue

        node_id_match = re.search(r"Event ID:\s*(\d+)", block)
        if not node_id_match:
            continue

        section_match = re.search(
            r"Derived from\s+(Section [0-9A-Za-z.]+|Unknown Section)",
            block,
        )
        sentence_match = re.search(r'Sentence:\s*"(.*)"', block)

        nodes.append(
            Node(
                node_id=int(node_id_match.group(1)),
                section=section_match.group(1) if section_match else "Unknown Section",
                sentence=sentence_match.group(1).strip() if sentence_match else "",
                start=read_field(block, "Start State"),
                condition=read_field(block, "Condition"),
                action=read_field(block, "Action"),
                end=read_field(block, "End State"),
            )
        )

    return nodes



def load_semantic_similarity(similarity_file: str) -> dict[tuple[int, int], float]:
    """Load End→Start cosine similarity scores from the similarity report.

    Keys are stored as `(source_event_id, target_event_id)` because the similarity
    script compares `source.end` to `target.start`.
    """
    similarity_map: dict[tuple[int, int], float] = {}
    current_source: Optional[int] = None
    current_target: Optional[int] = None

    with open(similarity_file, "r", encoding="utf-8") as input_file:
        for line in input_file:
            pair_match = re.search(r"E_j\s*=\s*(\d+)\s*.*E_i\s*=\s*(\d+)", line)
            if pair_match:
                current_source = int(pair_match.group(1))
                current_target = int(pair_match.group(2))
                continue

            score_match = re.search(r"End→Start\s*CosSim:\s*([0-9.]+)", line)
            if score_match and current_source is not None and current_target is not None:
                similarity_map[(current_source, current_target)] = float(score_match.group(1))

    print(f"[SIM] Loaded semantic edges: {len(similarity_map)}")
    return similarity_map



def build_client(api_key: str, base_url: str) -> OpenAI:
    """Create an OpenAI-compatible client configured for DeepSeek."""
    return OpenAI(api_key=api_key, base_url=base_url)



def request_reasoning_answer(
    client: OpenAI,
    model_name: str,
    prompt: str,
    temperature: float,
) -> str:
    """Send one reasoning prompt and return the model text response."""
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()



def initialize_output_file(output_path: str, input_path: str) -> None:
    """Reset the output file and write a short metadata header."""
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(f"# Function chain report\n")
        output_file.write(f"# Input: {input_path}\n\n")



def append_temporal_connections(nodes: list[Node], output_path: str) -> None:
    """Append exact End→Start matches as temporal edges."""
    print("[Temporal] Building temporal connections...")
    results: list[tuple[int, int, str]] = []
    progress_bar = tqdm(total=len(nodes) ** 2, desc="Temporal Linking", ncols=100)

    for source_node in nodes:
        for target_node in nodes:
            if source_node.node_id == target_node.node_id:
                progress_bar.update(1)
                continue

            if (
                source_node.end
                and target_node.start
                and source_node.end == target_node.start
                and not is_placeholder_text(source_node.end)
            ):
                results.append(
                    (source_node.node_id, target_node.node_id, source_node.end)
                )
            progress_bar.update(1)

    progress_bar.close()

    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write("==================== TEMPORAL CONNECTIONS ====================\n")
        if not results:
            output_file.write("# No temporal connections found\n\n")
            print("[Temporal] Done. No connections found.")
            return

        output_file.write("source_event_id\ttarget_event_id\tmatched_state\n")
        for source_id, target_id, matched_state in results:
            output_file.write(f"{source_id}\t{target_id}\t{matched_state}\n")
        output_file.write("\n")

    print(f"[Temporal] Done. Found {len(results)} connections.")



def append_semantic_connections(
    nodes: list[Node],
    output_path: str,
    similarity_map: dict[tuple[int, int], float],
    client: OpenAI,
    model_name: str,
) -> None:
    """Append LLM-judged semantic edges with similarity evidence when available."""
    print("[Semantic] Building semantic connections...")
    progress_bar = tqdm(total=len(nodes) ** 2, desc="Semantic Reasoning", ncols=100)

    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write("==================== SEMANTIC CONNECTIONS ====================\n")

        for source_node in nodes:
            for target_node in nodes:
                if source_node.node_id == target_node.node_id:
                    progress_bar.update(1)
                    continue

                similarity_score = similarity_map.get(
                    (source_node.node_id, target_node.node_id)
                )
                evidence = ""
                if similarity_score is not None:
                    evidence = (
                        "[SIMILARITY EVIDENCE]\n"
                        f"Semantic Similarity (End→Start) = {similarity_score:.4f}\n"
                        "Interpretation Rules:\n"
                        "- >0.50 -> likely same system state\n"
                        "- <=0.50 -> likely different\n\n"
                    )

                prompt = evidence + (
                    "[SEMANTIC TASK]\n"
                    "Determine whether source_node.end and target_node.start refer to the SAME system state.\n\n"
                    f"source_node END = \"{source_node.end}\"\n"
                    f"target_node START = \"{target_node.start}\"\n\n"
                    "Answer strictly:\n"
                    "Yes. [reason]\n"
                    "No. [reason]\n"
                )

                answer = request_reasoning_answer(
                    client=client,
                    model_name=model_name,
                    prompt=prompt,
                    temperature=0.1,
                )
                output_file.write(
                    f"E{source_node.node_id} -> E{target_node.node_id}: {answer}\n"
                )
                output_file.flush()
                progress_bar.update(1)

        output_file.write("\n")

    progress_bar.close()
    print("[Semantic] Done.")



def append_causal_connections(
    nodes: list[Node],
    output_path: str,
    client: OpenAI,
    model_name: str,
) -> None:
    """Append LLM-judged causal edges between every pair of nodes."""
    print("[Causal] Building causal connections...")
    progress_bar = tqdm(total=len(nodes) ** 2, desc="Causal Reasoning", ncols=100)

    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write("==================== CAUSAL CONNECTIONS ====================\n")

        for source_node in nodes:
            for target_node in nodes:
                if source_node.node_id == target_node.node_id:
                    progress_bar.update(1)
                    continue

                prompt = f"""
[CAUSAL TASK]
Determine whether source_node CAUSES target_node.

Definition:
source_node -> target_node if the source node's state, condition, or action logically enables or triggers the target node.

source_node (ID {source_node.node_id}):
  Start: {source_node.start}
  Condition: {source_node.condition}
  Action: {source_node.action}
  End: {source_node.end}

target_node (ID {target_node.node_id}):
  Start: {target_node.start}
  Condition: {target_node.condition}
  Action: {target_node.action}
  End: {target_node.end}

Important:
- Do NOT use similarity metrics.
- Judge ONLY based on protocol semantics.

Answer strictly:
Yes. [reason]
No. [reason]
"""

                answer = request_reasoning_answer(
                    client=client,
                    model_name=model_name,
                    prompt=prompt,
                    temperature=0.0,
                )
                output_file.write(
                    f"E{source_node.node_id} -> E{target_node.node_id}: {answer}\n"
                )
                output_file.flush()
                progress_bar.update(1)

        output_file.write("\n")

    progress_bar.close()
    print("[Causal] Done.")



def build_clause_index(nodes: Iterable[Node]) -> dict[str, list[Node]]:
    """Group nodes by section/clause identifier for reference-guided linking."""
    clause_to_nodes: dict[str, list[Node]] = defaultdict(list)
    for node in nodes:
        for clause in REFERENCE_PATTERN.findall(node.section):
            clause_to_nodes[clause].append(node)
    return clause_to_nodes



def append_reference_connections(
    nodes: list[Node],
    output_path: str,
    similarity_map: dict[tuple[int, int], float],
    client: OpenAI,
    model_name: str,
) -> None:
    """Append reference-guided edges based on clause/subclause mentions."""
    print("[Reference] Building reference-guided connections...")
    clause_to_nodes = build_clause_index(nodes)

    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write("==================== REFERENCE-GUIDED CONNECTIONS ====================\n")

        for source_node in tqdm(nodes, desc="Reference Linking", ncols=100):
            combined_text = " ".join(
                [
                    source_node.sentence,
                    source_node.start,
                    source_node.condition,
                    source_node.action,
                    source_node.end,
                ]
            )
            references = REFERENCE_PATTERN.findall(combined_text)
            if not references:
                continue

            for reference in references:
                for target_node in clause_to_nodes.get(reference, []):
                    if source_node.node_id == target_node.node_id:
                        continue

                    similarity_score = similarity_map.get(
                        (source_node.node_id, target_node.node_id)
                    )
                    temporal_match = source_node.end == target_node.start

                    evidence_lines = ["[REFERENCE EVIDENCE]"]
                    if temporal_match:
                        evidence_lines.append("- Temporal match: source_node.end == target_node.start")
                    if similarity_score is not None:
                        evidence_lines.append(
                            f"- State similarity: {similarity_score:.4f}"
                        )
                    evidence = "\n".join(evidence_lines) + "\n\n"

                    prompt = evidence + f"""
[REFERENCE TASK]
Determine whether ANY of the following connection types holds:
- Temporal: source_node.end == target_node.start
- Semantic: source_node.end ~= target_node.start
- Causal: source_node logically triggers target_node

source_node (ID {source_node.node_id}):
  Start: {source_node.start}
  Condition: {source_node.condition}
  Action: {source_node.action}
  End: {source_node.end}

target_node (ID {target_node.node_id}):
  Start: {target_node.start}
  Condition: {target_node.condition}
  Action: {target_node.action}
  End: {target_node.end}

Answer strictly:
Yes. [reason]
No. [reason]
"""

                    answer = request_reasoning_answer(
                        client=client,
                        model_name=model_name,
                        prompt=prompt,
                        temperature=0.0,
                    )
                    output_file.write(
                        f"E{source_node.node_id} -> E{target_node.node_id} | ref {reference}: {answer}\n"
                    )
                    output_file.flush()

        output_file.write("\n")

    print("[Reference] Done.")



def main() -> None:
    """CLI entry point."""
    args = parse_args()
    validate_args(args)
    tasks = expand_tasks(args.run)
    nodes = parse_nodes(args.input)
    initialize_output_file(args.out, args.input)

    similarity_map: dict[tuple[int, int], float] = {}
    if any(task in {"semantic", "reference"} for task in tasks):
        similarity_map = load_semantic_similarity(args.similarity_file)

    client: Optional[OpenAI] = None
    if any(task in {"semantic", "causal", "reference"} for task in tasks):
        client = build_client(args.api_key, args.base_url)

    if "temporal" in tasks:
        append_temporal_connections(nodes, args.out)

    if "semantic" in tasks:
        append_semantic_connections(nodes, args.out, similarity_map, client, args.model)

    if "causal" in tasks:
        append_causal_connections(nodes, args.out, client, args.model)

    if "reference" in tasks:
        append_reference_connections(nodes, args.out, similarity_map, client, args.model)

    print(f"[DONE] Output saved -> {args.out}")


if __name__ == "__main__":
    main()
