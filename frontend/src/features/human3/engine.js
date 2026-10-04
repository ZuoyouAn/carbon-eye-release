import { DOMAINS, QUESTIONS, VERSION, SOURCE_URL, validateAnswers } from './questionnaire.js'

const ARCHETYPES = {
  workaholic: { name: '工作投入型', english: 'The Workaholic', description: '工作或学习占据大部分精力，而身体与连接的日常支持较少。先为基本生活留出空间。' },
  seeker: { name: '探索寻路型', english: 'The Seeker', description: '思考与意义探索较活跃，身体习惯和实际产出还需要更多承接。用一个小行动验证一个想法。' },
  optimizer: { name: '自我优化型', english: 'The Optimizer', description: '思维与身体实践相对稳定，连接与贡献暂时较弱。可以把已有习惯延伸到共同活动或实际项目。' },
  drifter: { name: '寻找锚点型', english: 'The Drifter', description: '四个领域的日常实践还在起步。先选择一个容易持续的小习惯，形成可以依靠的节奏。' },
  specialist: { name: '单域专长型', english: 'The Specialist', description: '一个领域的实践明显更稳定，其他领域的支持较少。尝试用强项帮助一项基本习惯形成。' },
  integrated: { name: '协同发展型', english: 'The Integrated', description: '四个领域都报告了较稳定的实践，并且存在相互支持。关注这些习惯在新压力下是否仍然适用。' },
  mixed: { name: '多向发展型', english: 'Mixed pattern', description: '目前的回答没有明显落在某一种模式中。保留四个领域的差异，比强行套入一个标签更有用。' },
  uncertain: { name: '需要更多观察', english: 'More context needed', description: '部分领域的有效回答不足，暂时无法可靠地归入一种模式。先观察一周，再补充实际经历。' },
}
const ACTIONS = {
  mind: ['每天用五分钟记录一个重要判断：依据是什么，有什么反例。', '每周选择一个想法做小实验，记录实际结果。', '整理三次实验，保留有效方法，并标注不适用的情境。', '把有效方法用于一个真实问题，每月请可信任的人给一次反馈。'],
  body: ['选定一个可做到的作息时间，连续七天记录精力；从适合自己的轻量活动开始。', '每周复盘一次：忙碌时至少保留哪一项基本习惯。', '连续四周测试一个能兼顾忙碌与恢复的安排。', '在一个较忙的周期里复核习惯，调整到可长期维持的节奏。'],
  spirit: ['给一位信任的人发一条真实近况，并约一次交流。', '每周留出一次相互倾听的时间，也尊重彼此的边界。', '持续参加一个适合自己的共同活动，观察是否建立了真实连接。', '回看哪些关系和活动带来支持，调整投入，减少仅靠意志维持的安排。'],
  vocation: ['选一个可在半小时内推进的具体任务，写下完成标准。', '每周完成一个小产出，向实际使用者或老师同事获取反馈。', '完成一个可以展示的项目或学习成果，复盘投入和收益。', '按反馈调整方向，建立能持续产出、也能保留生活空间的节奏。'],
}

export function assess(answers) {
  if (!validateAnswers(answers, { complete: true })) throw new Error('请完成全部题目，并使用有效的选项。')
  const selected = id => {
    const question = QUESTIONS.find(q => q.id === id)
    return question.options.find(o => o.id === answers[id])
  }
  const internal = DOMAINS.map(domain => {
    const questions = QUESTIONS.filter(q => q.domain === domain.id)
    const evidence = questions.map(q => ({ question: q.title, answer: selected(q.id).label }))
    const values = questions.filter(q => q.kind === 'behavior').map(q => selected(q.id).value).filter(v => v !== null)
    const average = values.length >= 2 ? values.reduce((a, b) => a + b, 0) / values.length : null
    const band = average === null ? null : average < 1.2 ? 0 : average < 2.2 ? 1 : 2
    return { ...domain, average, band, evidence, orientation: selected(`${domain.id}-orientation`).value || '暂未明确', phase: selected(`${domain.id}-phase`).value || '暂未明确', consistency: band === null ? '信息不足' : ['基础待建立', '正在形成', '相对稳定'][band] }
  })
  const byId = Object.fromEntries(internal.map(d => [d.id, d]))
  const { mind, body, spirit, vocation } = byId
  const energy = selected('context-energy').value
  const integration = selected('context-integration').value
  let archetypeId = 'mixed'
  if (internal.some(d => d.band === null)) archetypeId = 'uncertain'
  else if (energy === 'high' && body.band === 0 && spirit.band === 0) archetypeId = 'workaholic'
  else if (mind.band === 2 && spirit.band === 2 && body.band === 0 && vocation.band === 0) archetypeId = 'seeker'
  else if (mind.band === 2 && body.band === 2 && spirit.band === 0 && vocation.band === 0) archetypeId = 'optimizer'
  else if (internal.every(d => d.band === 0)) archetypeId = 'drifter'
  else if (internal.filter(d => d.band === 2).length === 1 && internal.filter(d => d.band === 0).length >= 2) archetypeId = 'specialist'
  else if (internal.every(d => d.band === 2) && integration === 'support') archetypeId = 'integrated'

  const known = internal.filter(d => d.average !== null)
  const lowest = known.length ? Math.min(...known.map(d => d.average)) : null
  const candidates = known.filter(d => Math.abs(d.average - lowest) < 0.01)
  const preference = selected('context-priority').value
  // Preserve ambiguity: ties without a user preference do not become a made-up bottleneck.
  const focus = candidates.find(d => d.id === preference) || (candidates.length === 1 ? candidates[0] : null)
  const planFocus = focus || internal.find(d => d.id === preference) || null
  const strong = known.filter(d => d.band === 2)
  const gaps = internal.filter(d => selected(`${d.id}-learning`).value >= 2 && selected(`${d.id}-practice`).value !== null && selected(`${d.id}-practice`).value <= 1)
  const ai = selected('context-ai').value
  const observations = []
  if (gaps.length) observations.push(`在${gaps.map(d => d.name).join('、')}中，你报告了多次尝试，但日常持续性较少。可以先核对：是否把“试过”当成了“已形成习惯”？`)
  const stressGaps = internal.filter(d => selected(`${d.id}-practice`).value >= 2 && selected(`${d.id}-stress`).value !== null && selected(`${d.id}-stress`).value <= 1)
  if (stressGaps.length) observations.push(`在${stressGaps.map(d => d.name).join('、')}中，日常实践较多，但压力下较难维持。这是需要核实的情境差异，不代表能力已经丧失；先设计忙碌时可保留的最小习惯。`)
  const orientationGaps = internal.filter(d => selected(`${d.id}-orientation`).id === 'synthesis' && selected(`${d.id}-practice`).value !== null && selected(`${d.id}-practice`).value <= 1)
  if (orientationGaps.length) observations.push(`你在${orientationGaps.map(d => d.name).join('、')}中选择了“多方整合”，但日常实践还较少。理解复杂观点不等于已经稳定做到；请用最近一次实际行动核实。`)
  if (energy === 'high') observations.push('你选择工作或学习占用超过八成精力。先核对哪些基本习惯正在被挤占，再增加新的目标。')
  if (integration === 'drain') observations.push('你报告四个领域经常互相挤占。下一周记录一次具体冲突，看看是否可以减少一项投入，保留另一项基本需求。')
  if (ai === 'delegate' || ai === 'dependent') observations.push('你报告较少独立检查 AI 答案，或离开 AI 后难以继续任务。每天保留一段独立完成任务的时间，再对照 AI 的建议。')
  if (!observations.length) observations.push('本次回答没有触发明确的实践落差提示。选择题仍需要结合实际经历核实，尤其是压力较大时的表现。')
  let focusText = '目前没有足够的行为信息确定优先领域。先记录一周的实际生活，再补充回答。'
  if (focus) focusText = `从你的回答看，「${focus.name}」的实践稳定性相对较弱，可以作为下一步核实与行动的候选方向。`
  else if (candidates.length > 1) focusText = `「${candidates.map(d => d.name).join('、')}」的实践情况接近，暂不指定唯一瓶颈。你可以从最想改变、最容易开始的一项着手。`
  if (archetypeId === 'integrated') focusText = '四个领域都报告了相对稳定且相互支持的实践。下一步是验证它们在忙碌或变化中是否仍能持续。'
  const action = planFocus ? ACTIONS[planFocus.id] : ['连续七天记录精力、重要任务和一次真实交流，不必同时改变所有习惯。', '从记录中选一个最小行动，一周尝试三次。', '只保留确实有效的一项实践，每周复盘一次。', '回看已有实践如何影响其他领域，按实际反馈调整。']
  const followUps = internal.map(d => {
    const missing = QUESTIONS.filter(q => q.domain === d.id && q.kind === 'behavior').some(q => selected(q.id).value === null)
    if (missing) return { domain: d.id, title: d.name, reason: '补充缺少的行为信息', question: `最近四周，在「${d.name}」中选一个记得最清楚的场景：发生了什么、你具体做了什么、结果怎样？没有经历也可以直接说没有。`, priority: 0 }
    if (stressGaps.includes(d)) return { domain: d.id, title: d.name, reason: '核实压力下的情境差异', question: `最近一次「${d.name}」的习惯在忙碌时中断，是被什么挤掉的？当时最小能保留的行动是什么？`, priority: 1 }
    if (gaps.includes(d)) return { domain: d.id, title: d.name, reason: '区分尝试与长期实践', question: `在「${d.name}」中，你最近尝试的方法连续做了多久？哪次反馈真正改变了后续做法？`, priority: 2 }
    return { domain: d.id, title: d.name, reason: '用具体经历验证自报选择', question: `请举一个最近四周「${d.name}」中的实际行动：依据是什么、结果是什么、在哪种情况下不适用？`, priority: 3 }
  }).sort((a, b) => a.priority - b.priority).slice(0, 3).map(({ priority, ...item }) => item)
  followUps.push({ domain: 'context', title: '生活联系', reason: '核实四个领域如何相互影响', question: integration === 'support' ? '最近哪一个习惯同时帮助了两个生活领域？发生了什么，能否在下一周再试一次？' : '最近一次时间或精力冲突影响了哪两个领域？如果减少一项投入，什么基本需求可以得到保留？' })
  const evidenceStatus = internal.some(d => d.band === null) ? '行为信息不足：先补充具体经历，暂不确定模式。' : stressGaps.length || gaps.length || orientationGaps.length ? '有待核实的情境或实践差异：先回答追问，再看分类是否贴近实际。' : '选择题已完整：仍需用具体经历核实，不能等同于深度访谈。'
  return {
    version: VERSION, rulesVersion: 'human3-behavior-rules-v2', sourceUrl: SOURCE_URL,
    followUps, evidenceStatus,
    archetype: { id: archetypeId, ...ARCHETYPES[archetypeId] },
    // Never return internal numerical scores to the UI or exported report.
    domains: internal.map(({ average, band, ...domain }) => domain),
    focus: planFocus ? { id: planFocus.id, name: planFocus.name } : null,
    focusText, focusBasis: planFocus && !focus ? '依据你的优先选择确定行动方向；不代表已发现唯一瓶颈。' : '依据最近四周的自报行为提供初步建议。',
    strengths: strong.map(d => d.name), observations,
    dynamics: integration === 'support' ? '你报告这些领域能相互支持。记录一个具体例子，观察哪项习惯最有帮助。' : integration === 'drain' ? '你报告这些领域经常互相挤占。先检查时间与精力安排，再判断是否需要新增计划。' : '领域之间的支持关系还不明确。记录一次“一个领域影响另一个领域”的实际经历。',
    plan: [{ period: '今天', action: action[0] }, { period: '未来 30 天', action: action[1] }, { period: '未来 90 天', action: action[2] }, { period: '未来 180 天', action: action[3] }],
    followUp: planFocus ? `最近一次「${planFocus.name}」的习惯被打断时，具体发生了什么？你做了什么，又需要什么支持？` : '选一个最近遇到的具体问题：它影响了哪些领域，你已经尝试过什么？',
    context: QUESTIONS.filter(q => q.domain === 'context').map(q => ({ question: q.title, answer: selected(q.id).label })),
    limitation: '这是依据自报答案生成的初步发展画像。题目和分类规则为本产品设计，尚未经过心理测量验证；不用于心理或医疗诊断，也不判断人的价值。',
  }
}

export function reportMarkdown(report) {
  const lines = ['# 四维成长评估 · 初步报告', '', `当前模式：${report.archetype.name}（${report.archetype.english}）`, '', report.archetype.description, '', '## 四象限画像', '']
  for (const d of report.domains) {
    lines.push(`### ${d.name} / ${d.english}`, '', `实践：${d.consistency}；参照方式：${d.orientation}；当前阶段：${d.phase}`, '')
    for (const e of d.evidence) lines.push(`- ${e.question} → ${e.answer}`)
    lines.push('')
  }
  lines.push('## 优先行动方向', '', report.focusText, '', report.focusBasis, '', '## 跨象限关系', '', report.dynamics, '', '## 值得核实的地方', '')
  report.observations.forEach(x => lines.push(`- ${x}`))
  lines.push('', '## 行动计划', '')
  report.plan.forEach(p => lines.push(`- ${p.period}：${p.action}`))
  lines.push('', '## 深入反思', '', report.followUp, '', '## 补充回答', '')
  lines.push(report.evidenceStatus, '')
  report.followUps.forEach(item => lines.push(`- ${item.title}（${item.reason}）：${item.question}`))
  report.context.forEach(e => lines.push(`- ${e.question} → ${e.answer}`))
  lines.push('', '## 方法与来源', '', report.limitation, '', `问卷版本：${report.version}；规则版本：${report.rulesVersion}`, '', `框架灵感来源：Dan Koe HUMAN 3.0，${report.sourceUrl}`, '')
  return lines.join('\n')
}
