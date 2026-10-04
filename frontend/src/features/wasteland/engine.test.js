import test from 'node:test'
import assert from 'node:assert/strict'
import { ATTRIBUTES, STATS, TALENTS, EVENTS, VERSION, validateConfig, createGame, availableChoice, advance, saveGame, restoreGame, gameMarkdown } from './engine.js'

const config = (seed = '长夜之后') => ({ seed, talents: ['mechanic', 'ration'], attributes: { survival: 3, insight: 3, craft: 3, empathy: 3 } })
function finish(seed, ending = 2) {
  let state = createGame(config(seed))
  while (!state.ending) {
    const options = state.event.choices.map((choice, index) => ({ choice, index })).filter(({ choice }) => availableChoice(state, choice))
    // Conservative policy: keep food/health first, then build toward a selected ending.
    const weight = key => key === 'food' ? (state.stats.food < 15 ? 9 : 2) : key === 'health' ? (state.stats.health < 35 ? 8 : 1) : key === 'tech' ? (ending === 0 ? 3 : 1) : key === 'shelter' || key === 'trust' ? (ending === 1 ? 3 : 1) : .4
    options.sort((a, b) => {
      const score = item => Object.entries(item.choice.effects).reduce((sum, [key, value]) => sum + value * weight(key), 0) - item.choice.risk * 60
      return score(b) - score(a)
    })
    const choice = state.day === 30 && availableChoice(state, state.event.choices[ending]) ? ending : options[0].index
    state = advance(state, choice)
  }
  return state
}
test('configuration requires exactly two unique known talents and twelve bounded integer attributes', () => {
  assert.equal(validateConfig(config()), true)
  for (const bad of [null, { ...config(), seed: '' }, { ...config(), seed: 'x'.repeat(65) }, { ...config(), talents: ['medic', 'medic'] }, { ...config(), talents: ['unknown', 'medic'] }, { ...config(), attributes: { survival: 9, insight: 1, craft: 1, empathy: 1 } }, { ...config(), attributes: { survival: 3.5, insight: 2.5, craft: 3, empathy: 3 } }, { ...config(), attributes: { survival: 3, insight: 3, craft: 3, empathy: 3, forged: 0 } }]) {
    assert.equal(validateConfig(bad), false); assert.throws(() => createGame(bad))
  }
})
test('six talents, four attributes, six resources and eighteen unique original encounters', () => {
  assert.equal(TALENTS.length, 6); assert.equal(ATTRIBUTES.length, 4); assert.equal(STATS.length, 6)
  assert.equal(EVENTS.length, 18); assert.equal(new Set(EVENTS.map(event => event.id)).size, 18)
  for (const event of EVENTS) { assert.equal(event.choices.length, 3); assert.ok(event.text) }
})
test('same seed and actions produce identical worlds; advancing does not mutate input', () => {
  const a = createGame(config()), b = createGame(config())
  assert.deepEqual(a, b)
  const old = structuredClone(a), next = advance(a, 0)
  assert.deepEqual(a, old); assert.equal(next.day, 2); assert.equal(next.log.length, 1)
  assert.notDeepEqual(createGame(config('另一座城')).rng, a.rng)
})
test('choice gates, invalid indexes and completed games cannot be bypassed', () => {
  const state = createGame(config())
  assert.equal(availableChoice(state, { need: { craft: 4 } }), false)
  assert.equal(availableChoice(state, { need: { craft: 3 } }), true)
  for (const index of [-1, 3, 0.5, '0']) assert.throws(() => advance(state, index))
  state.event.choices[0].need = { craft: 4 }
  assert.throws(() => advance(state, 0))
  assert.throws(() => advance(finish('complete'), 0))
})
test('100 seeded journeys stay bounded, end in at most thirty days and reach all checkpoints when alive', () => {
  for (let seed = 0; seed < 100; seed++) {
    const state = finish(`invariants-${seed}`)
    assert.ok(state.ending); assert.ok(state.log.length >= 1 && state.log.length <= 30)
    for (const value of Object.values(state.stats)) assert.ok(Number.isInteger(value) && value >= 0 && value <= 100)
    for (const [day, id] of [[7, 'camp'], [15, 'transmission'], [24, 'decision'], [30, 'dawn']]) {
      if (state.log.length >= day) assert.equal(state.log[day - 1].eventId, id)
    }
    assert.deepEqual(restoreGame(saveGame(state)), state)
  }
})
test('three surviving endings are reachable by real journeys', () => {
  for (const [choice, ending] of [[0, 'evacuation'], [1, 'rebuild'], [2, 'wanderer']]) {
    const journeys = Array.from({ length: 30 }, (_, seed) => finish(`endings-${seed}`, choice))
    assert.ok(journeys.some(state => state.ending.id === ending), `unreachable ending ${ending}`)
  }
})
test('resource depletion ends a journey rather than advancing forever', () => {
  const state = createGame(config())
  state.stats.health = 1; state.stats.food = 0
  state.event.choices[0].effects = {}
  const ended = advance(state, 0)
  assert.equal(ended.ending.id, 'fallen'); assert.equal(ended.day, 1)
})
test('save stores actions only; replay rejects corruption and ignores forged resources', () => {
  const game = advance(createGame(config()), 0), saved = saveGame(game)
  assert.deepEqual(Object.keys(saved).sort(), ['actions', 'config', 'version'])
  assert.deepEqual(restoreGame({ ...saved, stats: { health: 99999 } }), game)
  for (const bad of [null, { ...saved, version: 'old' }, { ...saved, actions: Array(31).fill(saved.actions[0]) }, { ...saved, actions: [{ eventId: 'forged', choice: 0 }] }, { ...saved, actions: [{ eventId: saved.actions[0].eventId, choice: 99 }] }]) assert.throws(() => restoreGame(bad))
  assert.equal(saved.version, VERSION)
})
test('export includes seed, actual journey, ending and fictional-game disclaimer', () => {
  const state = finish('export-seed')
  const markdown = gameMarkdown(state)
  for (const text of ['末世模拟器', 'export-seed', state.ending.title, `第${state.log.length}天`, '原创虚构', VERSION]) assert.ok(markdown.includes(text))
})
