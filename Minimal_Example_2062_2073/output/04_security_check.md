| 2062 | 2073 | Inject | BEGIN_JSON
{
"vulnerability_detected": "Yes",
"violated_requirements": [2, 12, 16, 44],
"explanation": "Injecting a forged UE-originated REGISTRATION REQUEST with the NG-RAN-RCU bit set could cause the AMF to process an unauthorized registration update before integrity protection is available, creating inconsistent registration-related state between the UE and the network.",
"issue_classification": "Protocol Design Issue",
"test_case": "Inject a spoofed UE-originated REGISTRATION REQUEST with NG-RAN-RCU=1 during the RRC inactive state.",
"vulnerability_source": "event2073"
}
END_JSON |
| 2062 | 2073 | Drop | BEGIN_JSON
{
"vulnerability_detected": "No",
"violated_requirements": [],
"explanation": "Dropping the relevant message may cause temporary connectivity loss, but the UE can recover through the standard registration procedure. Under this attack model, the dropped message does not by itself create a persistent state inconsistency or security bypass.",
"issue_classification": "N/A",
"test_case": "N/A",
"vulnerability_source": "unclear"
}
END_JSON |
| 2062 | 2073 | Modify | BEGIN_JSON
{
"vulnerability_detected": "Yes",
"violated_requirements": [2, 12, 16, 44],
"explanation": "Modifying a UE-originated REGISTRATION REQUEST, such as altering the NG-RAN-RCU bit, could cause the AMF to process an unintended registration update before integrity protection is available, creating inconsistent registration-related state and potential service disruption.",
"issue_classification": "Protocol Design Issue",
"test_case": "Modify a captured UE-originated REGISTRATION REQUEST by forging the NG-RAN-RCU bit during the RRC inactive state.",
"vulnerability_source": "event2073"
}
END_JSON |
| 2062 | 2073 | Replay | BEGIN_JSON
{
  "vulnerability_detected": "Yes",
  "violated_requirements": [5],
  "explanation": "A replay attack could target the REGISTRATION REQUEST message with the NG-RAN-RCU bit set, sent in Event 2073. By capturing and retransmitting this message, an attacker may cause the receiving AMF to process a stale duplicate if replay protection is not properly enforced. This violates the Replay Attack Protection requirement and may result in duplicate registration handling, signaling overhead, or other unintended network-side effects.",
  "issue_classification": "Protocol Design Issue",
  "test_case": "An attacker captures the REGISTRATION REQUEST message during the transition and retransmits it toward the network, causing duplicate registration handling or other unintended effects if stale requests are not properly rejected.",
  "vulnerability_source": "event2073"
}
END_JSON |