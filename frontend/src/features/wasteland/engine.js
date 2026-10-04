// Original fiction and rules. Deterministic replays, no remote calls or paid assets.
export const VERSION = 'wasteland-v1'
export const ATTRIBUTES = [
  { id: 'survival', name: '体能', description: '影响初始健康与外出风险' },
  { id: 'insight', name: '洞察', description: '影响判断与初始技术' },
  { id: 'craft', name: '巧手', description: '影响修复与初始庇护' },
  { id: 'empathy', name: '共情', description: '影响初始士气与信任' },
]
export const STATS = [
  { id: 'health', name: '健康', color: '#ed9c8a' }, { id: 'food', name: '补给', color: '#d7be81' },
  { id: 'morale', name: '士气', color: '#b1bbf1' }, { id: 'shelter', name: '庇护', color: '#90c5ba' },
  { id: 'tech', name: '技术', color: '#92bfe0' }, { id: 'trust', name: '信任', color: '#d9b2ca' },
]
export const TALENTS = [
  { id: 'scavenger', name: '拾荒直觉', text: '初始补给 +10；偶尔找到被忽略的物资。', effects: { food: 10 } },
  { id: 'medic', name: '急救经验', text: '初始健康 +15；行动受伤时损失较少。', effects: { health: 15 } },
  { id: 'mechanic', name: '旧物新生', text: '初始庇护 +12；每天积累一点修复技术。', effects: { shelter: 12 } },
  { id: 'calm', name: '风暴中的安静', text: '初始士气 +15；动荡中依然保留一点希望。', effects: { morale: 15 } },
  { id: 'speaker', name: '一盏灯的温度', text: '初始信任 +12；互助行动有额外收获。', effects: { trust: 12 } },
  { id: 'ration', name: '精打细算', text: '每日补给消耗从2降至1，少量储备也能走得更远。', effects: {} },
]
const choice = (text, effects, risk = 0, failure = {}, need = null) => ({ text, effects, risk, failure, need })
export const EVENTS = [
  { id: 'market', title: '褪色的集市', text: '风吹过卷帘门。货架空了，角落里还有几个没有拆封的箱子。', choices: [choice('慢慢搜寻，留意出口', { food: 7, morale: -2 }), choice('深入仓库，寻找大宗储备', { food: 14, tech: 3 }, .38, { health: -12, food: 2 }), choice('画下地图，让后来的人少走弯路', { trust: 8, tech: 4, food: 2 })] },
  { id: 'rain', title: '长夜的雨', text: '雨穿过破损的天窗。你能听见滴水，也听见远处有人敲门。', choices: [choice('修补屋顶，守住这一夜', { shelter: 10, morale: 3 }), choice('分出干燥的位置', { trust: 10, morale: 6, food: -3 }), choice('搭一套简易收集器', { tech: 10, food: 4 }, 0, {}, { craft: 4 })] },
  { id: 'radio', title: '电台里的杂音', text: '旧收音机传来断续的坐标。信号也许来自营地，也许只是一个过时的承诺。', choices: [choice('记录坐标，继续核实', { tech: 9, morale: 3 }), choice('当天就出发', { food: 12, trust: 7 }, .4, { health: -12, morale: -5 }), choice('在附近架起中继天线', { tech: 12, trust: 5, shelter: 3 }, 0, {}, { insight: 4 })] },
  { id: 'dog', title: '跟着你的影子', text: '一只瘦小的狗保持着几步距离。它没有靠近，也没有离开。', choices: [choice('留一点补给，慢慢建立信任', { food: -3, morale: 9, trust: 6 }), choice('跟着它找路', { food: 11, morale: 4 }, .25, { health: -6 }), choice('记住它出现的位置', { tech: 5, morale: 2, food: 2 })] },
  { id: 'garden', title: '楼顶的绿色', text: '高楼顶上，一片小小的绿叶仍然朝向太阳。世界没有停止生长。', choices: [choice('整理种植箱，留下种子', { shelter: 5, morale: 5, food: 5 }), choice('改造灌溉装置', { food: 10, tech: 6 }, 0, {}, { craft: 4 }), choice('邀请邻近的人共同维护', { trust: 9, food: 4, morale: 3 })] },
  { id: 'bridge', title: '断桥边的脚印', text: '旧桥的一半沉进了水里。新的脚印，停在靠近断口的位置。', choices: [choice('退回，寻找另一条路', { food: 3, health: 2 }), choice('搭起临时通道', { tech: 9, trust: 8 }, .3, { health: -9, shelter: -3 }), choice('从脚印判断安全路线', { food: 9, tech: 4 }, 0, {}, { insight: 5 })] },
  { id: 'library', title: '没有熄灭的书页', text: '图书馆落满灰尘。一本工程手册里，夹着前任读者留下的书签。', choices: [choice('带走手册与地图', { tech: 10, morale: 3 }), choice('搭建共享阅读角', { trust: 8, shelter: 5, morale: 5 }), choice('查看地下档案室', { tech: 14, food: 7 }, .35, { health: -8, morale: -5 })] },
  { id: 'power', title: '停转的发电机', text: '营地旁的设备还有一点燃料。能否再亮起一盏灯，取决于你接下来的尝试。', choices: [choice('拆下可用的零件', { tech: 6, shelter: 4 }), choice('耐心修复电路', { tech: 12, shelter: 8 }, 0, {}, { craft: 4 }), choice('召集懂技术的邻居', { trust: 8, tech: 6, food: -2 })] },
  { id: 'mist', title: '雾中的路标', text: '浓雾里只有几米能见度。你发现路标被旋转了方向。', choices: [choice('停下整理记录', { health: 4, tech: 4, morale: 2 }), choice('沿墙探索附近', { food: 9 }, .3, { health: -8, morale: -3 }), choice('重新标记正确方向', { trust: 9, tech: 6 })] },
  { id: 'visitor', title: '背着工具箱的人', text: '陌生人没有要求进屋。他说，只想换一顿饭，然后修好你破损的窗。', choices: [choice('分享一餐，交换技能', { food: -4, shelter: 10, trust: 7 }), choice('在屋外共同完成修补', { shelter: 6, tech: 5 }), choice('提供临时落脚点', { trust: 12, morale: 8, food: -5 }, 0, {}, { empathy: 4 })] },
  { id: 'clinic', title: '旧站里的补给包', text: '一座应急站尚未完全倒塌。柜子里有封装完好的基础补给。', choices: [choice('取走一份并清点存量', { health: 9, food: 4 }), choice('把存量分享给营地', { trust: 12, morale: 5, health: 3 }), choice('进入倾斜的后厅', { health: 15, food: 8 }, .4, { health: -13 })] },
  { id: 'snow', title: '提前到来的冷风', text: '温度一夜间下降。地面出现细碎冰晶，门缝里的风越来越响。', choices: [choice('加固墙体，封住门缝', { shelter: 11, health: 3 }), choice('为邻居送去保暖材料', { trust: 9, morale: 7, shelter: -3 }), choice('寻找旧仓里的厚布', { shelter: 14, food: 6 }, .3, { health: -9 })] },
  { id: 'signal', title: '墙上的记号', text: '三道短线，一条箭头。相同的记号出现在街角，像是一种新的约定。', choices: [choice('做记录，辨认规律', { tech: 8, food: 2 }), choice('跟随箭头', { food: 12, trust: 5 }, .32, { morale: -7, health: -7 }), choice('留下自己的安全路线', { trust: 9, tech: 5 })] },
  { id: 'rest', title: '没有任务的午后', text: '今天街道安静了一点。难得的空白，也是一种需要好好安排的资源。', choices: [choice('休息，整理伤痕', { health: 10, morale: 7 }), choice('清点物资，减少浪费', { food: 7, tech: 3 }), choice('与营地的人聊聊', { morale: 10, trust: 8 })] },
  { id: 'cart', title: '卡住的手推车', text: '车轮陷进碎石。车上满是补给，推车的人快没有力气了。', choices: [choice('一起推过去，分享一点补给', { food: 9, trust: 6, health: -2 }), choice('改造车轮', { tech: 7, food: 8, trust: 5 }, 0, {}, { craft: 4 }), choice('让其他人帮忙，再回到岗位', { trust: 5, shelter: 7, food: 3 })] },
  { id: 'candle', title: '一场小小的生日', text: '营地里有人找到一根蜡烛。没有蛋糕，他们仍然想记住这个日子。', choices: [choice('拿出一点储备', { food: -3, morale: 13, trust: 8 }), choice('讲一个旧世界的故事', { morale: 8, trust: 5 }), choice('做一件小礼物', { tech: 6, morale: 8 }, 0, {}, { craft: 4 })] },
  { id: 'solar', title: '晴天的碎玻璃', text: '屋顶上残留一块光伏板。表面有裂痕，但接线盒还很完整。', choices: [choice('回收稳定可用的部分', { tech: 9, shelter: 3 }), choice('尝试恢复供电', { tech: 15, shelter: 8 }, .28, { health: -6, tech: 2 }), choice('搭建共同充电点', { trust: 10, tech: 8, food: -2 })] },
  { id: 'river', title: '顺流而来的箱子', text: '密封箱卡在浅滩里。河水变得湍急，岸边还有安全的固定点。', choices: [choice('用长杆拖到岸边', { food: 8, tech: 3 }), choice('系好绳子尝试打捞', { food: 15, tech: 4 }, .35, { health: -10 }), choice('叫来同伴一起处理', { food: 10, trust: 8 }, 0, {}, { empathy: 4 })] },
]
const CHECKPOINTS = {
  7: { id: 'camp', title: '第七天：一个可以称为家的地方', text: '你不再只是一名过客。有人提出建立一处共同营地，也有人准备继续迁移。', choices: [choice('稳定营地与储备', { shelter: 14, food: 8 }), choice('建立互助约定', { trust: 14, morale: 8 }), choice('研究撤离路线', { tech: 14, food: 4 })] },
  15: { id: 'transmission', title: '第十五天：坐标开始清晰', text: '远处传来有规律的广播。你第一次听清“月底”与“转运站”两个词。', choices: [choice('修复信号设备', { tech: 15, morale: 5 }), choice('稳固营地，不把希望押在一条广播上', { shelter: 15, food: 7 }), choice('联络其他幸存者', { trust: 15, food: 5 })] },
  24: { id: 'decision', title: '第二十四天：下一段路', text: '一份可靠的路线图到了营地。带走设备还是留下建设，需要提前准备。', choices: [choice('准备远行装备', { tech: 14, food: 8, shelter: -3 }), choice('建立长期防护', { shelter: 16, food: 4 }), choice('组成同行队伍', { trust: 16, morale: 8, food: 3 })] },
  30: { id: 'dawn', title: '第三十天：远处的灯', text: '转运站的灯亮起来了。营地也在清晨升起炊烟。你走到这一天，已经做出了无数次选择。', choices: [choice('沿着可靠坐标，走向转运站', { morale: 10 }, 0, {}, { tech: 45 }), choice('与营地一起，重新建造生活', { morale: 10 }, 0, {}, { shelter: 45, trust: 35 }), choice('带上日记，继续守望这片土地', { morale: 5 })] },
}
const clamp = value => Math.max(0, Math.min(100, value))
function hash(seed) { let value = 2166136261; for (const char of seed) value = Math.imul(value ^ char.charCodeAt(0), 16777619); return value >>> 0 || 1 }
function random(state) { let value = state.rng; value ^= value << 13; value ^= value >>> 17; value ^= value << 5; state.rng = value >>> 0 || 1; return state.rng / 4294967296 }
function effects(state, changes) { for (const [key, value] of Object.entries(changes)) state.stats[key] = clamp(state.stats[key] + value) }
function pickEvent(state) {
  if (CHECKPOINTS[state.day]) return CHECKPOINTS[state.day]
  const recent = state.log.slice(-3).map(item => item.eventId)
  const pool = EVENTS.filter(event => !recent.includes(event.id))
  return pool[Math.floor(random(state) * pool.length)]
}
export function validateConfig(config) {
  return Boolean(config && typeof config.seed === 'string' && config.seed.length >= 1 && config.seed.length <= 64 && Array.isArray(config.talents) && config.talents.length === 2 && new Set(config.talents).size === 2 && config.talents.every(id => TALENTS.some(t => t.id === id)) && config.attributes && Object.keys(config.attributes).length === 4 && ATTRIBUTES.every(a => Number.isInteger(config.attributes[a.id]) && config.attributes[a.id] >= 0 && config.attributes[a.id] <= 8) && Object.values(config.attributes).reduce((a, b) => a + b, 0) === 12)
}
export function createGame(config) {
  if (!validateConfig(config)) throw new Error('选择2个天赋，分配12点属性；每项0–8点，种子1–64字。')
  const { survival, insight, craft, empathy } = config.attributes
  const state = { version: VERSION, config: structuredClone(config), rng: hash(config.seed), day: 1, stats: { health: 65 + survival * 2, food: 20 + survival * 2, morale: 50 + empathy * 2, shelter: 8 + craft * 3, tech: 5 + insight * 3, trust: 8 + empathy * 3 }, log: [], ending: null, event: null }
  config.talents.forEach(id => effects(state, TALENTS.find(t => t.id === id).effects))
  state.event = structuredClone(pickEvent(state))
  return state
}
export function availableChoice(state, item) {
  if (!item.need) return true
  return Object.entries(item.need).every(([id, minimum]) => (state.config.attributes[id] ?? state.stats[id] ?? 0) >= minimum)
}
export function advance(state, index) {
  if (!state || state.ending || !Number.isInteger(index) || !state.event?.choices[index]) throw new Error('此行动不可用。')
  const next = structuredClone(state), item = next.event.choices[index]
  if (!availableChoice(next, item)) throw new Error('属性尚未达到此行动的条件。')
  const before = { ...next.stats }, talents = next.config.talents
  const risk = Math.max(0, item.risk - next.config.attributes.survival * .025 - next.config.attributes.insight * .015)
  const success = item.risk === 0 || random(next) >= risk
  const outcome = { ...(success ? item.effects : item.failure) }
  if (!success && talents.includes('medic') && outcome.health < 0) outcome.health = Math.ceil(outcome.health * .6)
  effects(next, outcome)
  effects(next, { food: talents.includes('ration') ? -1 : -2, morale: -1 })
  if (talents.includes('mechanic')) effects(next, { tech: 1 })
  if (talents.includes('calm')) effects(next, { morale: 1 })
  if (talents.includes('speaker') && outcome.trust > 0) effects(next, { trust: 2 })
  if (talents.includes('scavenger') && random(next) < .22) effects(next, { food: 3 })
  if (next.stats.food === 0) effects(next, { health: -12, morale: -5 })
  if (next.stats.shelter < 10 && next.day % 5 === 0) effects(next, { health: -7 })
  if (next.stats.morale === 0) effects(next, { health: -6 })
  const changes = Object.fromEntries(STATS.map(s => [s.id, next.stats[s.id] - before[s.id]]).filter(([, value]) => value !== 0))
  next.log.push({ day: next.day, eventId: next.event.id, title: next.event.title, choice: item.text, choiceIndex: index, success, changes })
  if (next.stats.health === 0) next.ending = { id: 'fallen', title: '暂别长夜', text: '你没有走到月底，但你留下的路径、修复与善意，可能成为另一个人的起点。换一组天赋，再试一次。' }
  else if (next.day === 30) next.ending = index === 0 ? { id: 'evacuation', title: '灯火彼岸', text: '你凭可靠的技术与路线走进转运站。新的日子，终于不再只有求生。' } : index === 1 ? { id: 'rebuild', title: '明日营地', text: '你与同伴留下来了。庇护所成了家，而信任让这片地方重新有了名字。' } : { id: 'wanderer', title: '荒野守望', text: '你活过了三十天。带着记录与经验，你选择继续寻找自己的道路。' }
  if (!next.ending) { next.day++; next.event = structuredClone(pickEvent(next)) }
  return next
}
export function saveGame(state) { return { version: VERSION, config: state.config, actions: state.log.map(item => ({ eventId: item.eventId, choice: item.choiceIndex })) } }
export function restoreGame(saved) {
  if (!saved || saved.version !== VERSION || !Array.isArray(saved.actions) || saved.actions.length > 30) throw new Error('存档版本或格式无效。')
  let state = createGame(saved.config)
  for (const item of saved.actions) {
    if (!item || state.ending || state.event.id !== item.eventId) throw new Error('存档行动序列无效。')
    state = advance(state, item.choice)
  }
  return state
}
export function gameMarkdown(state) {
  return ['# 末世模拟器 · 生存记录', '', `世界种子：${state.config.seed}`, `天赋：${state.config.talents.map(id => TALENTS.find(t => t.id === id).name).join('、')}`, `结局：${state.ending?.title || '尚在旅途中'}`, '', ...state.log.map(item => `- 第${item.day}天 / ${item.title}：${item.choice}（${item.success ? '行动完成' : '遇到意外'}）`), '', '这是原创虚构文字游戏，不是现实生存、健康或灾害应对指导。', `规则版本：${VERSION}`, ''].join('\n')
}
