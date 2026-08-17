const data = window.CSI_CONTENT;
const moduleDescriptions = { adapt: 'SpecAdaptation prepares the specification knowledge used by all downstream modules. It sanitizes collected 3GPP specifications while preserving clause numbers, cross-references, specification versions, and release identifiers. It then retrieves relevant normative evidence for each downstream reasoning task.' };

const nav = document.querySelector('.page-nav');
const navLinks = Array.from(document.querySelectorAll('.page-nav a'));
const sections = navLinks.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
function updateNavigation() {
  nav.classList.toggle('visible', window.scrollY > 320);
  const current = sections.filter(section => section.getBoundingClientRect().top < window.innerHeight * .38).pop();
  navLinks.forEach(link => link.classList.toggle('active', document.querySelector(link.getAttribute('href')) === current));
}
document.addEventListener('scroll', updateNavigation, { passive: true });
window.addEventListener('load', updateNavigation);

const moduleDetail = document.querySelector('#module-detail');
const scaSourceToField = { trigger: 'condition', action: 'action', timer: 'action', connection: 'action', reference: 'action' };
const scaFieldEvidence = { start: [], condition: ['trigger'], action: ['action', 'timer', 'connection', 'reference'], end: ['action', 'timer', 'connection', 'reference'] };
const chainNodes = {
  2110: { key: 'RRC resume moves the UE to 5GMM-CONNECTED', start: '5GMM-IDLE mode with suspend indication.', condition: 'Lower layers indicate that the RRC connection has resumed.', action: 'The UE transitions to 5GMM-CONNECTED mode.', end: '5GMM-CONNECTED mode.', clause: 'TS 24.501, 5G mobility management procedure' },
  2055: { key: 'Connected-mode transition with RRC inactive indication', start: '5GMM-CONNECTED mode.', condition: 'An RRC inactive indication is received.', action: 'The UE transitions to 5GMM-CONNECTED mode with RRC inactive indication.', end: '5GMM-CONNECTED mode with RRC inactive indication.', clause: 'TS 24.501, 5G mobility management procedure' },
  2093: { key: 'A transition within the 5G mobility management chain', start: 'See the source SCA node in the analyzed 5G mobility management chain.', condition: 'See the source SCA node.', action: 'See the source SCA node.', end: 'See the source SCA node.', clause: 'TS 24.501, 5G mobility management chain' },
  2724: { key: 'A transition within the 5G mobility management chain', start: 'See the source SCA node in the analyzed 5G mobility management chain.', condition: 'See the source SCA node.', action: 'See the source SCA node.', end: 'See the source SCA node.', clause: 'TS 24.501, 5G mobility management chain' },
  2062: { key: 'RRC suspension changes the UE context', start: 'UE is in 5GMM-CONNECTED mode over 3GPP access.', condition: 'Lower layers indicate that the RRC connection has been suspended.', action: 'The UE transitions to 5GMM-CONNECTED mode with RRC inactive indication.', end: 'UE is in 5GMM-CONNECTED mode with RRC inactive indication.', clause: 'TS 24.501 §5.3.1.4' },
  2073: { key: 'Radio capability update initiates registration', start: 'UE is in 5GMM-CONNECTED mode with RRC inactive indication.', condition: 'A trigger sends a REGISTRATION REQUEST with NG-RAN-RCU set to “UE radio capability update needed”.', action: 'The UE moves to 5GMM-IDLE and proceeds with mobility and periodic registration.', end: 'UE is in 5GMM-IDLE and has initiated registration.', clause: 'TS 24.501 §5.3.1.4; references §5.5.1.3.2' },
  5263: { key: 'Radio-capability change starts registration', start: 'Radio capability update context.', condition: 'Registration is triggered by a change in radio capability.', action: 'The UE initiates the registration procedure.', end: 'UE is in 5GMM-IDLE mode and has initiated registration.', clause: 'TS 24.501 §5.5.1.3.2' },
  2107: { key: 'Registration request is prepared and sent', start: 'UE is attempting to send a REGISTRATION REQUEST message.', condition: 'A registration procedure is underway.', action: 'The UE sends the registration request and continues the procedure.', end: 'UE continues the registration procedure in 5GMM-IDLE mode.', clause: 'TS 24.501, registration procedure' },
  2037: { key: 'Network-initiated common procedure is handled', start: 'An N1 NAS signalling connection is active and timer T3540 is running.', condition: 'A message for a network-initiated 5GMM common procedure is received.', action: 'The UE stops T3540 and responds using the existing N1 NAS signalling connection.', end: 'T3540 is stopped and the UE has responded to the procedure.', clause: 'TS 24.501 §5.4' }
};
const chainEdges = {
  '2110-2055': { type: 'Temporal Connection', reason: 'Node 2110 ends in exactly the 5GMM-CONNECTED state required to start Node 2055.', clause: 'TS 24.501, 5G mobility management procedure' },
  '5263-2107': { type: 'Semantic Connection', reason: 'The two descriptions use different wording but both represent initiating registration after a radio-capability update.', clause: 'TS 24.501, registration procedure' },
  '2073-2037': { type: 'Causal Connection', reason: 'Node 2073 establishes the signalling context that Node 2037 requires to receive and respond to the network-initiated procedure.', clause: 'TS 24.501 §5.3.1.4 and §5.4' },
  '2073-5263': { type: 'Reference-Guided Connection', reason: 'Node 2073 explicitly cites subclause 5.5.1.3.2; its registration action is then validated as causally preceding Node 5263.', clause: 'TS 24.501 §5.3.1.4 → §5.5.1.3.2' }
};
function chainPanel() {
  return `<p class="chain-intro">Function Chain Builder reconstructs complete cellular procedures from SCA nodes whose related behaviors are scattered across sentences, clauses, and references.</p><div class="chain-strategies"><article><span class="chain-number">TYPE I</span><h4>Node-Informed Exhaustive Connection</h4><p>Compares candidate SCA-node pairs to identify valid procedural dependencies.</p><div class="connection-types"><span><b>Temporal</b><small>Identical end and start states</small></span><span><b>Semantic</b><small>Different wording, equivalent state</small></span><span><b>Causal</b><small>One behavior enables another</small></span></div></article><article><span class="chain-number">TYPE II</span><h4>Reference Guided Connection</h4><p>Uses explicit 3GPP cross-references to focus the search before validating a relationship.</p><div class="reference-steps"><span>Detect reference</span><b>→</b><span>Retrieve candidate nodes</span><b>→</b><span>Validate connection</span></div></article></div><figure class="chain-paper-figure"><div class="chain-figure-label"><span>Worked example</span><b>5G mobility management function chain</b></div><img src="assets/function-chain-figure3.png?v=2" alt="Paper Figure 3: a 5G mobility management function chain showing temporal, semantic, causal, and reference-guided connections"><figcaption>Connected SCA nodes reveal temporal, semantic, causal, and reference-guided dependencies within one procedure.</figcaption></figure>`;
}
const securityProperties = {
  'Authentication': 'Checks whether participating entities can be reliably authenticated before security-relevant behavior is accepted.',
  'Authorization': 'Checks whether an entity is permitted to perform the requested operation in the current context.',
  'Service Integrity': 'Checks whether cellular services and their procedure state can be altered or triggered without sufficient protection.',
  'Service Confidentiality': 'Checks whether service-related information is protected from unauthorized disclosure.',
  'Privacy Protection': 'Checks whether procedure behavior exposes identifying or privacy-sensitive information.',
  'Network Availability & Signaling Security': 'Checks whether signaling manipulation can disrupt network availability or service reachability.',
  'Interworking Security': 'Checks security requirements that span interconnected networks or access technologies.',
  'Threat Detection & Logging': 'Checks whether security-relevant events can be detected and recorded for response.',
  'Regulatory Compliance': 'Checks whether procedure behavior is consistent with applicable security and privacy obligations.'
};
function secOraclePanel() {
  const propertyCards = Object.keys(securityProperties).map(property => `<article class="property-card"><b>${property}</b></article>`).join('');
  return `<div class="security-equation" aria-label="Security analysis relationship"><span>4 Adversarial Actions</span><b>×</b><span>9 Foundational Security Properties</span><b>→</b><strong>Candidate Violations</strong></div><section class="oracle-group"><p class="oracle-label">Adversarial actions</p><div class="attack-cards" aria-label="Four adversarial actions"><article><i aria-hidden="true">↓</i><h4>Dropping</h4><p>Suppress a message or event required by the procedure.</p></article><article><i aria-hidden="true">↯</i><h4>Modifying</h4><p>Alter message content or a procedure-relevant event.</p></article><article><i aria-hidden="true">＋</i><h4>Injecting</h4><p>Introduce a message or event not issued by the expected party.</p></article><article><i aria-hidden="true">↻</i><h4>Replaying</h4><p>Reuse a previously valid message or event in a new context.</p></article></div></section><section class="oracle-group"><p class="oracle-label">Foundational security properties</p><div class="property-grid" aria-label="Nine foundational security properties">${propertyCards}</div></section>`;
}
function vulnTestPanel() {
  return `<p class="test-intro">VulnTestGenerator narrows the gap between specification-level candidate violations and real-world validation. It focuses on generating test cases to guide these validation experiments.</p><div class="validation-bridge" aria-label="Validation test generation flow"><article><span>01</span><b>Candidate Violation</b><p>A security property is flagged on grounded specification behavior.</p></article><i aria-hidden="true">→</i><article><span>02</span><b>Structured Test Case</b><p>The candidate is translated into a practical validation procedure.</p></article><i aria-hidden="true">→</i><article><span>03</span><b>Expert Validation</b><p>Researchers execute and observe the procedure on a testbed or operational network.</p></article></div><div class="test-guidance"><p class="eyebrow">Validation guidance</p><p>Generated procedures specify the relevant network state, security-context status, UE and core-network configuration, operation sequence, and expected output so that experts can validate the candidate and identify its root cause.</p><p><strong>Scope.</strong> VulnTestGenerator generates guidance for validation experiments; automated execution remains future work.</p></div>`;
}
function selectModule(key) {
  if (!moduleDetail) return;
  const names = { adapt: 'SpecAdaptation', sca: 'SCA Representation Extractor', chain: 'Function Chain Builder', oracle: 'SecOracle', test: 'VulnTestGenerator' };
  const index = { adapt: '01', sca: '02', chain: '03', oracle: '04', test: '05' };
  const sca = `<div class="sca-demo">
      <article>
        <p class="eyebrow">Original TS 24.501 Text</p>
        <p class="sca-source">“<button class="evidence-trigger" data-sca="trigger">Upon receipt of a message of a network-initiated 5GMM common procedure</button>, the UE <button class="evidence-action" data-sca="action">shall stop timer</button> <button class="evidence-timer" data-sca="timer">T3540</button> <button class="evidence-action" data-sca="action">and respond to the network-initiated 5GMM common procedure</button> via <button class="evidence-connection" data-sca="connection">the existing N1 NAS signalling connection</button> <button class="evidence-reference" data-sca="reference">as specified in subclause 5.4</button>.”</p>
        <div class="sca-legend" aria-label="Evidence legend"><span class="evidence-trigger">Trigger Phrase</span><span class="evidence-action">Required Action</span><span class="evidence-timer">Timer</span><span class="evidence-connection">Connection Context</span><span class="evidence-reference">Cross-reference</span></div>
      </article>
      <div class="sca-arrow" aria-hidden="true"><b>→</b></div>
      <article>
        <p class="eyebrow">Structured SCA Node 2037</p>
        <button data-field="start"><b>Start State</b><span>UE has an active N1 NAS signalling connection and timer T3540 is running. <em>Inferred from contextual evidence.</em></span></button>
        <button data-field="condition"><b>Condition</b><span>Receipt of a message for a network-initiated 5GMM common procedure.</span></button>
        <button data-field="action"><b>Action</b><span>The UE stops timer T3540 and responds to the network-initiated 5GMM common procedure using the existing N1 NAS signalling connection as specified in subclause 5.4.</span></button>
        <button data-field="end"><b>End State</b><span>Timer T3540 is stopped, and the UE has responded to the network-initiated 5GMM common procedure via the N1 NAS signalling connection.</span></button>
      </article>
    </div>`;
  moduleDetail.innerHTML = `<h3>${names[key]}</h3>${key === 'adapt' ? `<div class="adapt-copy"><p>Retrieves release-specific 3GPP evidence to ground specification reasoning.</p><p>${moduleDescriptions[key]}</p></div>` : key === 'sca' ? sca : key === 'chain' ? chainPanel() : key === 'oracle' ? secOraclePanel() : key === 'test' ? vulnTestPanel() : ''}`;
  document.querySelectorAll('[data-module]').forEach(button => button.classList.toggle('active', button.dataset.module === key));
  if (key === 'sca') {
    moduleDetail.querySelectorAll('[data-sca]').forEach(element => {
      const reveal = () => highlightSca(element.dataset.sca);
      element.addEventListener('click', reveal);
      element.addEventListener('focus', reveal);
    });
    moduleDetail.querySelectorAll('[data-field]').forEach(element => {
      const reveal = () => highlightSca(element.dataset.field);
      element.addEventListener('click', reveal);
      element.addEventListener('focus', reveal);
    });
  }
}
function bindSecurityAnalysis() {
  const detail = moduleDetail.querySelector('.property-detail');
  moduleDetail.querySelectorAll('[data-property]').forEach(button => {
    const show = () => {
      const property = button.dataset.property;
      moduleDetail.querySelectorAll('[data-property]').forEach(item => {
        const active = item === button;
        item.classList.toggle('active', active);
        item.setAttribute('aria-expanded', String(active));
      });
      detail.innerHTML = `<p class="eyebrow">${property}</p><p>${securityProperties[property]}</p>`;
    };
    button.addEventListener('click', show);
    button.addEventListener('focus', show);
  });
}
function bindChainExplorer() {
  const inspector = moduleDetail.querySelector('.chain-inspector');
  const displayNode = id => {
    const node = chainNodes[id];
    moduleDetail.querySelectorAll('[data-chain-node],[data-chain-edge]').forEach(item => item.classList.toggle('active', item.dataset.chainNode === String(id)));
    inspector.innerHTML = `<p class="eyebrow">Node ${id}</p><p class="chain-key">${node.key}</p><dl><dt>Start State</dt><dd>${node.start}</dd><dt>Condition</dt><dd>${node.condition}</dd><dt>Action</dt><dd>${node.action}</dd><dt>End State</dt><dd>${node.end}</dd><dt>Specification Clause</dt><dd>${node.clause}</dd></dl>`;
  };
  const displayEdge = id => {
    const edge = chainEdges[id]; const [source, target] = id.split('-');
    moduleDetail.querySelectorAll('[data-chain-node],[data-chain-edge]').forEach(item => item.classList.toggle('active', item.dataset.chainEdge === id));
    inspector.innerHTML = `<p class="eyebrow">${edge.type}</p><dl><dt>Source Node</dt><dd>Node ${source}</dd><dt>Target Node</dt><dd>Node ${target}</dd><dt>Connection Type</dt><dd>${edge.type}</dd><dt>Why the connection is valid</dt><dd>${edge.reason}</dd><dt>Relevant clause or cross-reference</dt><dd>${edge.clause}</dd></dl>`;
  };
  moduleDetail.querySelectorAll('[data-chain-node]').forEach(item => {
    const show = () => displayNode(item.dataset.chainNode);
    item.addEventListener('click', show); item.addEventListener('focus', show);
    item.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); show(); } });
  });
  moduleDetail.querySelectorAll('[data-chain-edge]').forEach(item => {
    const show = () => displayEdge(item.dataset.chainEdge);
    item.addEventListener('click', show); item.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); show(); } });
  });
}
document.querySelectorAll('[data-module]').forEach(button => button.addEventListener('click', () => selectModule(button.dataset.module)));
document.querySelector('#module-flow')?.addEventListener('keydown', event => {
  if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
  const modules = Array.from(document.querySelectorAll('[data-module]'));
  const current = modules.indexOf(document.activeElement);
  if (current < 0) return;
  event.preventDefault();
  const next = modules[(current + (event.key === 'ArrowRight' ? 1 : -1) + modules.length) % modules.length];
  next.focus();
  selectModule(next.dataset.module);
});
selectModule('adapt');
function highlightSca(field) {
  const target = scaSourceToField[field] || field;
  const evidence = scaFieldEvidence[target] || [];
  moduleDetail?.querySelectorAll('[data-sca],[data-field]').forEach(el => {
    el.classList.toggle('active', evidence.includes(el.dataset.sca) || el.dataset.field === target);
  });
}
document.querySelectorAll('[data-sca]').forEach(el => { el.addEventListener('mouseenter', () => highlightSca(el.dataset.sca)); el.addEventListener('click', () => highlightSca(el.dataset.sca)); });
document.querySelectorAll('[data-field]').forEach(el => el.addEventListener('click', () => highlightSca(el.dataset.field)));

const walkPanel = document.querySelector('#walkthrough-panel');
const walkthroughStepNumbers = { source: '01', sca: '02', chain: '03', oracle: '04', test: '05' };
const walkthroughExplainers = {
  source: "CellSecInspector starts from the normative text and retains its source specification number, release/version, clause identifier, and cross-reference information. Here, the two events are both derived from TS 24.501 §5.3.1.4.",
  sca: "The SCA Representation Extractor maps each relevant specification sentence into an SCA node with four fields: <strong>start state</strong>, <strong>condition</strong>, <strong>action</strong>, and <strong>end state</strong>. Cross-references are retained verbatim in the most relevant field, including Event 2073’s reference to <code>subclause 5.5.1.3.2</code>.",
  chain: "The Function Chain Builder assembles scattered SCA nodes into complete cellular procedures through two strategies. <strong>Type I: Node-Informed Exhaustive Connection</strong> finds temporal, semantic, and causal links between nodes. <strong>Type II: Reference Guided Connection</strong> detects a cited subclause, retrieves candidate nodes from that clause, and then applies Type I to validate the link. In this example, Event 2062’s end state exactly matches Event 2073’s start state, forming a temporal connection.",
  oracle: "SecOracle evaluates every node and node transition in a function chain against <strong>nine core security properties</strong>, derived from cellular security standards and classic security models. It applies four adversarial methods, <strong>dropping, modifying, injecting, and replaying</strong>, and flags a <em>candidate violation</em> when a property no longer holds. A candidate still requires validation before it is treated as a vulnerability.",
  test: "VulnTestGenerator converts a candidate violation into a structured test case that specifies network state, security-context status, UE and core-network configuration, operation sequence, and expected output. The generated procedure guides validation of the violated security property in a controlled testbed or an operational network."
};
function showWalk(key) {
  const w = data.walkthrough[key];
  let body = `<header class="walk-header"><span>STEP ${walkthroughStepNumbers[key]}</span><h3>${w.title}</h3></header>`;
  const explainer = walkthroughExplainers[key] || w.explainer;
  if (explainer) body += `<p class="step-explainer">${explainer}</p>`;
  if (w.body) body += `<p class="walk-result">${w.body}</p>`;
  if (w.quote) body += `<blockquote>${w.quote}</blockquote>`;
  if (w.meta) body += `<p class="meta">${w.meta}</p>`;
  if (w.events) body += `<div class="node-grid">${w.events.map(event => `<article class="node"><span>Event ${event.id}</span><dl><dt>Sentence</dt><dd>${event.summary}</dd></dl></article>`).join('')}</div>`;
  if (w.nodes) body += `<div class="node-grid">${w.nodes.map(n => `<article class="node"><span>Event ID: ${n.id}</span><dl><dt>Start state</dt><dd>${n.start}</dd><dt>Condition</dt><dd>${n.condition}</dd><dt>Action</dt><dd>${n.action}</dd><dt>End state</dt><dd>${n.end}</dd></dl></article>`).join('')}</div>`;
  if (w.testCase) body += `<div class="table-wrap"><table><thead><tr><th>Step</th><th>Procedure</th><th>U–M</th><th>Message</th><th>Parameter</th><th>Verdict</th></tr></thead><tbody>${w.testCase.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  walkPanel.innerHTML = body;
}
document.querySelectorAll('[data-step]').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('[data-step]').forEach(x => x.classList.toggle('active', x === b)); showWalk(b.dataset.step); }));
showWalk('source');

const grid = document.querySelector('#findings-grid');
function attackFigure(f) { const number = Number(f.id.slice(1)); return `<figure class="finding-figure"><img src="assets/finding-v${number}.png" alt="Attack flow for ${f.title}"></figure>`; }
function renderFindings(spec = 'all') { grid.innerHTML = data.findings.filter(f => spec === 'all' || f.spec === spec).map(f => `<details class="finding"><summary aria-expanded="false"><span class="badge">${f.id}</span><span class="finding-summary"><small>${f.spec}</small><h3>${f.title}</h3><p>${f.impact}</p></span><span class="plus">+</span></summary><div class="finding-body"><dl><dt>Description</dt><dd>${f.description}</dd><dt>Impact</dt><dd>${f.impact}</dd></dl>${attackFigure(f)}<dl><dt>Validation Setup</dt><dd>${f.validation}</dd><dt>Observed Result</dt><dd>${f.result}</dd><dt>Root Cause</dt><dd>${f.root}</dd></dl></div></details>`).join(''); document.querySelectorAll('.finding').forEach(item => item.addEventListener('toggle', () => item.querySelector('summary').setAttribute('aria-expanded', String(item.open)))); }
document.querySelectorAll('[data-spec]').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('[data-spec]').forEach(item => item.classList.toggle('active', item === button)); renderFindings(button.dataset.spec); }));
renderFindings();

const comparisonBody = document.querySelector('#comparison-body'), compareFilter = document.querySelector('#comparison-filter'), compareCount = document.querySelector('#comparison-count');
const rqGrid = document.querySelector('.rq-grid');
if (rqGrid) { const detail = document.createElement('article'); detail.className = 'rq-detail'; detail.hidden = true; rqGrid.after(detail); const details = ["43 confirmed vulnerabilities: 36 previously reported and 7 previously unreported findings.", "Hermes detected 22 of 36 known vulnerabilities (61.1%); CellSecInspector detected 36 of 36 (100%).", "", "Candidate conversion is a lower-bound filtering rate: duplicates, implementation-dependent, and currently unverifiable candidates are excluded before confirmation.", "Reference-guided analysis reduces estimated TS 24.501 chain construction from 18.78 years to 60 days; semantic and causal connections account for approximately 99% of builder runtime."]; const rq2 = `<p>Hermes is the closest comparable specification-analysis system. CellSecInspector covered all 36 known specification-level vulnerabilities in the benchmark, while Hermes detected 22.</p><div class="rq2-bars"><div><b>Hermes</b><span>22 / 36 · 61.1%</span><i style="width:61.1%"></i></div><div><b>CellSecInspector</b><span>36 / 36 · 100%</span><i style="width:100%"></i></div></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>Known vulnerability</th><th>Hermes</th><th>CellSecInspector</th></tr></thead><tbody>${data.comparison.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2] ? 'Detected' : 'Missed'}</td><td>Detected</td></tr>`).join('')}</tbody></table></div>`; const rq3 = `<div class="rq-tabs"><button data-rq3="quantity">Quantity</button><button data-rq3="completeness">Completeness</button><button data-rq3="accuracy">Accuracy</button><button data-rq3="example">SCA vs. FSM Example</button></div><div id="rq3-content"></div>`; const rq3Views={quantity:`<p>SCA captures substantially more start and end states. Hermes reports more conditions and actions in some specifications because closely connected elements may be split into independent entries; raw quantity alone therefore does not measure structural completeness.</p><table><tr><th>Field</th><th>5G NAS (H/A/C)</th><th>5G RRC (H/A/C)</th><th>4G NAS (H/A/C)</th></tr><tr><td>Start State</td><td>55 / 98 / 6696</td><td>68 / 30 / 862</td><td>48 / 99 / 4999</td></tr><tr><td>Condition</td><td>10079 / 98 / 8611</td><td>3995 / 30 / 863</td><td>9754 / 99 / 6195</td></tr><tr><td>Action</td><td>5616 / 98 / 8616</td><td>3336 / 30 / 874</td><td>5643 / 99 / 6212</td></tr><tr><td>End State</td><td>349 / 98 / 8487</td><td>9 / 30 / 859</td><td>318 / 99 / 6169</td></tr></table>`,completeness:`<p>A transition is fully specified when all four fields are present and are not placeholders.</p><table><tr><th>Specification</th><th>CellSecInspector</th><th>Hermes</th><th>ARCANE</th></tr><tr><td>TS 24.501</td><td>6549 · 62.9%</td><td>5 · 0.1%</td><td>98 · 100%</td></tr><tr><td>TS 38.331</td><td>855 · 71.5%</td><td>0 · 0.0%</td><td>30 · 100%</td></tr><tr><td>TS 24.301</td><td>4974 · 62.2%</td><td>6 · 0.1%</td><td>99 · 100%</td></tr></table><p>ARCANE produces a much smaller set of message-level transitions tailored to fuzzing.</p>`,accuracy:`<table><tr><th>Method</th><th>Evaluated</th><th>Accuracy</th><th>Raw Agreement</th><th>Cohen’s κ</th></tr><tr><td>CellSecInspector</td><td>3147</td><td>98.92%</td><td>99.33%</td><td>0.80</td></tr><tr><td>Hermes</td><td>3634</td><td>25.23%</td><td>98.35%</td><td>0.96</td></tr><tr><td>ARCANE</td><td>162</td><td>0.00%</td><td>100.00%</td><td>N/A</td></tr></table><p>Accuracy requires both evidence-grounded correctness and semantic consistency.</p>`,example:`<p>“A UE enters the state 5GMM-SERVICE-REQUEST-INITIATED after it has started the service request procedure and is waiting for a response from the network.”</p><div class="fsm-example"><div><b>CellSecInspector / SCA</b><p>Start: UE is likely in 5GMM-REGISTERED.</p><p>Condition: After the UE has started the service request procedure AND is waiting for a response.</p><p>Action: UE enters 5GMM-SERVICE-REQUEST-INITIATED.</p><p>End: UE is in that state, waiting for a response.</p></div><div><b>Hermes / FSM</b><p>Start: A UE enters 5GMM-SERVICE-REQUEST-INITIATED.</p><p>Condition: started procedure; waiting for response.</p><p class="missing">Action: N/A</p><p class="missing">End: N/A</p></div></div>`}; function bindRq3(){const out=detail.querySelector('#rq3-content'); const show=k=>{out.innerHTML=rq3Views[k];detail.querySelectorAll('[data-rq3]').forEach(b=>b.classList.toggle('active',b.dataset.rq3===k));};detail.querySelectorAll('[data-rq3]').forEach(b=>b.onclick=()=>show(b.dataset.rq3));show('quantity');} Array.from(rqGrid.children).forEach((card,index)=>{card.tabIndex=0;card.setAttribute('role','button');card.setAttribute('aria-expanded','false');const open=()=>{const active=card.classList.contains('active');Array.from(rqGrid.children).forEach(item=>{item.classList.remove('active');item.setAttribute('aria-expanded','false');});detail.hidden=active;if(!active){card.classList.add('active');card.setAttribute('aria-expanded','true');detail.innerHTML=`<p class="eyebrow">${card.querySelector('small').textContent}</p>${index===1?rq2:index===2?rq3:`<p>${details[index]}</p>`}`;if(index===2)bindRq3();}};card.onclick=open;card.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}};});}
if (comparisonBody && compareFilter && compareCount) {
  function renderComparison() { const rows = data.comparison.filter(r => compareFilter.value === 'all' || !r[2]); comparisonBody.innerHTML = rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2] ? '<span class="yes">● Detected</span>' : '<span class="no">○ Missed</span>'}</td><td><span class="yes">● Detected</span></td></tr>`).join(''); compareCount.textContent = `${rows.length} findings`; }
  compareFilter.addEventListener('change', renderComparison);
  renderComparison();
}
