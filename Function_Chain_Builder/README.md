# Function Chain Builder

This file builds **function-chain connections** from SCA (Start State, Condition, Action, End State) event files.

It provides two main scripts:

- `cos_similarity.py`: computes pairwise semantic similarity scores between SCA fields
- `Function_chain_builder.py`: builds temporal, semantic, causal, and reference-guided connections between events

## Repository Contents

- `cos_similarity.py`: section-scoped similarity analysis for SCA events
- `Function_chain_builder.py`: end-to-end function-chain generation
- `function_chains_4G NAS.txt`: example/generated 4G NAS function-chain output
- `function_chains_5G NAS.txt`: example/generated 5G NAS function-chain output
- `function_chains_5G RRC.txt`: example/generated 5G RRC function-chain output
- `function_chains_TS23.501.txt`: example/generated TS 23.501 function-chain output
- `function_chains_TS24.229.txt`: example/generated TS 24.229 function-chain output

## Workflow

1. Start from an SCA event file produced by your upstream extractor.
2. Run `cos_similarity.py` to generate End→Start similarity scores.
3. Run `Function_chain_builder.py` to build one or more classes of event connections.

## Requirements

- Python 3.10+
- `torch`
- `transformers`
- `openai`
- `tqdm`

Optional:

- `bitsandbytes` if you want to use `--load-in-8bit`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## DeepSeek API Configuration

`Function_chain_builder.py` uses the DeepSeek API for semantic, causal, and reference-guided reasoning.

Set your API key before running:

```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

Optional environment variables:

```bash
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-reasoner"
```

## Usage

### 1. Compute similarity scores

```bash
python3 cos_similarity.py \
  --input /path/to/sca_events.txt \
  --output ./similarity.txt
```

Optional 8-bit loading:

```bash
python3 cos_similarity.py \
  --input /path/to/sca_events.txt \
  --output ./similarity.txt \
  --load-in-8bit
```

### 2. Build all function-chain connections

```bash
python3 Function_chain_builder.py \
  --input /path/to/sca_events.txt \
  --similarity-file ./similarity.txt \
  --out ./function_chain_connections.txt \
  --run all
```

### 3. Build a specific connection type

```bash
python3 Function_chain_builder.py \
  --input /path/to/sca_events.txt \
  --similarity-file ./similarity.txt \
  --out ./semantic_connections.txt \
  --run semantic
```

Available `--run` values:

- `temporal`
- `semantic`
- `causal`
- `reference`
- `all`

## Output Format

`cos_similarity.py` writes section-grouped pairwise scores such as:

```text
(E_j=12 → E_i=18)
   End→Start CosSim: 0.8421
   Cond→Cond CosSim: 0.1057
   Action→Action CosSim: 0.7334
```

`Function_chain_builder.py` writes labeled sections for each connection type, for example:

```text
==================== TEMPORAL CONNECTIONS ====================
source_event_id    target_event_id    matched_state
12                 18                 REGISTERED
```

