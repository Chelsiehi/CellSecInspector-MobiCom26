# SCA Dataset Collection

This directory contains text-based **SCA (Start State, Condition, Action, End State)** representations extracted from 3GPP specifications.

## Overview

Each `.txt` file stores a sequence of SCA records. Every record corresponds to one sentence-level extraction result and is written in a plain-text block format.

The collection currently includes:

- `4G_NAS_SCA.txt`
- `5G_NAS_SCA.txt`
- `5G_RRC_SCA.txt`
- `TS23.501_SCA.txt`
- `TS24.229_SCA.txt`

## Data Format

Each event is stored as a block with the following fields:

```text
Event ID: <integer> (Derived from <section>)
Sentence: "<source sentence>"
Start State: <Representing the initial system state before the transition.>
Condition: <Denoting the triggering clause or prerequisite specified in the specification.>
Action: <Describing the operation mandated by the specification once the condition is satisfied.>
End State: <Indicating the resulting system state after the action is executed.>
============================================================
```

## Example

```text
Event ID: 5 (Derived from Section 4.1)
Sentence: "The non-access stratum (NAS) described in the present document forms the highest stratum of the control plane between UE and AMF ..."
Start State: UE and AMF are not explicitly connected at the NAS level.
Condition: UE needs to communicate with AMF using NAS procedures.
Action: Define NAS as the highest control plane layer and establish its role in UE-AMF interaction.
End State: NAS is identified as the highest control plane stratum for both 3GPP and non-3GPP access.
============================================================
```

## File Descriptions

- `4G_NAS_SCA.txt`: SCA representations derived from 4G NAS specification.
- `5G_NAS_SCA.txt`: SCA representations derived from 5G NAS specification.
- `5G_RRC_SCA.txt`: SCA representations derived from 5G RRC specification.
- `TS23.501_SCA.txt`: SCA representations associated with 3GPP TS 23.501 Setcion 6.
- `TS24.229_SCA.txt`: SCA representations associated with 3GPP TS 24.229 Section 4.

