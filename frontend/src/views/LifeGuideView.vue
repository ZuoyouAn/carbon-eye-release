<template>
  <main class="content-page guide-page">
    <header class="guide-heading"><p class="section-kicker">THE EVIDENCE-BASED LIFE / A READING SPACE</p><h1>把生活，<br><span>过得更明白。</span></h1><p>高性价比人生指南 · 原文阅读、全文检索、来源可追溯。</p></header>
    <p class="guide-disclaimer">这是一份备选清单，不是任务清单。正文由原作者维护，不替代医生、律师或会计。急症请先求助急救；法律、补贴和政策请核对最新官方规定。</p>
    <p v-if="loading" class="state-text" role="status">正在加载原文…</p>
    <p v-if="error" class="state-text" role="alert">{{ error }} <button class="text-button" type="button" @click="load">重试未加载的章节</button></p>
    <template v-if="manifest">
      <section class="guide-reader" aria-label="阅读与收藏"><div><p class="section-kicker">YOUR READING SPACE</p><h2>留住值得再读的那一条。</h2><p>收藏 {{ saved.length }} 条 · {{ enabled ? '已开启本机保存' : '仅当前会话，不自动保存' }}。不上传账号，不保存检索词或正文。</p></div><div class="guide-reader-actions"><label><input v-model="enabled" type="checkbox" @change="persistenceChanged" /> 在本机保存收藏与阅读定位</label><label><input v-model="onlySaved" type="checkbox" @change="filtersChanged" /> 只看收藏</label><button v-if="resume" class="text-button" type="button" @click="jump(resume)">继续读第 {{ resume.split('-')[0] }} 节第 {{ resume.split('-')[1] }} 条 ↗</button><button class="text-button" type="button" @click="clearRecords">清除收藏与阅读记录</button></div></section>
      <p v-if="warning" class="guide-notice" role="status">{{ warning }}</p>
      <form class="guide-filters" @submit.prevent="filtersChanged">
        <label class="guide-search">全文检索<input v-model="query" type="search" placeholder="例如：租房、睡眠、借条，空格分隔多个词" maxlength="100" @input="filtersChanged" /></label>
        <label>章节<select v-model="chapter" @change="filtersChanged"><option value="">全部章节</option><option v-for="item in manifest.chapters" :key="item.number" :value="String(item.number)">第 {{ item.number }} 节 · {{ item.title }}</option></select></label>
        <label>证据等级<select v-model="evidence" @change="filtersChanged"><option value="">全部证据</option><option>A</option><option>B</option><option>C</option></select></label>
        <label>换回什么<select v-model="benefit" @change="filtersChanged"><option value="">全部口径（不混合排名）</option><option v-for="item in benefits" :key="item">{{ item }}</option></select></label>
        <label>金钱成本<select v-model="money" @change="filtersChanged"><option value="">不限成本</option><option value="0">不花钱</option><option value="少">少</option><option value="多">多</option></select></label>
        <label>作者性价比档<select v-model="value" @change="filtersChanged"><option value="">全部档位</option><option>极高</option><option>高</option><option>一般</option></select></label>
        <div class="guide-filter-actions"><button class="button button-secondary" type="button" @click="reset">清空筛选</button><button class="text-button" type="button" @click="share()">复制筛选链接 ↗</button></div>
      </form>
      <div class="guide-meta" :data-index-ready="loaded === manifest.chapters.length"><span>{{ results.length }} / {{ manifest.count }} 条 · {{ manifest.chapters.length }} 节</span><span>{{ indexing || loaded < manifest.chapters.length ? `索引准备 ${loaded} / ${manifest.chapters.length}，当前结果尚不完整` : '全文索引就绪 · 原文顺序' }} · 证据 ≠ 性价比</span></div>
      <section v-if="currentChapter" class="guide-intro markdown-body" v-html="renderMarkdown(resolveSourceLinks(currentChapter.intro, manifest.commit, currentChapter.file))" />
      <p v-if="!results.length" class="state-text">{{ indexing ? '已加载的章节暂时没有匹配项，正在继续准备全文索引。' : onlySaved ? '当前筛选下没有收藏，先收藏条目或清空筛选。' : '没有找到符合条件的原文。换个关键词，或清空筛选。' }}</p>
      <div class="guide-results"><article v-for="entry in paged" :key="entry.id" class="guide-card" :id="`entry-${entry.id}`" tabindex="-1">
        <div class="guide-entry-meta"><span>第 {{ entry.chapter }} 节 · 第 {{ entry.number }} 条</span><span>证据 {{ entry.evidence || '未标注' }}</span></div><h2>{{ entry.title }}</h2><p>{{ entry.summary || '展开查看完整原文、来源和适用条件。' }}</p>
        <div class="guide-tags"><span v-if="entry.tags.口径">换{{ entry.tags.口径 }}</span><span>性价比：{{ entry.ratio }}</span><span v-if="/争议/.test(entry.markdown)">含争议，阅读备注</span><span v-if="/TODO|待核实/.test(entry.markdown)">含待核实内容</span></div>
        <div class="guide-card-actions"><button type="button" :aria-pressed="saved.includes(entry.id)" :aria-label="`${saved.includes(entry.id) ? '取消收藏' : '收藏'}第${entry.chapter}节第${entry.number}条`" @click="save(entry.id)">{{ saved.includes(entry.id) ? '已收藏 ✓' : '收藏这一条' }}</button><button type="button" @click="share(entry.id)">分享条目 ↗</button></div>
        <details :open="expanded.has(entry.id)" @toggle="toggleEntry(entry.id, $event)"><summary>阅读完整原文、来源与备注</summary><template v-if="expanded.has(entry.id)"><div class="markdown-body guide-original" v-html="renderMarkdown(resolveSourceLinks(entry.markdown, manifest.commit, entry.file))" /><a class="text-button" :href="sourceUrl(manifest.commit, entry.file)" target="_blank" rel="noopener noreferrer">核对这一节的原文 ↗</a></template></details>
      </article></div>
      <nav v-if="pages > 1" class="guide-pagination" aria-label="原文分页"><button type="button" :disabled="page <= 1" @click="turn(-1)">上一页</button><span>{{ page }} / {{ pages }}</span><button type="button" :disabled="page >= pages" @click="turn(1)">下一页</button></nav>
      <div v-if="shareMessage" class="guide-share" role="status"><p>{{ shareMessage }}</p><label v-if="shareFallback">分享链接<input :value="shareFallback" readonly @focus="$event.target.select()" /></label></div>
      <section class="guide-explainer"><h2>怎么读这些标签？</h2><p>A / B / C 是原书标注的证据等级，不保证对每个人适用，也不代表因果确定。性价比档来自作者的成本与收益量级判断，本身不是医学或法律证据。钱、时间、寿命和人身自由各算各的，不混合排名。</p><p>展开条目会保留完整来源和备注；有争议或待核实的内容不能当成定论。本页没有个性化建议，也不调用模型 API。本机记录只保存条目编号；共用设备请关闭保存或清除记录。</p></section>
      <footer class="guide-attribution"><p>《高性价比人生指南》 · {{ manifest.author }} · <a :href="manifest.source" target="_blank" rel="noopener noreferrer">原始仓库</a> · <a :href="manifest.licenseUrl" target="_blank" rel="noopener noreferrer">CC BY 4.0</a> · <a href="/life-guide/LICENSE.txt">完整许可</a></p><p>同步日期 {{ manifest.syncedAt }} · 版本 {{ manifest.commit.slice(0, 12) }}。{{ manifest.changes }} 原作者未为本站背书；内容按原作者原样提供，不保证持续更新。</p></footer>
    </template>
  </main>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { renderMarkdown } from '../utils/markdown'
import { filterEntries, resolveSourceLinks, sourceUrl } from '../features/life-guide/library'
import { guideLoader } from '../features/life-guide/loader'
import { guideQuery, parseGuideQuery, readReader, writeReader } from '../features/life-guide/reader'
const route = useRoute(), router = useRouter(), manifest = ref(null), chapters = ref([]), loading = ref(true), indexing = ref(false), error = ref(''), loaded = ref(0)
const query = ref(''), chapter = ref(''), evidence = ref(''), benefit = ref(''), money = ref(''), value = ref(''), page = ref(1), pendingEntry = ref('')
const saved = ref([]), resume = ref(''), enabled = ref(false), onlySaved = ref(false), warning = ref(''), expanded = ref(new Set()), shareMessage = ref(''), shareFallback = ref('')
const storage = { getItem: key => window.localStorage.getItem(key), setItem: (key, data) => window.localStorage.setItem(key, data), removeItem: key => window.localStorage.removeItem(key) }
const benefits = ['死亡率', '时间', '金钱', '自由']
let controller, generation = 0, queryTimer
const results = computed(() => filterEntries(chapters.value, { query: query.value, chapter: chapter.value, evidence: evidence.value, benefit: benefit.value, money: money.value, value: value.value }).filter(entry => !onlySaved.value || saved.value.includes(entry.id)))
const pages = computed(() => Math.max(1, Math.ceil(results.value.length / 12))), paged = computed(() => results.value.slice((page.value - 1) * 12, page.value * 12)), currentChapter = computed(() => chapters.value.find(c => c.number === Number(chapter.value)))
function state() { return { q: query.value, chapter: chapter.value, evidence: evidence.value, benefit: benefit.value, money: money.value, value: value.value, page: page.value } }
function syncUrl(extra = {}) { const query = guideQuery({ ...state(), ...extra }); if (new URLSearchParams(query).toString() !== new URLSearchParams(route.query).toString()) router.replace({ path: '/life-guide', query }) }
function applyRoute() { const data = parseGuideQuery(route.query); query.value = data.q; chapter.value = data.chapter; evidence.value = data.evidence; benefit.value = data.benefit; money.value = data.money; value.value = data.value; page.value = data.page; pendingEntry.value = data.entry; if (data.entry) jump(data.entry, false) }
watch(() => route.query, applyRoute); applyRoute()
function filtersChanged() { page.value = 1; pendingEntry.value = ''; clearTimeout(queryTimer); queryTimer = setTimeout(() => syncUrl(), 150) }
function persist() { if (enabled.value) warning.value = writeReader(storage, { enabled: true, saved: saved.value, resume: resume.value }) }
function persistenceChanged() { warning.value = writeReader(storage, { enabled: enabled.value, saved: saved.value, resume: resume.value }) }
function save(id) { saved.value = saved.value.includes(id) ? saved.value.filter(item => item !== id) : [...saved.value, id]; persist(); if (onlySaved.value && page.value > pages.value) { page.value = pages.value; syncUrl() } }
function clearRecords() { enabled.value = false; saved.value = []; resume.value = ''; warning.value = writeReader(storage, { enabled: false }); page.value = 1; syncUrl() }
function toggleEntry(id, event) { const set = new Set(expanded.value); if (event.target.open) { set.add(id); resume.value = id; persist() } else set.delete(id); expanded.value = set }
async function jump(id, updateUrl = true) {
  const entry = filterEntries(chapters.value).find(item => item.id === id)
  if (!entry) { if (!indexing.value && manifest.value) warning.value = '这条原文尚未加载或编号不存在，请重试加载。'; return }
  clearTimeout(queryTimer); query.value = ''; chapter.value = String(entry.chapter); evidence.value = ''; benefit.value = ''; money.value = ''; value.value = ''; onlySaved.value = false
  page.value = Math.floor((entry.number - 1) / 12) + 1; expanded.value = new Set([id]); pendingEntry.value = ''; if (updateUrl) syncUrl({ entry: id })
  await nextTick(); if (!controller?.signal.aborted) { const node = document.getElementById(`entry-${id}`); node?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }); node?.focus({ preventScroll: true }) }
}
async function share(id) {
  const params = new URLSearchParams(id ? { entry: id } : guideQuery(state())), url = `${window.location.origin}/life-guide${params.size ? `?${params}` : ''}`
  try { await navigator.clipboard.writeText(url); shareMessage.value = '链接已复制。只分享原文条目或筛选条件，不包含你的收藏记录。'; shareFallback.value = '' }
  catch { shareMessage.value = '浏览器未允许自动复制，请选中下面的链接手动复制。'; shareFallback.value = url }
}
async function load() {
  controller?.abort(); controller = new AbortController(); const signal = controller.signal, request = ++generation
  loading.value = !chapters.value.length; indexing.value = true; error.value = ''
  try {
    const data = await guideLoader.manifest(signal); if (request !== generation) return; manifest.value = data
    const priority = Number(pendingEntry.value.split('-')[0] || chapter.value || 1), ordered = [...data.chapters].sort((a, b) => Number(b.number === priority) - Number(a.number === priority))
    let cursor = 0, failed = 0
    await Promise.all(Array.from({ length: 4 }, async () => {
      while (cursor < ordered.length && !signal.aborted) {
        const item = ordered[cursor++]
        try {
          const result = await guideLoader.chapter(item, signal); if (request !== generation) return
          chapters.value = [...chapters.value.filter(c => c.number !== item.number), result].sort((a, b) => a.number - b.number); loaded.value = chapters.value.length; loading.value = false
          if (pendingEntry.value && result.number === Number(pendingEntry.value.split('-')[0])) await jump(pendingEntry.value)
        } catch (cause) { if (cause.name === 'AbortError' || signal.aborted) return; failed++ }
      }
    }))
    if (request === generation && !signal.aborted) {
      if (failed) error.value = `${failed} 个章节未能加载，已加载的原文仍可阅读。`
      if (loaded.value === data.chapters.length) { const ids = new Set(filterEntries(chapters.value).map(e => e.id)); saved.value = saved.value.filter(id => ids.has(id)); if (resume.value && !ids.has(resume.value)) resume.value = ''; persist() }
      if (pendingEntry.value) { await jump(pendingEntry.value); if (pendingEntry.value) warning.value = '这个条目编号不存在或章节未能加载，请核对链接。' }
      if (page.value > pages.value) { page.value = pages.value; syncUrl() }
    }
  } catch (cause) { if (request === generation && cause.name !== 'AbortError') error.value = cause.message || '暂时无法加载原文。' }
  finally { if (request === generation) { loading.value = false; indexing.value = false } }
}
function reset() { query.value = ''; chapter.value = ''; evidence.value = ''; benefit.value = ''; money.value = ''; value.value = ''; onlySaved.value = false; page.value = 1; pendingEntry.value = ''; clearTimeout(queryTimer); syncUrl() }
function turn(delta) { clearTimeout(queryTimer); page.value = Math.max(1, Math.min(pages.value, page.value + delta)); syncUrl(); document.querySelector('.guide-meta')?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }) }
onMounted(() => { const state = readReader(storage); enabled.value = state.enabled; saved.value = state.saved; resume.value = state.resume; warning.value = state.warning; load() })
onUnmounted(() => { generation++; controller?.abort(); clearTimeout(queryTimer) })
</script>
<style scoped>
.guide-heading{padding:35px 0 25px}.guide-heading h1{font-size:clamp(42px,6vw,76px);line-height:1.12;letter-spacing:-.05em;margin:20px 0}.guide-heading h1 span{color:#7a6852}.guide-heading>p:last-child{color:var(--muted);font-size:16px}.guide-disclaimer{font-size:14px;line-height:1.9;padding:18px 22px;background:#f1eee8;border:1px solid #e8e1d6;border-radius:16px;color:#675a49}
.guide-reader{display:flex;gap:24px;justify-content:space-between;align-items:center;background:linear-gradient(120deg,#fff,#f2f5f8);border:1px solid var(--border);border-radius:22px;padding:25px;margin-top:24px}.guide-reader h2{font-size:23px;letter-spacing:-.03em}.guide-reader p:last-child{font-size:14px;line-height:1.9;color:var(--muted);max-width:480px}.guide-reader-actions{display:grid;gap:12px;flex-shrink:0}.guide-reader-actions label{display:flex;align-items:center;gap:8px;font-size:14px}.guide-reader-actions input{width:16px;height:16px;min-height:0;padding:0;margin:0;box-shadow:none}.guide-reader-actions button{text-align:left;font-size:14px}.guide-notice{font-size:14px;line-height:1.8;color:#766045}
.guide-filters{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;padding:25px;background:#fff;border:1px solid var(--border);border-radius:22px;margin:25px 0}.guide-filters label{font-size:14px;color:var(--muted);display:grid;gap:8px}.guide-search{grid-column:1/-1}.guide-filters input,.guide-filters select,.guide-share input{width:100%;font-size:16px;min-width:0;padding:12px;border:1px solid var(--border);border-radius:10px;background:#fafafb;color:var(--ink)}.guide-filter-actions{display:flex;gap:16px;align-items:center;grid-column:1/-1;flex-wrap:wrap}.guide-filter-actions button{font-size:14px}.guide-meta{display:flex;gap:16px;justify-content:space-between;margin:30px 0 18px;color:var(--muted);font-size:14px;scroll-margin-top:100px}.guide-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;align-items:start}.guide-card{border:1px solid var(--border);background:#fff;border-radius:20px;padding:24px;min-width:0;scroll-margin-top:100px}.guide-card:focus-visible{outline:2px solid #7c9dc2;outline-offset:4px}.guide-entry-meta{display:flex;justify-content:space-between;font-size:14px;color:var(--muted);gap:12px}.guide-entry-meta span:last-child{color:#27774d}.guide-card h2{font-size:20px;line-height:1.55;margin:18px 0 12px;overflow-wrap:anywhere}.guide-card>p{font-size:16px;line-height:1.9;color:var(--muted);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}.guide-tags{display:flex;gap:7px;flex-wrap:wrap;margin:18px 0}.guide-tags span{font-size:14px;padding:5px 8px;background:#f5f5f7;border-radius:6px;color:#62646b}.guide-card-actions{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px}.guide-card-actions button{border:1px solid var(--border);background:#fafafb;color:#57677b;cursor:pointer;font-size:14px;padding:9px 12px;border-radius:99px}.guide-card-actions button[aria-pressed=true]{background:#edf4fc;color:#0066cc;border-color:#a2bfdd}.guide-card summary{cursor:pointer;font-size:14px;color:#0066cc;padding:10px 0}.guide-original{font-size:16px;line-height:1.9;overflow-wrap:anywhere;border-top:1px solid var(--border);padding-top:16px}.guide-original :deep(h3){font-size:16px}.guide-original :deep(li){margin-bottom:16px}.guide-intro,.guide-explainer,.guide-share{background:#fff;border:1px solid var(--border);border-radius:20px;padding:25px;margin:20px 0}.guide-explainer h2{font-size:22px}.guide-explainer p,.guide-attribution,.guide-share{font-size:14px;line-height:1.9;color:var(--muted)}.guide-attribution{padding:20px 0;overflow-wrap:anywhere}.guide-attribution a{color:#0066cc;text-decoration:underline}.guide-pagination{display:flex;justify-content:center;gap:20px;align-items:center;margin:25px;font-size:14px}.guide-pagination button{border:1px solid var(--border);background:#fff;border-radius:99px;padding:10px 18px;color:var(--ink);cursor:pointer}.guide-pagination button:disabled{opacity:.4;cursor:default}@media(max-width:850px){.guide-reader{align-items:start;flex-direction:column}.guide-reader-actions{flex-shrink:1;width:100%}}@media(max-width:700px){.guide-filters{grid-template-columns:repeat(2,minmax(0,1fr));padding:18px}.guide-results{grid-template-columns:1fr}.guide-meta{flex-direction:column;gap:8px}.guide-card,.guide-reader{padding:20px}}
</style>
