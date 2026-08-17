"""Compute pairwise cosine similarities between SCA event fields.

This script reads SCA event blocks from a text file, embeds the semantic fields of
those events with a Hugging Face causal language model, and writes pairwise
similarity scores grouped by section.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

BLOCK_SEPARATOR = "============================================================"
DEFAULT_MODEL_NAME = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
UNKNOWN_SECTION = "Unknown Section"
PLACEHOLDER_PREFIXES = (
    "not specified",
    "not explicitly",
    "unknown",
    "not applicable",
    "n/a",
)


@dataclass
class Event:
    """Structured representation of one SCA event block."""

    event_id: int
    section: str
    sentence: str
    start_state: str
    condition: str
    action: str
    end_state: str
    start_emb: Optional[torch.Tensor] = field(default=None, repr=False)
    end_emb: Optional[torch.Tensor] = field(default=None, repr=False)
    cond_emb: Optional[torch.Tensor] = field(default=None, repr=False)
    action_emb: Optional[torch.Tensor] = field(default=None, repr=False)



def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Compute pairwise cosine similarities for SCA event fields."
    )
    parser.add_argument("--input", required=True, help="Path to the SCA event file.")
    parser.add_argument(
        "--output",
        default="./similarity.txt",
        help="Path to the similarity report. Defaults to ./similarity.txt.",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
        help=f"Hugging Face model name. Defaults to {DEFAULT_MODEL_NAME}.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
        help="Maximum tokenized input length for each field.",
    )
    parser.add_argument(
        "--load-in-8bit",
        action="store_true",
        help="Load the model in 8-bit mode. Requires bitsandbytes support.",
    )
    return parser.parse_args()



def read_field(block: str, label: str) -> str:
    """Extract a single line field from an event block."""
    match = re.search(rf"{re.escape(label)}:\s*(.*)", block)
    return match.group(1).strip() if match else ""



def is_placeholder_text(text: str) -> bool:
    """Return True when a field does not carry usable semantic content."""
    normalized = text.strip().lower()
    return not normalized or normalized.startswith(PLACEHOLDER_PREFIXES)



def load_events(path: str) -> list[Event]:
    """Parse SCA event blocks from the input file."""
    with open(path, "r", encoding="utf-8") as input_file:
        text = input_file.read()

    events: list[Event] = []
    for raw_block in text.split(BLOCK_SEPARATOR):
        block = raw_block.strip()
        if not block:
            continue

        event_id_match = re.search(r"Event ID:\s*(\d+)", block)
        if not event_id_match:
            continue

        section_match = re.search(
            r"Derived from\s+(Section [0-9A-Za-z.]+|Unknown Section)",
            block,
        )
        sentence_match = re.search(r'Sentence:\s*"(.*)"', block)

        events.append(
            Event(
                event_id=int(event_id_match.group(1)),
                section=section_match.group(1) if section_match else UNKNOWN_SECTION,
                sentence=sentence_match.group(1).strip() if sentence_match else "",
                start_state=read_field(block, "Start State"),
                condition=read_field(block, "Condition"),
                action=read_field(block, "Action"),
                end_state=read_field(block, "End State"),
            )
        )

    return events



def embed_text(text: str, tokenizer, model, max_length: int) -> Optional[torch.Tensor]:
    """Embed one field by mean-pooling the final hidden state."""
    if is_placeholder_text(text):
        return None

    device = next(model.parameters()).device
    encoded = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )
    encoded = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
        outputs = model(**encoded, output_hidden_states=True)
        hidden_state = outputs.hidden_states[-1]
        pooled = hidden_state.mean(dim=1)

    return pooled.squeeze(0).detach().cpu()



def cosine_similarity(left: torch.Tensor, right: torch.Tensor) -> float:
    """Compute cosine similarity between two 1D embeddings."""
    return F.cosine_similarity(left.unsqueeze(0), right.unsqueeze(0)).item()



def group_events_by_section(events: list[Event]) -> dict[str, list[Event]]:
    """Group events so similarity is computed within the same section."""
    sections: dict[str, list[Event]] = {}
    for event in events:
        sections.setdefault(event.section, []).append(event)
    return sections



def compute_embeddings(
    sections: dict[str, list[Event]],
    tokenizer,
    model,
    max_length: int,
) -> None:
    """Compute and store embeddings for each event field."""
    for events in sections.values():
        for event in events:
            event.start_emb = embed_text(event.start_state, tokenizer, model, max_length)
            event.end_emb = embed_text(event.end_state, tokenizer, model, max_length)
            event.cond_emb = embed_text(event.condition, tokenizer, model, max_length)
            event.action_emb = embed_text(event.action, tokenizer, model, max_length)



def write_similarity_report(
    sections: dict[str, list[Event]],
    output_path: str,
) -> None:
    """Write pairwise similarity scores for all events in each section."""
    normalized_output_path = output_path.replace(" ", "_")
    with open(normalized_output_path, "w", encoding="utf-8") as output_file:
        for section, events in sections.items():
            output_file.write(f"\n============= {section} =============\n\n")

            for source_event in events:
                for target_event in events:
                    output_file.write(
                        f"(E_j={source_event.event_id} → E_i={target_event.event_id})\n"
                    )

                    if source_event.end_emb is not None and target_event.start_emb is not None:
                        score = cosine_similarity(source_event.end_emb, target_event.start_emb)
                        output_file.write(f"   End→Start CosSim: {score:.4f}\n")
                    else:
                        output_file.write("   End→Start CosSim: N/A\n")

                    if source_event.cond_emb is not None and target_event.cond_emb is not None:
                        score = cosine_similarity(source_event.cond_emb, target_event.cond_emb)
                        output_file.write(f"   Cond→Cond CosSim: {score:.4f}\n")
                    else:
                        output_file.write("   Cond→Cond CosSim: N/A\n")

                    if source_event.action_emb is not None and target_event.action_emb is not None:
                        score = cosine_similarity(source_event.action_emb, target_event.action_emb)
                        output_file.write(f"   Action→Action CosSim: {score:.4f}\n")
                    else:
                        output_file.write("   Action→Action CosSim: N/A\n")

                    output_file.write("\n")

    print(f"Done. Similarity report written to {normalized_output_path}")



def load_model_and_tokenizer(model_name: str, load_in_8bit: bool):
    """Load a tokenizer and causal LM for embedding extraction."""
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {"device_map": "auto"}
    if load_in_8bit:
        model_kwargs["load_in_8bit"] = True

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    model.eval()
    return model, tokenizer



def main() -> None:
    """CLI entry point."""
    args = parse_args()
    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")

    print(f"Loading events from {args.input} ...")
    events = load_events(args.input)
    print(f"Loaded {len(events)} events.")

    sections = group_events_by_section(events)
    print(f"Sections found: {len(sections)}")

    model, tokenizer = load_model_and_tokenizer(args.model_name, args.load_in_8bit)
    print("Computing embeddings...")
    compute_embeddings(sections, tokenizer, model, args.max_length)
    write_similarity_report(sections, args.output)


if __name__ == "__main__":
    main()
