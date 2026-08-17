# CellSecInspector Minimal API Example: Event 2062 -> 2073

This minimal example reproduces the CellSecInspector pipeline for two TS 24.501 Section 5.3.1.4 events. It uses DeepSeek API calls and reuses the repository's original module logic:

1. `SCA_Representation_Extractor` extracts SCA fields for Events 2062 and 2073.
2. `Function_Chain_Builder` finds the temporal connection `2062 -> 2073`.
3. `SecOracle` evaluates Inject, Drop, Modify, and Replay attacks.
4. `VulnTestGenerator` generates the Replay validation procedure.

## Prerequisites

The included `.venv` contains the required `openai` package. Running them sends real API requests and consumes API quota.

## Run

```bash
cd /home/test/deepseek/github/minimal_cellsecinspector_2062_2073

# Generate specification text, API SCA nodes, the original temporal chain,
# and original SecOracle results.
.venv/bin/python run_pipeline.py

# Generate the final Replay-only text case from SecOracle's Replay=Yes result.
.venv/bin/python generate_replay_case.py
```

## Outputs

The generated artifacts are stored in `output/`:

- `01_spec_text.txt` — the two specification sentences.
- `02_sca_nodes.txt` — Extracted SCA nodes.
- `03_function_chain.txt` — original Function Chain Builder temporal result: `2062 -> 2073`.
- `04_security_check.md` — original SecOracle  analysis for all four attack types.
- `05_text_case.md` — original VulnTestGenerator output.
- `connection_details.txt` — event context supplied to SecOracle and VulnTestGenerator.

