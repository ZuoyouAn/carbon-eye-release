<template>
  <main class="human-page">
    <div class="human-topline"><RouterLink to="/projects">← 返回项目</RouterLink><span>HUMAN 3.0 INSPIRED · 四维成长地图</span></div>

    <section v-if="stage === 'intro'" class="human-welcome">
      <div class="human-kicker">SELF DISCOVERY / 01</div>
      <h1>看见你的生活，<br><em>从哪里开始改变。</em></h1>
      <p class="human-lead">用最近四周的真实经历，看看思维、身体、关系与事业如何相互影响。找到一个可以从今天开始的小行动。</p>
      <div class="human-facts"><span>24 道选择题</span><span>约 5–8 分钟</span><span>无需登录</span></div>
      <div class="human-domain-grid">
        <article v-for="(domain, i) in DOMAINS" :key="domain.id" class="human-domain-preview" :style="{ '--accent': domain.color }">
          <div class="human-domain-index">0{{ i + 1 }} <span>{{ domain.english }}</span></div>
          <h2>{{ domain.name }}</h2><p>{{ domain.description }}</p>
        </article>
      </div>
      <div class="human-start-card">
        <p>请选择“实际上怎么做”，不必寻找最理想的答案。可以选择不确定，也可以返回修改。</p>
        <label class="human-check"><input v-model="remember" type="checkbox" @change="changeRemember">在这台设备保存进度，方便稍后继续</label>
        <p class="human-caption">默认回答和规则报告均在浏览器内处理，不会上传。勾选后保存在此浏览器，可随时清除；共享设备建议不勾选。未来使用 AI 补充分析时，会另行征求上传同意。</p>
        <p v-if="resumeAvailable" class="human-resume">发现已保存的进度：已回答 {{ answeredCount }} / {{ QUESTIONS.length }} 题。</p>
        <div class="human-actions"><button class="human-primary" @click="start">{{ resumeAvailable ? '继续我的评估' : '开始了解自己' }} <span>→</span></button><button v-if="resumeAvailable" class="human-secondary" @click="clearAll">清除已保存的内容</button></div>
      </div>
      <p class="human-method">基于 HUMAN 3.0 四象限框架设计的固定问卷。结果用于自我反思；题目和规则尚未经过心理测量验证，不用于心理或医疗诊断。<a :href="SOURCE_URL" target="_blank" rel="noopener noreferrer">了解框架来源 ↗</a></p>
    </section>

    <section v-else-if="stage === 'questions'" class="human-interview">
      <div class="human-progress-heading"><span>{{ currentSection }}</span><span>第 {{ index + 1 }} / {{ QUESTIONS.length }} 题</span></div>
      <div class="human-progress" role="progressbar" aria-label="已回答题目" :aria-valuenow="answeredCount" :aria-valuemax="QUESTIONS.length" aria-valuemin="0"><div :style="{ width: `${answeredCount / QUESTIONS.length * 100}%` }"></div></div>
      <ol class="human-steps"><li v-for="(name, i) in ['思维', '身体', '关系与意义', '事业与贡献', '生活联系']" :key="name" :class="{ active: sectionIndex === i, done: sectionIndex > i }"><span>{{ i + 1 }}</span>{{ name }}</li></ol>
      <form class="human-question-card" @submit.prevent="next">
        <p class="human-kicker">{{ current.domain === 'context' ? 'CONNECT THE DOTS' : DOMAINS.find(d => d.id === current.domain).english.toUpperCase() }}</p>
        <fieldset :key="current.id"><legend ref="questionHeading" tabindex="-1">{{ current.title }}</legend><p class="human-hint">{{ current.hint }}</p>
          <label v-for="(option, i) in current.options" :key="option.id" class="human-option" :class="{ selected: answers[current.id] === option.id }"><input :checked="answers[current.id] === option.id" type="radio" :name="current.id" :value="option.id" @change="choose(option.id)"><span class="human-option-letter">{{ String.fromCharCode(65 + i) }}</span><span>{{ option.label }}</span><span class="human-option-check" aria-hidden="true">{{ answers[current.id] === option.id ? '✓' : '' }}</span></label>
        </fieldset>
        <div class="human-question-footer"><button type="button" class="human-secondary" @click="previous">{{ index === 0 ? '返回介绍' : '← 上一题' }}</button><button class="human-primary" type="submit" :disabled="!answers[current.id]">{{ index === QUESTIONS.length - 1 ? '查看我的报告' : '下一题' }} →</button></div>
      </form>
      <div class="human-session-controls"><span>{{ remember ? '进度已保存在此浏览器' : '当前回答仅在本次页面中保留' }}</span><button class="human-link-button" @click="clearAll">清除回答并返回</button></div>
    </section>

    <section v-else-if="report" class="human-report">
      <div class="human-report-heading"><div><p class="human-kicker">YOUR DEVELOPMENT MAP</p><h1>你的四维成长地图</h1><p>这是一张当前状态的草图，可以随着新的经历更新。</p></div><button class="human-secondary" @click="download">下载完整报告 ↓</button></div>
      <div class="human-pattern"><div><span class="human-pill">当前生活模式 · 初步倾向</span><h2>{{ report.archetype.name }}</h2><span class="human-english">{{ report.archetype.english }}</span></div><p>{{ report.archetype.description }}</p></div>
      <div class="human-domain-grid human-result-grid"><article v-for="domain in report.domains" :key="domain.id" class="human-domain-preview" :style="{ '--accent': domain.color }"><div class="human-domain-index">{{ domain.english }}<span>四象限画像</span></div><h2>{{ domain.name }}</h2><div class="human-result-label">{{ domain.consistency }}</div><dl><div><dt>参照方式</dt><dd>{{ domain.orientation }}</dd></div><div><dt>当前阶段</dt><dd>{{ domain.phase }}</dd></div></dl><details><summary>查看回答依据</summary><ul><li v-for="e in domain.evidence" :key="e.question"><p>{{ e.question }}</p><span>{{ e.answer }}</span></li></ul></details></article></div>
      <div class="human-report-columns"><article class="human-report-panel"><p class="human-kicker">01 / NEXT FOCUS</p><h2>先从一个方向开始</h2><p>{{ report.focusText }}</p><p class="human-caption">{{ report.focusBasis }}</p><p v-if="report.strengths.length">可借助的实践基础：{{ report.strengths.join('、') }}。</p></article><article class="human-report-panel"><p class="human-kicker">02 / CONNECTIONS</p><h2>看见领域之间的联系</h2><p>{{ report.dynamics }}</p></article></div>
      <article class="human-report-panel"><p class="human-kicker">03 / A CLOSER LOOK</p><h2>值得进一步核实的地方</h2><ul class="human-observations"><li v-for="observation in report.observations" :key="observation">{{ observation }}</li></ul></article>
      <article class="human-report-panel"><p class="human-kicker">04 / SMALL STEPS</p><h2>{{ report.focus ? `从「${report.focus.name}」开始的行动计划` : '从观察开始的行动计划' }}</h2><div class="human-plan"><div v-for="(step, i) in report.plan" :key="step.period"><span class="human-plan-number">0{{ i + 1 }}</span><h3>{{ step.period }}</h3><p>{{ step.action }}</p></div></div></article>
      <article class="human-reflection"><p class="human-kicker">GO BEYOND THE CHECKBOX</p><h2>{{ report.followUp }}</h2><p>{{ report.evidenceStatus }}</p><ol><li v-for="item in report.followUps" :key="item.domain"><strong>{{ item.title }} · {{ item.reason }}</strong><p>{{ item.question }}</p></li></ol><p>追问根据本次回答调整，并非固定人格标签。写给自己，或者与信任的人聊聊；下一步的价值来自行动和反馈。</p></article>
      <article class="human-report-panel"><p class="human-kicker">OPTIONAL / AI REFLECTION</p><h2>AI 补充反思</h2><p v-if="!aiStatus?.enabled">{{ aiStatusError ? '暂时无法确认AI服务状态。' : '当前为免费的本地规则版；AI接口已预留，配置模型密钥后才会开放。' }} 不影响查看、修改和下载报告。</p><template v-else><p>模型服务：{{ aiStatus.provider === 'doubao' ? '豆包 / 火山方舟' : 'DeepSeek' }}。AI只提供补充追问与行动建议，不重新评定人格或等级。</p><label for="human-reflection">可选：补充一个真实经历（最多 1600 字，不要填写姓名、联系方式或健康隐私）</label><textarea id="human-reflection" v-model="reflection" maxlength="1600" placeholder="发生了什么？你做了什么？结果如何？" :disabled="aiLoading"></textarea><label class="human-check"><input v-model="aiConsent" type="checkbox" :disabled="aiLoading">我同意将24道答案及本次补充发至模型服务商</label><p class="human-caption">本站不保存答案及AI文本，仅记录每日调用次数。服务商按其隐私政策处理数据；每天有调用限制，失败也计入次数。请先登录。</p><button class="human-primary" :disabled="!aiConsent || !isLoggedIn || aiLoading" @click="requestReflection">{{ aiLoading ? '正在生成补充反思…' : '发送本次答案，获取补充反思' }}</button><RouterLink v-if="!isLoggedIn" to="/login?redirect=/human3" class="human-secondary">先登录（离开会丢失未保存回答）</RouterLink></template><p v-if="aiError" role="status">{{ aiError }}</p><div v-if="aiResult" class="human-ai-result" role="status"><p class="human-caption">{{ aiResult.disclaimer }}</p><p>{{ aiResult.content }}</p></div></article>
      <details class="human-report-panel"><summary>方法、框架来源与补充回答</summary><p>{{ report.limitation }}</p><p>实践稳定性、参照方式和阶段分别推断；它们不会被合并为“人格等级”。原型只在回答明确符合规则时给出，其他情况保留混合模式或信息不足。</p><ul><li v-for="e in report.context" :key="e.question">{{ e.question }} → {{ e.answer }}</li></ul><p class="human-caption">规则版本：{{ report.version }} · 灵感来源：<a :href="SOURCE_URL" target="_blank" rel="noopener noreferrer">Dan Koe / HUMAN 3.0 ↗</a></p></details>
      <div class="human-actions human-report-bottom"><button class="human-primary" @click="download">下载报告</button><button class="human-secondary" @click="review">修改我的回答</button><button class="human-secondary" @click="clearAll">清除回答和报告</button></div>
      <label class="human-check human-save-report"><input v-model="remember" type="checkbox" @change="changeRemember">在此浏览器保存回答，下次可以重新查看报告</label>
    </section>
    <p v-if="notice" role="status" class="human-notice">{{ notice }}</p>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { DOMAINS, QUESTIONS, SOURCE_URL, VERSION, validateAnswers } from '../features/human3/questionnaire.js'
import { assess, reportMarkdown } from '../features/human3/engine.js'
import { apiRequest } from '../api/client.js'
import { isLoggedIn } from '../stores/auth.js'

const STORAGE_KEY = 'human3-questionnaire-progress'
const stage = ref('intro')
const index = ref(0)
const answers = ref({})
const remember = ref(false)
const resumeAvailable = ref(false)
const report = ref(null)
const notice = ref('')
const questionHeading = ref(null)
const aiStatus = ref(null), aiStatusError = ref(false), aiConsent = ref(false), reflection = ref(''), aiResult = ref(null), aiLoading = ref(false), aiError = ref('')
let aiController = null
function resetAI() {
  aiController?.abort(); aiController = null
  aiConsent.value = false; reflection.value = ''; aiResult.value = null; aiError.value = ''; aiLoading.value = false
}
onUnmounted(resetAI)
watch(stage, async (value) => {
  resetAI()
  if (value !== 'report') return
  aiStatus.value = null; aiStatusError.value = false
  try { aiStatus.value = await apiRequest('/api/human3/ai-status') }
  catch { aiStatusError.value = true }
})
async function requestReflection() {
  if (!aiConsent.value || !isLoggedIn.value || !aiStatus.value?.enabled || aiLoading.value) return
  const controller = new AbortController(); aiController = controller
  aiLoading.value = true; aiError.value = ''; aiResult.value = null
  try {
    const result = await apiRequest('/api/human3/reflect', { method: 'POST', signal: controller.signal, body: JSON.stringify({ consent: true, answers: answers.value, reflection: reflection.value }) })
    if (aiController === controller) aiResult.value = result
  } catch (error) { if (aiController === controller) aiError.value = error.message }
  finally { if (aiController === controller) { aiLoading.value = false; aiController = null } }
}
const current = computed(() => QUESTIONS[index.value])
const answeredCount = computed(() => Object.keys(answers.value).length)
const sectionIndex = computed(() => index.value < 20 ? Math.floor(index.value / 5) : 4)
const currentSection = computed(() => current.value.domain === 'context' ? '生活联系' : DOMAINS.find(d => d.id === current.value.domain).name)

onMounted(() => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const saved = JSON.parse(raw)
    if (saved.version !== VERSION || !validateAnswers(saved.answers) || !Number.isInteger(saved.index) || saved.index < 0 || saved.index >= QUESTIONS.length) {
      localStorage.removeItem(STORAGE_KEY)
      notice.value = '旧进度与当前问卷不匹配，已清除；可以开始新的评估。'
      return
    }
    answers.value = saved.answers
    const firstMissing = QUESTIONS.findIndex(q => !Object.hasOwn(saved.answers, q.id))
    index.value = firstMissing < 0 ? saved.index : Math.min(saved.index, firstMissing)
    remember.value = true
    resumeAvailable.value = true
  } catch {
    notice.value = '无法读取本机进度，你仍可正常完成评估。'
  }
})

function save() {
  if (!remember.value) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: VERSION, answers: answers.value, index: index.value }))
  } catch {
    remember.value = false
    notice.value = '浏览器未能保存进度，回答仍保留在当前页面中。'
  }
}
function changeRemember() {
  if (remember.value) save()
  else {
    try { localStorage.removeItem(STORAGE_KEY) } catch { notice.value = '浏览器阻止了清除保存内容，请在浏览器设置中清除此网站的数据。' }
  }
}
function start() {
  notice.value = ''
  if (validateAnswers(answers.value, { complete: true })) {
    report.value = assess(answers.value)
    stage.value = 'report'
  } else stage.value = 'questions'
  save()
  focusQuestion()
}
function choose(id) {
  answers.value = { ...answers.value, [current.value.id]: id }
  save()
}
function next() {
  if (!answers.value[current.value.id]) return
  if (index.value < QUESTIONS.length - 1) index.value++
  else {
    try { report.value = assess(answers.value); stage.value = 'report'; window.scrollTo({ top: 0, behavior: 'smooth' }) }
    catch (error) { notice.value = error.message; index.value = QUESTIONS.findIndex(q => !answers.value[q.id]) }
  }
  save()
  focusQuestion()
}
function previous() {
  if (index.value === 0) stage.value = 'intro'
  else index.value--
  resumeAvailable.value = answeredCount.value > 0
  save()
  focusQuestion()
}
function review() { report.value = null; index.value = 0; stage.value = 'questions'; save(); focusQuestion() }
async function focusQuestion() { await nextTick(); questionHeading.value?.focus() }
function clearAll() {
  resetAI()
  answers.value = {}; report.value = null; index.value = 0; stage.value = 'intro'; remember.value = false; resumeAvailable.value = false
  notice.value = '回答、报告与此浏览器中的保存进度已清除。'
  try { localStorage.removeItem(STORAGE_KEY) } catch { notice.value = '当前页面的回答已清除；浏览器阻止了删除保存内容，请在浏览器设置中清除此网站的数据。' }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function download() {
  const blob = new Blob([reportMarkdown(report.value)], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = '四维成长评估报告.md'; document.body.appendChild(anchor); anchor.click(); anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
</script>

<style scoped>
.human-page { width: min(1100px, calc(100% - 40px)); margin: 0 auto; padding: 30px 0 70px; color: #eef0f8; }
.human-topline { display: flex; justify-content: space-between; gap: 20px; font-size: 12px; color: #a6afc2; padding-bottom: 32px; }
.human-topline a:hover, .human-method a, .human-report-panel a { color: #a8c7ff; }
.human-topline span, .human-kicker { letter-spacing: .13em; }
.human-kicker { font-size: 11px; color: #9eaccb; margin: 0 0 22px; }
.human-welcome h1 { font-size: clamp(36px, 5.6vw, 65px); line-height: 1.2; letter-spacing: -.035em; font-weight: 650; margin: 0 0 24px; }
.human-welcome h1 em { font-style: normal; color: #a9b7ff; }
.human-lead { max-width: 620px; font-size: 17px; line-height: 1.9; color: #b6bfd2; }
.human-facts { display: flex; flex-wrap: wrap; gap: 12px; margin: 24px 0 36px; }
.human-facts span, .human-pill { display: inline-block; padding: 7px 12px; border: 1px solid #34405b; border-radius: 20px; color: #cad3e6; font-size: 12px; }
.human-domain-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 28px; }
.human-domain-preview { padding: 23px 19px; background: #121b2be0; border: 1px solid #2a354a; border-radius: 16px; border-top: 2px solid var(--accent); min-width: 0; }
.human-domain-index { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; color: var(--accent); font-size: 12px; }
.human-domain-index span { color: #8d9bb3; }
.human-domain-preview h2 { font-size: 21px; margin: 20px 0 12px; }
.human-domain-preview p { color: #aab6cb; font-size: 13px; line-height: 1.8; margin: 0; }
.human-start-card { padding: 26px; border: 1px solid #35415e; border-radius: 18px; background: linear-gradient(110deg, #1c2840e0, #141c2bd9); }
.human-start-card > p:first-child { margin-top: 0; color: #c4cede; line-height: 1.8; }
.human-check { display: flex; align-items: center; gap: 10px; font-size: 14px; cursor: pointer; }
.human-check input { accent-color: #a8b9ff; width: 17px; height: 17px; flex-shrink: 0; }
.human-caption { color: #9baac1; font-size: 12px; line-height: 1.8; }
.human-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
.human-primary, .human-secondary { padding: 13px 22px; border-radius: 9px; cursor: pointer; min-height: 46px; font-size: 14px; line-height: 1.5; }
.human-primary { background: #b4c0ff; color: #111b32; font-weight: 700; }
.human-primary:hover:not(:disabled) { background: #c7d0ff; }
.human-primary:disabled { opacity: .4; cursor: not-allowed; }
.human-secondary { border: 1px solid #3b4860; background: #152032; color: #c6d1e4; }
.human-secondary:hover { background: #22314b; }
.human-method { max-width: 830px; font-size: 12px; line-height: 1.9; color: #8797b0; margin-top: 22px; }
.human-method a { margin-left: 8px; }
.human-resume { color: #93dfbc; font-size: 13px; }
.human-interview { max-width: 800px; margin: 0 auto; }
.human-progress-heading { display: flex; justify-content: space-between; font-size: 13px; color: #b5c2dc; margin-bottom: 12px; }
.human-progress { height: 5px; background: #26334b; border-radius: 10px; overflow: hidden; }
.human-progress > div { background: linear-gradient(90deg, #95b2ff, #95dbd0); height: 100%; transition: width .2s; }
.human-steps { display: flex; list-style: none; padding: 0; gap: 14px; justify-content: space-between; margin: 25px 0 32px; }
.human-steps li { color: #93a1b9; display: flex; align-items: center; gap: 7px; font-size: 12px; }
.human-steps li span { display: grid; place-items: center; width: 23px; height: 23px; border: 1px solid #3a4660; border-radius: 50%; }
.human-steps .active { color: #c2cbff; }.human-steps .active span { background: #a7b8ff; color: #10192e; }.human-steps .done { color: #92d4c0; }
.human-question-card { background: #121b2bef; border: 1px solid #303d55; border-radius: 20px; padding: 36px; }
.human-question-card fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.human-question-card legend { padding: 0; width: 100%; font-size: clamp(22px, 3vw, 30px); line-height: 1.5; font-weight: 650; }
.human-question-card legend:focus { outline: none; }
.human-hint { color: #96a7c2; line-height: 1.8; font-size: 13px; margin: 16px 0 26px; }
.human-option { display: flex; align-items: center; gap: 13px; position: relative; padding: 17px; border: 1px solid #34415a; border-radius: 11px; margin: 12px 0; cursor: pointer; font-size: 14px; line-height: 1.7; background: #182338; }
.human-option:hover { border-color: #7c91c8; }.human-option.selected { border-color: #adbcff; background: #273654; }
.human-option input { position: absolute; opacity: 0; width: 1px; height: 1px; }.human-option:focus-within { outline: 2px solid #d5dcff; outline-offset: 3px; }
.human-option-letter { flex-shrink: 0; width: 29px; height: 29px; display: grid; place-items: center; font-size: 12px; background: #263550; border-radius: 7px; color: #b4c5e8; }
.human-option-check { margin-left: auto; color: #c5cfff; flex-shrink: 0; width: 15px; }
.human-question-footer { display: flex; justify-content: space-between; gap: 14px; margin-top: 30px; }
.human-session-controls { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; margin-top: 20px; color: #8fa0ba; font-size: 12px; }
.human-link-button { padding: 0; color: #aebcdf; background: none; cursor: pointer; text-decoration: underline; }
.human-report-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px; margin-bottom: 26px; }
.human-report-heading h1 { font-size: clamp(30px, 4vw, 44px); margin: 0 0 12px; }.human-report-heading p:not(.human-kicker) { color: #a7b6d0; font-size: 14px; }
.human-pattern { display: grid; grid-template-columns: 1fr 1.3fr; gap: 30px; padding: 30px; border: 1px solid #46547a; border-radius: 18px; margin-bottom: 28px; background: linear-gradient(120deg, #273554, #192435); }
.human-pattern h2 { font-size: 33px; margin: 22px 0 6px; }.human-english { color: #a9b9de; font-size: 14px; }.human-pattern p { align-self: center; color: #c4cee2; line-height: 1.9; font-size: 15px; }
.human-result-label { display: inline-block; padding: 7px 10px; background: #27334a; border-radius: 7px; color: var(--accent); font-size: 13px; }
.human-result-grid dl { margin: 22px 0; font-size: 12px; }.human-result-grid dl div { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin: 13px 0; }.human-result-grid dt { color: #95a5c0; }.human-result-grid dd { margin: 0; color: #d0d9ec; }
.human-result-grid summary { color: #b6c5e2; font-size: 12px; cursor: pointer; }.human-result-grid ul { padding-left: 16px; }.human-result-grid li { margin-bottom: 16px; font-size: 12px; line-height: 1.7; color: #c1cce1; }.human-result-grid li p { color: #92a3bf; margin-bottom: 6px; }
.human-report-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.human-report-panel { border: 1px solid #303c53; background: #121b2be0; border-radius: 16px; padding: 26px; margin-bottom: 22px; line-height: 1.85; }.human-report-panel h2 { font-size: 22px; margin: 0 0 18px; }.human-report-panel p:not(.human-kicker):not(.human-caption), .human-report-panel li { color: #b4c1d8; font-size: 14px; }.human-report-panel summary { cursor: pointer; color: #c3d0e8; }
.human-observations { padding-left: 20px; }.human-observations li + li { margin-top: 14px; }
.human-plan { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 24px; }.human-plan-number { font-size: 24px; color: #99b2dd; }.human-plan h3 { font-size: 15px; }.human-plan p { font-size: 13px !important; }
.human-reflection { padding: 30px; margin: 30px 0; border-left: 2px solid #b5c1ff; background: #1a2640b0; border-radius: 0 16px 16px 0; }.human-reflection h2 { font-size: 24px; line-height: 1.6; font-weight: 500; }.human-reflection p:not(.human-kicker) { font-size: 14px; line-height: 1.9; color: #aebdd5; }.human-report-bottom { margin-top: 28px; }.human-save-report { margin-top: 24px; color: #afbdd6; }
.human-notice { background: #243750; border: 1px solid #50729a; padding: 15px; border-radius: 9px; color: #d6e6ff; line-height: 1.7; font-size: 13px; margin-top: 22px; }
.human-reflection ol { padding-left: 20px; }.human-reflection li { padding: 10px 0; color: #bdcce3; font-size: 14px; }.human-ai-result { padding: 18px; margin-top: 22px; background: #1c2941; border-radius: 12px; }.human-ai-result > p:last-child { white-space: pre-wrap; overflow-wrap: anywhere; }.human-report-panel textarea { margin: 12px 0 20px; }
button:focus-visible, a:focus-visible, summary:focus-visible { outline: 2px solid #d5dcff; outline-offset: 4px; }
@media (max-width: 860px) { .human-domain-grid { grid-template-columns: 1fr 1fr; }.human-plan { grid-template-columns: 1fr 1fr; }.human-pattern { grid-template-columns: 1fr; gap: 12px; }.human-report-columns { grid-template-columns: 1fr; gap: 0; } }
@media (max-width: 540px) { .human-page { width: calc(100% - 28px); padding-top: 24px; }.human-topline { font-size: 11px; flex-direction: column; gap: 13px; }.human-domain-preview { padding: 18px 13px; }.human-domain-preview h2 { font-size: 18px; }.human-start-card { padding: 20px; }.human-steps { gap: 8px; flex-wrap: wrap; justify-content: flex-start; }.human-steps li { font-size: 11px; }.human-question-card { padding: 22px 17px; }.human-option { padding: 14px 11px; gap: 9px; font-size: 13px; }.human-primary, .human-secondary { padding: 12px 15px; font-size: 13px; }.human-pattern { padding: 23px; }.human-report-panel { padding: 22px; }.human-plan { grid-template-columns: 1fr; gap: 12px; }.human-plan > div { border-bottom: 1px solid #34405b; }.human-plan > div:last-child { border: 0; }.human-reflection { padding: 23px; }.human-reflection h2 { font-size: 21px; } }
@media (prefers-reduced-motion: reduce) { .human-progress > div { transition: none; } }
</style>
