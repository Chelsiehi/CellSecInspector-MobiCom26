# CellSecInspector

🌐 **Project Website:** Visit the [CellSecInspector project website](https://chelsiehi.github.io/CellSecInspector-MobiCom26/) for an overview of the system, its analysis pipeline, and key findings.

This is the official repository of the paper titled **“CellSecInspector: Safeguarding Cellular Networks via Automated Security Analysis on Specifications”** (ACM MobiCom ’26).

## Pipeline Overview

CellSecInspector follows a multi-stage workflow:

1. **SpecAdaptation**
   - Start from 3GPP specifications such as TS 24.501 version 16.8.0 Release 16, TS 24.301 version 16.8.0 Release 16, TS 38.331 version 17.0.0 Release 17, TS 23.501 version 20.0.0 Release 20, and TS 24.229 version 19.5.0 Release 19.

2. **SCA Representation Extractor**
   - Convert 3GPP specification sentences into structured **SCA nodes** with four fields:
     - `Start State`
     - `Condition`
     - `Action`
     - `End State`

3. **Function Chain Builder**
  - Connections:
    - Type I: Node-Informed Exhaustive Connection
    - Type II: Reference Guided Connection

4. **SecOracle**
  - Evaluates function chains under four attack models, including inject, drop, modify, and replay, using nine security properties.

5. **VulnTestGenerator**
   - Automatically generates test cases for candidate violations to guide validation experiments.

6. **Representation-level evaluation**
   - Compares SCA nodes with FSM-style intermediate representations from prior systems such as Hermes and ARCANE.

## Repository Structure

```text
├── 3GPP_Specification/
├── SpecAdaptation/
├── SCA_Representation_Extractor/
├── SCA/
├── Function_Chain_Builder/
├── SecOracle/
├── VulnTestGenerator/
├── SCA_nodes_vs._FSM_Evaluation/
├── Minimal_Example_2062_2073/
├── README.md
```

## Seven New Vulnerabilities
The following table summarizes the vulnerabilities detected by CellSecInspector.  
A total of 43 vulnerabilities were analyzed, among which 36 were previously reported, and 7* are newly discovered by CellSecInspector.

The following table compares vulnerabilities detected by Hermes (H) and CellSecInspector (C)

| ID | Attack | H | C |
|----|----------------------------------------------|----|----|
| 1 | Downgrade to non-LTE network services | ✅ | ✅ |
| 2 | Denying all network services | ✅ | ✅ |
| 3 | Denying selected service | ❌ | ✅ |
| 4 | Signaling DoS | ✅ | ✅ |
| 5 | S-TMSI catching | ✅ | ✅ |
| 6 | IMSI catching | ✅ | ✅ |
| 7 | EMM Information | ✅ | ✅ |
| 8 | Impersonation attack | ❌ | ✅ |
| 9 | Synchronization Failure attack | ❌ | ✅ |
| 10 | Malformed Identity Request | ❌ | ✅ |
| 11 | Neutralizing TMSI refreshment | ❌ | ✅ |
| 12 | NAS Counter Reset | ✅ | ✅ |
| 13 | Uplink NAS Counter Desynchronization | ✅ | ✅ |
| 14 | Exposing NAS Sequence Number | ✅ | ✅ |
| 15 | Cutting off the Device | ❌ | ✅ |
| 16 | Exposure of SQN | ✅ | ✅ |
| 17 | 5G AKA DoS Attack | ❌ | ✅ |
| 18 | SUCI catching | ❌ | ✅ |
| 19 | IMSI cracking | ❌ | ✅ |
| 20 | NAS COUNT update attack | ✅ | ✅ |
| 21 | Deletion of allowed CAG list | ✅ | ✅ |
| 22 | Downgrade using ATTACH/REGISTRATION REJECT | ❌ | ✅ |
| 23 | AUTHENTICATION REJECT attack | ❌ | ✅ |
| 24 | DETACH/DEREGISTRATION REQUEST attack | ❌ | ✅ |
| 25 | SERVICE REJECT attack | ❌ | ✅ |
| 26 | Denial-of-Service with RRC SETUP REQUEST attack | ❌ | ✅ |
| 27 | Installing Null Cipher and Null Integrity | ✅ | ✅ |
| 28 | Lullaby Attack | ✅ | ✅ |
| 29 | Incarceration with RRC REJECT/RELEASE | ❌ | ✅ |
| 30 | Measurement report | ❌ | ✅ |
| 31 | RLF report | ❌ | ✅ |
| 32 | Blind DoS attack | ❌ | ✅ |
| 33 | AKA bypass | ❌ | ✅ |
| 34 | Paging channel hijacking | ❌ | ✅ |
| 35 | Energy Depletion with RRC SETUP | ❌ | ✅ |
| 36 | V2X Message Spoofing over PC5 | ❌ | ✅ |

### Summary

| Tool | Detected | Missed |
|------|----------|--------|
| Hermes | 22 / 36 | 14 |
| CellSecInspector | **36 / 36** | **0** |

### Legend

- **H** – Detected by Hermes  
- **C** – Detected by CellSecInspector  
- ✅ – Vulnerability detected  
- ❌ – Vulnerability missed


The following table summarizes newly identified vulnerabilities discovered by **CellSecInspector** across different 3GPP specifications.

### Summary of New Vulnerabilities

| Spec | Vulnerability | Description | Validation Setup | Experimental Result | Root Cause |
|---|---|---|---|---|---|
| TS 24.501<br>v16.8.0 – v20.0.0<sup>†</sup> | **V1: Multi-USIM Problematic Reachability** | For MUSIM devices, active traffic on one SIM can prevent the other SIM from receiving paging, which an attacker can exploit to disrupt reachability. | U.S. carrier networks;<br>Samsung S24;<br>Samsung S21 | Repeated attacker calls to SIM1 prevented SIM2 from ringing across tested carrier combinations. | Specification and implementation gap for shared-transceiver MUSIM devices, where reliable paging monitoring for the inactive SIM is not guaranteed. |
| TS 24.501<br>v16.8.0 – v20.0.0<sup>†</sup> | **V2: Emergency Session Teardown via Forged Signaling to Victim** | Unprotected emergency REGISTRATION and SIP signaling enable MitM injection that terminates emergency sessions. | srsRAN/srsEPC with Linphone IMS with a controlled emergency session setup | Forged RRC RELEASE or SIP CANCEL terminated the victim’s emergency session. | A threefold design weakness in emergency services: unprotected emergency NAS messages, acceptance of unauthenticated RRC RELEASE, and unprotected SIP signaling. |
| TS 23.501<br>v16.8.0 – v20.2.0<sup>†</sup> | **V3: Vulnerable DNS-Based PLMN Discovery over Non-3GPP Access** | In non-3GPP access, an attacker can use forged DNS responses to redirect a UE to malicious infrastructure before any security context is established. | Controlled Wi-Fi network;<br>Samsung S24;<br>Moto G Stylus 5G | DNS poisoning blocked legitimate N3IWF/ePDG access and non-3GPP registration. | Unauthenticated DNS-based PLMN discovery over untrusted pre-attachment links enables network misdirection attacks. |
| TS 24.229<br>v16.8.0 – v20.0.0<sup>†</sup> | **V4: Privacy Exposure via Over-Disclosed VoIMS Signaling Headers** | Over-disclosed SIP and SDP headers expose device, user identity, and IMS infrastructure information during VoIMS signaling. | U.S. carrier networks;<br>Samsung S21;<br>Pixel 5 | SIP traces exposed private information. | The text-based SIP signaling design largely increases the risk of transmitting headers with private information. |
| TS 24.301<br>v16.8.0 – v20.0.0<sup>†</sup> | **V5: Exploitable CS-Fallback Initiation** | An attacker sniffs an unprotected extended service request and injects a forged SERVICE REJECT (with EMM cause 39 and T3442). It can trap the victim in a long throttling timer. | srsRAN/open5GS SDR testbed;<br>Samsung S24;<br>Moto G Stylus 5G | Devices accepted forged SERVICE REJECT and stopped CSFB call setup until T3442 expired. | Specifications allow SERVICE REJECT to be processed without ciphering or integrity protection as a fail-safe mechanism, enabling attackers to inject unauthenticated rejection messages. |
| TS 38.331<br>v17.0.0 – v19.3.0<sup>†</sup> | **V6: Access Trap via Access Barring Factor** | Rogue base station advertises restrictive `barringFactor` in SIB1/SIB2, causing UEs to suppress MO access attempts and refrain from initiating RRC connection establishment. | RF-shielded srsRAN, srsEPC testbed;<br>Samsung S24;<br>Moto G Stylus 5G | Devices self-blocked access after receiving SIB2 with `ac-BarringFactor` set to `0`. | UAC policies are broadcast via unauthenticated SIB messages before security is established, creating a pre-authentication trust gap. |
| TS 38.331<br>v17.0.0 – v19.3.0<sup>†</sup> | **V7: Rogue Base Station RRC RESUME Blackhole** | By exploiting unauthenticated RRC RESUME procedure, a rogue gNB traps the victim UE in a continuous loop of connection failures. | RF-shielded gNB setup;<br>Samsung S21;<br>Moto G Stylus 5G | Devices were attracted to the rogue gNB and repeatedly failed RRC RESUME. | Cell selection and reselection occur at the RRC layer before a protected AS channel is established, and the mechanism does not account for resume failures. |

<sup>†</sup> The latest 3GPP specification version available at the time of submission.

## Responsible Disclosure

We have responsibly disclosed all newly identified vulnerabilities to the following major stakeholders:

- **Android — ✅ confirmed the reported issues**  
- Samsung  
- 3GPP  
- **the GSMA Coordinated Vulnerability Disclosure (CVD) program  — ✅ confirmed the reported issues** 

Details of vulnerability confirmation and remediation will be updated later.


### Directory Guide

- `3GPP_Specification/`
  - Contains the 3GPP specification files and related source materials used by the pipeline.

- `SpecAdaptation/`
  - Contains specification preparation and adaptation utilities used by the broader pipeline.

- `SCA/`
  - Contains the extracted SCA datasets in text format.

- `SCA_Representation_Extractor/`
  - Contains scripts for transforming specification text into SCA nodes.

- `Function_Chain_Builder/`
  - Contains scripts for temporal, semantic, causal, and reference-guided linking between SCA nodes.

- `SecOracle/`
  - Contains scripts for performing security analysis over connected function chains.

- `VulnTestGenerator/`
  - Contains scripts for converting candidate violations into test cases.

- `SCA_nodes_vs._FSM_Evaluation/`
  - Contains the evaluation scripts for **RQ3** in the paper.
  - Compares SCA nodes with Hermes- and ARCANE-style FSM representations in terms of quantity, completeness, and accuracy.

- `Minimal_Example_2062_2073/`
   - Minimal example reproduces the CellSecInspector pipeline for two TS 24.501 Section 5.3.1.4 events.


## Minimal Artifact Path

A practical minimal path through the repository is:

1. Extract SCA nodes from specification text using `SCA_Representation_Extractor/`
2. Build function-chain connections using `Function_Chain_Builder/`
3. Run security analysis using `SecOracle/`
4. Generate validation procedures using `VulnTestGenerator/`

This path corresponds to the core CellSecInspector pipeline.



