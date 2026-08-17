# SCA Representation Extractor

A Python script for extracting **SCA (Start State, Condition, Action, End State)** representations from technical specification sentences using the DeepSeek chat API.

## Overview

This project reads a plain-text input file where each non-empty line is treated as one sentence. For each sentence, it:

- detects section context when a line looks like a specification section heading
- sends the sentence to a DeepSeek reasoning model
- extracts the `Start State`, `Condition`, `Action`, and `End State` fields
- writes the normalized result to an output text file

The script is designed for specification-oriented text such as 3GPP protocol documents.


## Project Structure

```text
.
├── SCA_representation_extractor.py
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

## Requirements

- Python 3.10+
- A valid DeepSeek API key

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set your API key with an environment variable:

```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

Optional environment variables:

```bash
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-reasoner"
```

## Usage

```bash
python3 SCA_representation_extractor.py \
  --input /path/to/input.txt \
  --output /path/to/output.txt
```

Example with explicit API key:

```bash
python3 SCA_representation_extractor.py \
  --input ./data/processed_NAS_4G.txt \
  --output ./data/extracted_NAS_4G.txt \
  --api-key "$DEEPSEEK_API_KEY"
```

## Input Format

The input file should contain one sentence per line. Empty lines are ignored.

Example:

```text
4.1 General
The non-access stratum described in the present document forms the highest stratum of the control plane between UE and AMF.
If required by operator policy, the AMF shall include the NSSAI inclusion mode IE in the REGISTRATION ACCEPT message.
```

## Output Format

The output is written as plain text blocks in this format:

```text
Event ID: 1 (Derived from Section 4.1)
Sentence: "The non-access stratum described in the present document forms the highest stratum of the control plane between UE and AMF."
Start State: ...
Condition: ...
Action: ...
End State: ...
============================================================
```


