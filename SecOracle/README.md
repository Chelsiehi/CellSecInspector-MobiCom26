# SecOracle

## Repository Contents

- `SecOracle.py`: main analysis script
- `security_analysis_results_4g.md`: example/generated 4G analysis output
- `security_analysis_results_5g.md`: example/generated 5G analysis output
- `security_analysis_results_rrc.md`: example/generated RRC analysis output
- `security_analysis_results_23.501.md`: example/generated TS 23.501 analysis output
- `security_analysis_results_24.229.md`: example/generated TS 24.229 analysis output

## What The Script Does

For each connection in an input file, the script evaluates four attack classes:

- `Inject`
- `Drop`
- `Modify`
- `Replay`


## Requirements

- Python 3.10+
- `openai`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## API Configuration

Set your DeepSeek API key before running:

```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

Optional environment variables:

```bash
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
```

## Usage

The script accepts one or more `--job` arguments. Each job is an input/output pair.

### Single file

```bash
python3 SecOracle.py \
  --job /path/to/connection_details.txt /path/to/security_analysis.md
```

### Multiple files

```bash
python3 SecOracle.py \
  --job ./connection_details_output_4g.txt ./security_analysis_results_4g.md \
  --job ./connection_details_output_5g.txt ./security_analysis_results_5g.md
```

### Optional runtime settings

```bash
python3 SecOracle.py \
  --job ./connection_details_output_24.229.txt ./security_analysis_results_24.229.md \
  --model deepseek-chat \
  --temperature 0.1 \
  --max-tokens 4096
```

## Input Format

The script expects a connection-detail text file containing blocks in a structure similar to:

```text
=== Connection: 12 -> 13 ===
From Event (...)
Start State: ...
Condition: ...
Action: ...
End State: ...
To Event (...)
Start State: ...
Condition: ...
Action: ...
End State: ...
========================================
```

## Output Format

The output is a Markdown table with one row per `(connection, attack_type)` pair.

Example structure:

```text
| From Event | To Event | Attack Type | Analysis |
| --- | --- | --- | --- |
| 12 | 13 | Inject | JSON analysis payload |
```