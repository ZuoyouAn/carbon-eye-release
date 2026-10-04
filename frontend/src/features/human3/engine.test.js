import test from 'node:test'
import assert from 'node:assert/strict'
import { assess, reportMarkdown } from './engine.js'
import { DOMAINS, QUESTIONS, VERSION, validateAnswers } from './questionnaire.js'

function responses(scores, context = {}) {
  return Object.fromEntries(QUESTIONS.map(q => {
    if (q.kind === 'behavior') return [q.id, scores[q.domain] === null ? 'unknown' : `b${scores[q.domain]}`]
    if (q.kind === 'orientation') return [q.id, 'synthesis']
    if (q.kind === 'phase') return [q.id, 'uncertainty']
    return [q.id, context[q.id] || 'unknown']
  }))
}
const low = { mind: 0, body: 0, spirit: 0, vocation: 0 }

test('adaptive follow-ups prioritize missing behavior and include cross-domain evidence', () => {
  const report = assess(responses({ ...low, body: null }))
  assert.equal(report.followUps[0].domain, 'body')
  assert.equal(report.followUps.length, 4)
  assert.equal(report.followUps.at(-1).domain, 'context')
  assert.ok(report.evidenceStatus.includes('信息不足'))
})

test('stress disruption is flagged separately from routine practice without diagnosis', () => {
  const answers = responses({ mind: 3, body: 3, spirit: 3, vocation: 3 })
  answers['body-stress'] = 'b0'
  const report = assess(answers)
  assert.ok(report.observations.some(item => item.includes('身体') && item.includes('压力')))
  assert.equal(report.followUps[0].domain, 'body')
  assert.ok(report.followUps[0].reason.includes('压力'))
})

test('sophisticated orientation still needs specific practice evidence', () => {
  const report = assess(responses(low))
  assert.ok(report.observations.some(item => item.includes('理解复杂观点不等于')))
  assert.ok(reportMarkdown(report).includes(report.rulesVersion))
})

test('questionnaire has 24 unique questions and independently measures each domain', () => {
  assert.equal(QUESTIONS.length, 24)
  assert.equal(new Set(QUESTIONS.map(q => q.id)).size, 24)
  for (const d of DOMAINS) {
    const items = QUESTIONS.filter(q => q.domain === d.id)
    assert.equal(items.length, 5)
    assert.equal(items.filter(q => q.kind === 'behavior').length, 3)
    assert.equal(items.filter(q => q.kind === 'phase').length, 1)
    assert.equal(items.filter(q => q.kind === 'orientation').length, 1)
  }
})

for (const [name, scores, context] of [
  ['workaholic', { ...low, vocation: 3 }, { 'context-energy': 'high' }],
  ['seeker', { ...low, mind: 3, spirit: 3 }, {}],
  ['optimizer', { ...low, mind: 3, body: 3 }, {}],
  ['drifter', low, {}],
  ['specialist', { ...low, body: 3 }, {}],
  ['integrated', { mind: 3, body: 3, spirit: 3, vocation: 3 }, { 'context-integration': 'support' }],
  ['mixed', { mind: 2, body: 2, spirit: 2, vocation: 2 }, {}],
  ['uncertain', { ...low, mind: null }, {}],
]) {
  test(`representative profile: ${name}`, () => assert.equal(assess(responses(scores, context)).archetype.id, name))
}

test('high ability alone does not imply integration or work dominance', () => {
  assert.equal(assess(responses({ mind: 3, body: 3, spirit: 3, vocation: 3 })).archetype.id, 'mixed')
  assert.equal(assess(responses({ ...low, vocation: 3 })).archetype.id, 'specialist')
})

test('unknown responses remain valid but do not become low scores or fictional bottlenecks', () => {
  const report = assess(responses({ mind: null, body: null, spirit: null, vocation: null }))
  assert.equal(report.archetype.id, 'uncertain')
  assert.equal(report.focus, null)
  assert.ok(report.domains.every(d => d.consistency === '信息不足'))
})

test('one unknown behavioral response is allowed; two unknowns cause insufficient evidence', () => {
  const answers = responses({ ...low, mind: 3 })
  answers['mind-stress'] = 'unknown'
  assert.equal(assess(answers).domains[0].consistency, '相对稳定')
  answers['mind-learning'] = 'unknown'
  assert.equal(assess(answers).domains[0].consistency, '信息不足')
})

test('sophisticated orientation does not override absent practice; phase stays separate', () => {
  const report = assess(responses(low))
  assert.equal(report.domains[0].orientation, '多方整合')
  assert.equal(report.domains[0].phase, '探索试验')
  assert.equal(report.domains[0].consistency, '基础待建立')
})

test('tied domains are not silently ranked; explicit preference resolves the action choice', () => {
  assert.equal(assess(responses(low)).focus, null)
  const report = assess(responses(low, { 'context-priority': 'body' }))
  assert.equal(report.focus.id, 'body')
})

test('report cites exact selections and flags a learning/practice gap without diagnosing', () => {
  const answers = responses(low)
  answers['mind-learning'] = 'b3'
  const report = assess(answers)
  assert.ok(report.observations.some(x => x.includes('试过')))
  const selected = QUESTIONS[1].options.find(o => o.id === 'b3').label
  assert.equal(report.domains[0].evidence[1].answer, selected)
})

test('AI habit flag affects guidance, not the archetype or domain classifications', () => {
  const base = assess(responses(low))
  const dependent = assess(responses(low, { 'context-ai': 'dependent' }))
  assert.equal(dependent.archetype.id, base.archetype.id)
  assert.deepEqual(dependent.domains, base.domains)
  assert.ok(dependent.observations.some(x => x.includes('AI')))
})

test('validates completeness and rejects malformed or forged answers', () => {
  const valid = responses(low)
  assert.ok(validateAnswers(valid, { complete: true }))
  assert.ok(validateAnswers({}))
  assert.throws(() => assess({}), /完成全部/)
  for (const bad of [null, [], 'text', { ...valid, fake: 'b3' }, { ...valid, 'mind-stress': 3 }, { ...valid, 'mind-stress': 'b99' }]) {
    assert.equal(validateAnswers(bad), false)
    assert.throws(() => assess(bad))
  }
})

test('public report has no hidden score fields; export contains evidence, plan and source', () => {
  const report = assess(responses(low))
  const json = JSON.stringify(report)
  assert.doesNotMatch(json, /"(?:score|average|band)":/)
  const markdown = reportMarkdown(report)
  assert.ok(markdown.includes(VERSION))
  assert.ok(markdown.includes('Dan Koe'))
  assert.ok(markdown.includes('未来 180 天'))
  assert.ok(markdown.includes(QUESTIONS[0].title))
  assert.ok(markdown.includes('尚未经过心理测量验证'))
})
