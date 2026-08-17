# Service-Integrity Validation Test Procedure

## Event 2062 -> Event 2073 (Replay)

| Step | Procedure | U-M | Message | Parameter | Verdict |
|------|-----------|-----|---------|-----------|---------|
| 1 | The UE initiates the initial registration procedure. | → | REGISTRATION REQUEST | 5GS registration type = `"initial registration"` | – |
| 2 | The network accepts the registration, and the UE enters 5GMM-CONNECTED mode over 3GPP access. | ← | REGISTRATION ACCEPT | 5G-GUTI, TAI list, allowed NSSAI | – |
| 3 | The lower layers indicate that the RRC connection has been suspended. | ← | RRC Connection Suspend | RRC state = `RRC_INACTIVE` | – |
| 4 | The UE transitions to 5GMM-CONNECTED mode with RRC inactive indication. | – | – | 5GMM state = `5GMM-CONNECTED` with RRC inactive indication | – |
| 5 | A trigger occurs to update the UE radio capability, and the UE prepares a new registration. | – | – | `NG-RAN-RCU = "UE radio capability update needed"` | – |
| 6 | The UE moves to 5GMM-IDLE mode and initiates the registration procedure for mobility and periodic registration update. | → | REGISTRATION REQUEST | 5GS registration type = `"mobility registration updating"`;<br>5GS update type: `NG-RAN-RCU = 1` | – |
| 7 | The attacker captures the REGISTRATION REQUEST while it is transmitted toward the network. | → | Captured REGISTRATION REQUEST | Full NAS message captured | – |
| 8 | The attacker replays the captured REGISTRATION REQUEST toward the AMF. | → | REGISTRATION REQUEST (replayed) | Same captured message content | – |
| 9 | The AMF processes the replayed REGISTRATION REQUEST without sufficient authentication or verification. | – | – | Existing UE context affected | – |
| 10 | The replayed request causes the existing UE connection or registration context to be released, replaced, or disrupted. | – | – | UE registration context released, replaced, or disrupted | **Fail** |