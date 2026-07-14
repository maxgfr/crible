export const meta = { name: "ultraeval-codebase", description: "Evaluate /Users/maxime/Downloads/crible (mode: improve) — ground every finding, then emit a TDD backlog", phases: [{"title":"Research"},{"title":"TestPlan"},{"title":"Analyze"},{"title":"Brainstorm"},{"title":"Gate"},{"title":"Judge"},{"title":"Results"}] }

// NOT a plain Node script: launch via the Workflow tool — Workflow({ scriptPath: "evals/2026-07-14/eval.workflow.mjs" }).
// agent()/phase()/parallel()/log() only exist inside that harness; plain `node` prints guidance and exits 2.

// Constants for THIS eval run (injected by `ultraeval plan`).
const TARGET = "/Users/maxime/Downloads/crible"
const ENGINE = "/Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs"
const RUN = "evals/2026-07-14"
const AGENTS = RUN + '/agents'
const CATEGORY = "self-hosted fintech tool"
const KIND = "codebase"
const DIMENSIONS = [{"id":"correctness","name":"Correctness","weight":0.3,"whatPerfectLooksLike":"correct on happy AND edge paths; no logic bugs","anchors":[{"standard":"ISO/IEC 25010:2023","ref":"Functional suitability — functional correctness"},{"standard":"ISO/IEC 25010:2023","ref":"Reliability — faultlessness"}]},{"id":"tests","name":"Test quality","weight":0.2,"whatPerfectLooksLike":"tests fail when the code is wrong (not just coverage %)","anchors":[{"standard":"ISO/IEC 25010:2023","ref":"Maintainability — testability"}]},{"id":"security","name":"Security","weight":0.2,"whatPerfectLooksLike":"no exploitable source->sink flows; inputs validated","anchors":[{"standard":"ISO/IEC 25010:2023","ref":"Security — confidentiality, integrity, resistance"},{"standard":"OWASP Top 10 (2021)","ref":"categories A01–A10","note":"informative"}]},{"id":"maintainability","name":"Maintainability","weight":0.2,"whatPerfectLooksLike":"clear boundaries, low duplication","anchors":[{"standard":"ISO/IEC 25010:2023","ref":"Maintainability — modularity, analysability, modifiability"}]},{"id":"performance","name":"Performance","weight":0.1,"whatPerfectLooksLike":"no hot-path waste; scales to realistic inputs","anchors":[{"standard":"ISO/IEC 25010:2023","ref":"Performance efficiency — time behaviour, resource utilization, capacity"}]}]

// Parse-safe guard: under plain `node` the Workflow-harness globals are absent.
if (typeof phase === 'undefined') {
  console.error('eval.workflow.mjs is a Workflow-harness script, not a plain Node script — agent()/phase()/parallel()/log() come from the harness.')
  console.error('Launch it with: Workflow({ scriptPath: ' + JSON.stringify(RUN + '/eval.workflow.mjs') + ' })')
  console.error('No Workflow tool? Run the stages by hand: dispatch a subagent per contract under ' + AGENTS + '/*.md (see SKILL.md step 3).')
  process.exit(2)
}

function contract(name, extra) {
  return 'Read and follow the dispatch contract at ' + AGENTS + '/' + name + '.md VERBATIM.\n'
    + 'Constants: TARGET=' + TARGET + '  ENGINE=' + ENGINE + '  RUN=' + RUN + '  KIND=' + KIND + '  CATEGORY=' + CATEGORY + '.\n'
    + 'Invoke the engine only by its ABSOLUTE path: node ' + ENGINE + ' <cmd>. Write every artifact under RUN. Do not stop early.'
    + (extra ? '\n' + extra : '')
}

log("ultraeval improve eval for " + TARGET)

// Budget discipline (protocol v2): under a harness token target, scale down
// DELIBERATELY and record every coverage cut — a silent cut reads as full coverage.
let LENSES = ['correctness+grounding', 'completeness+coverage', 'ux+meets-expectations']
let RESEARCH_GROUPED = false
const CUTS = []
if (typeof budget !== 'undefined' && budget && budget.total) {
  const left = budget.remaining()
  if (left < 600000) { RESEARCH_GROUPED = true; CUTS.push('research: ' + DIMENSIONS.length + ' per-dimension agents -> 1 grouped agent (' + Math.round(left / 1000) + 'k tokens left < 600k)') }
  if (left < 300000) { LENSES = LENSES.slice(0, 2); CUTS.push('judges: 3 lenses -> 2 (' + Math.round(left / 1000) + 'k tokens left < 300k)') }
}
if (CUTS.length) {
  log('budget: recording ' + CUTS.length + ' coverage cut(s) to ' + RUN + '/runs/budget.md')
  await agent('Create the file ' + RUN + '/runs/budget.md (mkdir -p its directory) containing a markdown doc titled "# Budget coverage cuts" with one bullet per cut: ' + CUTS.map((c) => '"' + c + '"').join(', ') + '. Write NOTHING else and change no other file.', { label: 'budget-scribe', agentType: 'general-purpose' })
}

phase('Research')
if (RESEARCH_GROUPED) {
  await agent(contract('researcher', 'DIMENSIONS=ALL (budget cut — see runs/budget.md). Cover EVERY dimension in one pass; write one ' + RUN + '/research/<id>.md per dimension (cited).'), { label: 'research:all', phase: 'Research', agentType: 'general-purpose' })
} else {
  await parallel(DIMENSIONS.map((d) => () => agent(contract('researcher', 'DIMENSION=' + d.id + ' (' + d.name + '). Write ' + RUN + '/research/' + d.id + '.md (cited).'), { label: 'research:' + d.id, phase: 'Research', agentType: 'general-purpose' })))
}

phase('TestPlan')
await agent(contract('testplan'), { label: 'testplan', phase: 'TestPlan', agentType: 'general-purpose' })

phase('Analyze')
await agent(contract('analyzer'), { label: 'analyze', phase: 'Analyze', agentType: 'general-purpose' })

phase('Brainstorm')
await agent(contract('brainstormer'), { label: 'brainstorm', phase: 'Brainstorm', agentType: 'general-purpose' })

phase('Gate')
await agent(contract('gate'), { label: 'gate', phase: 'Gate', agentType: 'general-purpose' })

phase('Judge')
await parallel(LENSES.map((lens, i) => () => agent(contract('judge', 'LENS=' + lens), { label: 'judge' + (i + 1), phase: 'Judge', agentType: 'general-purpose' })))

phase('Results')
await agent(contract('remediator', CUTS.length ? 'BUDGET CUTS to report in SUMMARY.md (also listed in ' + RUN + '/runs/budget.md): ' + CUTS.join(' | ') : ''), { label: 'results', phase: 'Results', agentType: 'general-purpose' })

// No top-level `return` — that is a parse-time SyntaxError under plain `node` (the guard
// above never gets a chance to run). Mirror rejudge.workflow.mjs: close with a log line.
log('ultraeval eval complete — see ' + RUN + '/index.html and ' + RUN + '/SUMMARY.md')
