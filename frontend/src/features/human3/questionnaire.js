// Original questionnaire inspired by the four-domain HUMAN 3.0 framework.
// This is a versioned product rubric, not a validated psychological scale.
export const VERSION = 'human3-questionnaire-v1'
export const SOURCE_URL = 'https://letters.thedankoe.com/p/prompt-human-30-self-discovery-and'
export const DOMAINS = [
  { id: 'mind', name: '思维', english: 'Mind', color: '#9bafff', description: '理解信息、更新观点，以及把想法付诸实践。' },
  { id: 'body', name: '身体', english: 'Body', color: '#71dfbd', description: '睡眠、精力和日常习惯能否支持你的生活。' },
  { id: 'spirit', name: '关系与意义', english: 'Spirit', color: '#dfb5ff', description: '与人连接、归属感，以及生活的意义来源。' },
  { id: 'vocation', name: '事业与贡献', english: 'Vocation', color: '#ffc788', description: '工作或学习中，你怎样行动、创造价值。' },
]

function options(values) {
  return values.map(([id, label, value]) => ({ id, label, value }))
}
function behavior(id, domain, title, labels) {
  const choices = options(labels.map((label, value) => [`b${value}`, label, value]))
  // Alternate ordering to avoid always placing the highest-frequency answer last.
  if (id.endsWith('stress')) choices.reverse()
  return { id, domain, kind: 'behavior', title, hint: '回想最近四周的实际情况，而不是理想中的自己。', options: [...choices, { id: 'unknown', label: '不确定 / 暂时没有适用的经历', value: null }] }
}
function orientation(domain, title, labels) {
  return { id: `${domain}-orientation`, domain, kind: 'orientation', title, hint: '选择最接近你的做法；每种做法都有适用场景。', options: options([
    ['external', labels[0], '外部参照'], ['agency', labels[1], '自主探索'], ['synthesis', labels[2], '多方整合'], ['unknown', '不确定 / 几种方式都会使用', null],
  ]) }
}
function phase(domain) {
  return { id: `${domain}-phase`, domain, kind: 'phase', title: `对于「${DOMAINS.find(d => d.id === domain).name}」，你目前更接近哪种状态？`, hint: '状态会随情境变化，不代表固定的人格。', options: options([
    ['dissonance', '现有方式让我不满意，但还没找到替代办法。', '寻找改变'],
    ['uncertainty', '正在尝试新做法，还在观察它是否适合我。', '探索试验'],
    ['discovery', '找到了一些有效做法，正在让它们稳定下来。', '巩固实践'],
    ['unknown', '目前没有明显的阶段感。', null],
  ]) }
}

export const QUESTIONS = [
  orientation('mind', '遇到与你观点冲突的信息，你通常怎样处理？', ['先参考信任的人或机构如何判断。', '先独立寻找证据，再形成自己的判断。', '比较不同解释，并确认各自适用的条件。']),
  behavior('mind-learning', 'mind', '最近四周，你怎样检验学到的新想法？', ['主要阅读或收藏，还没有实际检验。', '偶尔试一次，很少记录效果。', '有多次尝试，会根据结果调整。', '持续实践和复盘，也能说明它在哪些情况下不适用。']),
  behavior('mind-practice', 'mind', '当发现自己的判断有问题时，你实际调整过几次？', ['没有调整过，或很少重新检查。', '有过一次调整，但后续没有再检查。', '多次根据新的信息修改做法。', '持续复核重要判断，也会主动寻找反例。']),
  behavior('mind-stress', 'mind', '压力较大时，你还能怎样处理复杂问题？', ['通常只能立即反应，很难停下来梳理。', '事后可以反思，当时较难做到。', '多数时候能暂停一下，再选择处理方式。', '能使用稳定的梳理方法，也知道何时需要帮助。']),
  phase('mind'),
  orientation('body', '做健康或运动决定时，你通常参考什么？', ['熟悉的建议、身边人的安排或日常惯例。', '自己的目标，例如外形、表现或体能。', '结合精力、长期健康和实际生活安排。']),
  behavior('body-learning', 'body', '最近四周，你怎样调整睡眠、饮食或活动习惯？', ['知道需要改变，但还没有采取行动。', '试过一些改变，没有持续观察。', '根据自己的精力或记录，调整过几次。', '持续观察并调整，能找到适合自己的安排。']),
  behavior('body-practice', 'body', '最近四周，你计划的基本身体习惯保持得怎样？', ['基本没有形成规律。', '只在少数几天做到了。', '多数日子可以做到。', '保持较稳定，也留出了休息与恢复空间。']),
  behavior('body-stress', 'body', '事情突然变多时，你的基本身体习惯通常怎样？', ['睡眠、饮食或活动常常全部被挤掉。', '中断后，往往很久才恢复。', '会缩小计划，保留一两项基本习惯。', '能灵活调整，忙碌后也能较快恢复。']),
  phase('body'),
  orientation('spirit', '生活缺少意义感时，你通常从哪里寻找方向？', ['家人、传统、信仰或熟悉群体提供的方向。', '自己选择的兴趣、体验或个人目标。', '连接个人选择、与人的关系和实际贡献。']),
  behavior('spirit-learning', 'spirit', '最近四周，你如何把重视的关系或价值观落实到生活里？', ['大多停留在想法上，还没有具体行动。', '偶尔有行动，但很少继续。', '有多次具体行动，也会听取对方反馈。', '有稳定的投入，并根据反馈调整相处方式。']),
  behavior('spirit-practice', 'spirit', '最近四周，你有多少真正交流或相互支持的机会？', ['很少，或基本没有。', '偶尔有，但比较难持续。', '多数周都有这样的交流。', '有稳定连接，彼此能表达需要和提供支持。']),
  behavior('spirit-stress', 'spirit', '有冲突或情绪低落时，你通常怎样维持连接？', ['往往断开联系，很难表达需要。', '愿意联系，但常常拖到很久以后。', '多数时候能找到可信任的人沟通。', '能表达需要、尊重边界，并在冲突后尝试修复。']),
  phase('spirit'),
  orientation('vocation', '判断工作或学习是否成功时，你通常看什么？', ['是否完成要求、获得认可或达到既定标准。', '是否达成自己的收入、技能或成就目标。', '是否产生实际价值，同时能长期持续。']),
  behavior('vocation-learning', 'vocation', '最近四周，你如何验证一个工作或学习的新方法？', ['主要看教程或计划，还没有开始验证。', '做过一次尝试，没有获取实际反馈。', '完成过多个小任务，并根据反馈调整。', '持续产出并复盘，能判断方法的适用范围。']),
  behavior('vocation-practice', 'vocation', '最近四周，你的重要任务推进得怎样？', ['方向不清楚，或基本没有推进。', '偶尔推进，常被其他事情打断。', '多数周能完成具体的阶段任务。', '有持续产出，也会主动调整目标与投入。']),
  behavior('vocation-stress', 'vocation', '任务压力升高时，你怎样维持工作或学习？', ['容易停滞，或者全部靠临时赶工。', '能继续做，但常常失去优先顺序。', '多数时候能减少任务，保留关键产出。', '能调整计划、沟通资源，并保持可持续节奏。']),
  phase('vocation'),
  { id: 'context-energy', domain: 'context', kind: 'context', title: '最近四周，工作或学习大约占用了多少可支配精力？', hint: '按你的感受估计即可；这是投入情况，不是能力评分。', options: options([['low', '不足一半', 'low'], ['medium', '大约一半到八成', 'medium'], ['high', '超过八成，其他生活经常被挤掉', 'high'], ['unknown', '不确定', null]]) },
  { id: 'context-integration', domain: 'context', kind: 'context', title: '这四个生活领域，目前怎样相互影响？', hint: '想一个最近发生的实际例子。', options: options([['drain', '经常互相挤占，例如忙工作就完全没时间照顾身体。', 'drain'], ['parallel', '主要靠分别安排时间维持，联系不多。', 'parallel'], ['support', '经常互相支持，例如活动改善精力，也带来人际连接。', 'support'], ['unknown', '暂时说不清。', null]]) },
  { id: 'context-ai', domain: 'context', kind: 'context', title: '使用 AI 时，你目前更接近哪种情况？', hint: '用于理解工具习惯，不参与四象限分类。', options: options([['none', '很少或没有使用 AI。', 'none'], ['assist', '先自己思考，再用 AI 协助，并检查重要结果。', 'assist'], ['delegate', '常直接采用 AI 的答案，较少独立检查。', 'delegate'], ['dependent', '没有 AI 时，很难继续原本能够完成的任务。', 'dependent'], ['unknown', '不确定。', null]]) },
  { id: 'context-priority', domain: 'context', kind: 'context', title: '如果未来一个月只改善一件事，你最想从哪里开始？', hint: '你的选择会帮助我们在相近的方向之间确定行动重点。', options: options([...DOMAINS.map(d => [d.id, d.name, d.id]), ['unknown', '还没想好', null]]) },
]

export function validateAnswers(answers, { complete = false } = {}) {
  if (!answers || typeof answers !== 'object' || Array.isArray(answers)) return false
  const allowed = new Map(QUESTIONS.map(q => [q.id, q]))
  if (!Object.entries(answers).every(([id, value]) => allowed.get(id)?.options.some(o => o.id === value))) return false
  return !complete || QUESTIONS.every(q => Object.hasOwn(answers, q.id))
}
