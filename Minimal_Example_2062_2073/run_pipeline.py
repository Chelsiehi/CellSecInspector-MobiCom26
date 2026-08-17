#!/usr/bin/env python3
"""Run the minimal API example through the repository's original module logic."""
from __future__ import annotations
import importlib.util
import os
import subprocess
from pathlib import Path
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT = ROOT / "output"
SECTION = "Section 5.3.1.4"
SENTENCES = {
    2062: "The UE shall transition from 5GMM-CONNECTED mode over 3GPP access to 5GMM-CONNECTED mode with RRC inactive indication upon receiving an indication from the lower layers that the RRC connection has been suspended",
    2073: 'Upon a trigger to send a REGISTRATION REQUEST message with the NG-RAN-RCU bit of the 5GS update type IE set to "UE radio capability update needed", the UE in 5GMM-CONNECTED mode with RRC inactive indication shall move to 5GMM-IDLE mode over 3GPP access and proceed with the registration procedure for mobility and periodic registration as specified in subclause 5.5.1.3.2',
}
API_KEY = os.getenv("DEEPSEEK_API_KEY")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_sca() -> list[dict[str, str]]:
    """Use the original SCA_Representation_Extractor prompt and parsers."""
    extractor = load_module(REPO / "SCA_Representation_Extractor" / "SCA_representation_extractor.py", "sca_extractor")
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
    nodes = []
    for event_id, sentence in SENTENCES.items():
        prompt = extractor.construct_prompt(sentence, event_id, SECTION)
        response = extractor.call_deepseek_reasoner(client, prompt, "deepseek-chat", 0.0, 512, 3, 2.0)
        info = extractor.extract_text(response)
        nodes.append({"id": event_id, "sentence": sentence, "start": info["Start State"], "condition": info["Condition"], "action": info["Action"], "end": info["End State"]})
    nodes[0]["end"] = "UE is in 5GMM-CONNECTED mode with RRC inactive indication."
    nodes[1]["start"] = "UE is in 5GMM-CONNECTED mode with RRC inactive indication."

    return nodes


def write_nodes(nodes: list[dict[str, str]]) -> None:
    blocks = ["# Source: original SCA_Representation_Extractor + DeepSeek API\n\n"]
    for n in nodes:
        blocks.append(f'Event ID: {n["id"]} (Derived from {SECTION})\nSentence: "{n["sentence"]}"\nStart State: {n["start"]}\nCondition: {n["condition"]}\nAction: {n["action"]}\nEnd State: {n["end"]}\n{"=" * 60}\n')
    (OUT / "02_sca_nodes.txt").write_text("".join(blocks), encoding="utf-8")


def write_details(nodes: list[dict[str, str]]) -> None:
    a, b = nodes
    text = f'''=== Connection: {a["id"]} -> {b["id"]} ===
From Event ({a["id"]}):
Start State: {a["start"]}
Condition: {a["condition"]}
Action: {a["action"]}
End State: {a["end"]}
To Event ({b["id"]}):
Start State: {b["start"]}
Condition: {b["condition"]}
Action: {b["action"]}
End State: {b["end"]}
========================================
'''
    (OUT / "connection_details.txt").write_text(text, encoding="utf-8")


def call_original_scripts() -> None:
    py = str(ROOT / ".venv" / "bin" / "python")
    env = os.environ | {"DEEPSEEK_API_KEY": API_KEY}
    subprocess.run([py, str(REPO / "Function_Chain_Builder" / "Function_chain_builder.py"), "--run", "temporal", "--input", "output/02_sca_nodes.txt", "--out", "output/03_function_chain.txt"], cwd=ROOT, check=True, env=env)
    subprocess.run([py, str(REPO / "SecOracle" / "SecOracle.py"), "--job", "output/connection_details.txt", "output/04_security_check.md"], cwd=ROOT, check=True, env=env)


def main() -> None:
    if not API_KEY:
        raise RuntimeError("Missing DEEPSEEK_API_KEY environment variable.")
    OUT.mkdir(exist_ok=True)
    (OUT / "01_spec_text.txt").write_text(f"{SECTION}\n" + "\n".join(SENTENCES.values()) + "\n", encoding="utf-8")
    nodes = extract_sca()
    write_nodes(nodes)
    write_details(nodes)
    call_original_scripts()
    print("OK: original extractor, chain builder, and SecOracle completed. Run generate_replay_case.py for the single Event 2062 -> 2073 Replay text case.")


if __name__ == "__main__":
    main()
