<template>
  <main class="content-page guide-page">
    <header class="guide-heading"><p class="section-kicker">THE EVIDENCE-BASED LIFE / A READING SPACE</p><h1>把生活，<br><span>过得更明白。</span></h1><p>高性价比人生指南 · 按原文查阅，而不是让 AI 替你猜。</p></header>
    <p class="guide-disclaimer">这是一份备选清单，不是任务清单。正文由原作者维护，不替代医生、律师或会计。急症请先求助急救；法律、补贴和政策请核对最新官方规定。</p>
    <div v-if="loading" class="state-text" role="status">正在加载原文…{{ loaded }} / {{ manifest?.chapters.length || 34 }} 章</div>
    <div v-if="error" class="state-text" role="alert">{{ error }} <button class="text-button" type="button" @click="load">重新加载</button></div>
    <template v-if="manifest && !loading && !error">
      <form class="guide-filters" @submit.prevent="page = 1"><label class="guide-search">全文检索<input v-model="query" type="search" placeholder="例如：租房、睡眠、借条，空格分隔多个词" maxlength="100" /></label><label>章节<select v-model="chapter"><option value="">全部章节</option><option v-for="item in manifest.chapters" :key="item.number" :value="String(item.number)">第 {{ item.number }} 节 · {{ item.title }}</option></select></label><label>证据等级<select v-model="evidence"><option value="">全部证据</option><option>A</option><option>B</option><option>C</option></select></label><label>换回什么<select v-model="benefit"><option value="">全部口径（不混合排名）</option><option v-for="item in benefits" :key="item">{{ item }}</option></select></label><label>金钱成本<select v-model="money"><option value="">不限成本</option><option value="0">不花钱</option><option value="少">少</option><option value="多">多</option></select></label><label>作者性价比档<select v-model="value"><option value="">全部档位</option><option>极高</option><option>高</option><option>一般</option></select></label><button class="button button-secondary" type="button" @click="reset">清空筛选</button></form>
      <div class="guide-meta"><span>{{ results.length }} / {{ manifest.count }} 条 · {{ manifest.chapters.length }} 节</span><span>原文顺序 · 证据 ≠ 性价比 · 不同收益不折算</span></div>
      <section v-if="currentChapter" class="guide-intro markdown-body" v-html="renderMarkdown(resolveSourceLinks(currentChapter.intro, manifest.commit, currentChapter.file))" />
      <p v-if="!results.length" class="state-text">没有找到符合条件的原文。换个关键词，或清空筛选。</p>
      <div class="guide-results"><article v-for="entry in paged" :key="entry.id" class="guide-card" :id="`entry-${entry.id}`"><div class="guide-entry-meta"><span>第 {{ entry.chapter }} 节 · 第 {{ entry.number }} 条</span><span>证据 {{ entry.evidence || '未标注' }}</span></div><h2>{{ entry.title }}</h2><p>{{ entry.summary || '展开查看完整原文、来源和适用条件。' }}</p><div class="guide-tags"><span v-if="entry.tags.口径">换{{ entry.tags.口径 }}</span><span>性价比：{{ entry.ratio }}</span><span v-if="/争议/.test(entry.markdown)">含争议，阅读备注</span><span v-if="/TODO|待核实/.test(entry.markdown)">含待核实内容</span></div><details><summary>阅读完整原文、来源与备注</summary><div class="markdown-body guide-original" v-html="renderMarkdown(resolveSourceLinks(entry.markdown, manifest.commit, entry.file))" /><a class="text-button" :href="sourceUrl(manifest.commit, entry.file)" target="_blank" rel="noopener noreferrer">核对这一节的原文 ↗</a></details></article></div>
      <nav v-if="pages > 1" class="guide-pagination" aria-label="原文分页"><button type="button" :disabled="page <= 1" @click="turn(-1)">上一页</button><span>{{ page }} / {{ pages }}</span><button type="button" :disabled="page >= pages" @click="turn(1)">下一页</button></nav>
      <section class="guide-explainer"><h2>怎么读这些标签？</h2><p>A / B / C 是原书标注的证据等级，不保证对每个人适用，也不代表因果确定。性价比档来自作者的成本与收益量级判断，本身不是医学或法律证据。钱、时间、寿命和人身自由各算各的。</p><p>展开条目会保留完整来源和备注；有争议或待核实的内容不能当成定论。本页没有个性化建议，也不调用模型 API。</p></section>
      <footer class="guide-attribution"><p>《高性价比人生指南》 · {{ manifest.author }} · <a :href="manifest.source" target="_blank" rel="noopener noreferrer">原始仓库</a> · <a :href="manifest.licenseUrl" target="_blank" rel="noopener noreferrer">CC BY 4.0</a> · <a href="/life-guide/LICENSE.txt">完整许可</a></p><p>同步日期 {{ manifest.syncedAt }} · 版本 {{ manifest.commit.slice(0, 12) }}。{{ manifest.changes }} 原作者未为本站背书；内容按原作者原样提供，不保证持续更新。</p></footer>
    </template>
  </main>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { renderMarkdown } from '../utils/markdown'
import { filterEntries, resolveSourceLinks, sourceUrl } from '../features/life-guide/library'
const route = useRoute(), router = useRouter(), manifest = ref(null), chapters = ref([]), loading = ref(false), error = ref(''), loaded = ref(0)
const query = ref(String(route.query.q || '').slice(0, 100)), chapter = ref(String(route.query.chapter || '')), evidence = ref(''), benefit = ref(''), money = ref(''), value = ref(''), page = ref(1)
let controller, generation = 0
const benefits = computed(() => [...new Set(chapters.value.flatMap(c => c.entries.map(e => e.tags.口径)).filter(Boolean))])
const results = computed(() => filterEntries(chapters.value, { query: query.value, chapter: chapter.value, evidence: evidence.value, benefit: benefit.value, money: money.value, value: value.value }))
const pages = computed(() => Math.ceil(results.value.length / 12)), paged = computed(() => results.value.slice((page.value - 1) * 12, page.value * 12)), currentChapter = computed(() => chapters.value.find(c => c.number === Number(chapter.value)))
watch([query, chapter, evidence, benefit, money, value], () => { page.value = 1 })
watch([query, chapter], () => { router.replace({ path: '/life-guide', query: { ...(query.value ? { q: query.value } : {}), ...(chapter.value ? { chapter: chapter.value } : {}) }, hash: route.hash }) })
async function readJson(url, signal) { const response = await fetch(url, { signal }); if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('原文资源暂时不可用。'); return response.json() }
async function load() {
  controller?.abort(); controller = new AbortController(); const signal = controller.signal, request = ++generation
  loading.value = true; error.value = ''; loaded.value = 0
  try {
    const data = await readJson('/life-guide/manifest.json', signal)
    if (data.commit !== 'b4048d14960fec19c0367f8c0e6891f2b038c7ef' || data.chapters.length !== 34) throw new Error('原文版本不匹配，请刷新后重试。')
    manifest.value = data
    const collected = []; let cursor = 0
    await Promise.all(Array.from({ length: 4 }, async () => {
      while (cursor < data.chapters.length) {
        const index = cursor++, item = data.chapters[index]
        if (!/^\/life-guide\/chapter-\d{2}\.json$/.test(item.url)) throw new Error('原文章节路径异常。')
        const result = await readJson(item.url, signal)
        if (result.number !== item.number || result.entries.length !== item.count) throw new Error('原文章节不完整。')
        collected[index] = result; if (request === generation) loaded.value++
      }
    }))
    if (request === generation) chapters.value = collected
  } catch (cause) { if (request === generation && cause.name !== 'AbortError') { error.value = cause.message || '暂时无法加载原文。'; controller.abort() } }
  finally { if (request === generation) loading.value = false }
}
function reset() { query.value = ''; chapter.value = ''; evidence.value = ''; benefit.value = ''; money.value = ''; value.value = '' }
function turn(delta) { page.value = Math.max(1, Math.min(pages.value, page.value + delta)); document.querySelector('.guide-meta')?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }) }
onMounted(load)
onUnmounted(() => { generation++; controller?.abort() })
</script>
<style scoped>
.guide-heading{padding:35px 0 25px}.guide-heading h1{font-size:clamp(42px,6vw,76px);line-height:1.12;letter-spacing:-.05em;margin:20px 0}.guide-heading h1 span{color:#7a6852}.guide-heading>p:last-child{color:var(--muted);font-size:16px}.guide-disclaimer{font-size:12px;line-height:1.9;padding:18px 22px;background:#f1eee8;border:1px solid #e8e1d6;border-radius:16px;color:#675a49}.guide-filters{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;padding:25px;background:#fff;border:1px solid var(--border);border-radius:22px;margin:25px 0}.guide-filters label{font-size:11px;color:var(--muted);display:grid;gap:8px}.guide-search{grid-column:1/-1}.guide-filters input,.guide-filters select{width:100%;font-size:13px;min-width:0;padding:12px;border:1px solid var(--border);border-radius:10px;background:#fafafb;color:var(--ink)}.guide-filters button{align-self:end;font-size:12px}.guide-meta{display:flex;gap:16px;justify-content:space-between;margin:30px 0 18px;color:var(--muted);font-size:12px;scroll-margin-top:100px}.guide-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;align-items:start}.guide-card{border:1px solid var(--border);background:#fff;border-radius:20px;padding:24px;min-width:0}.guide-entry-meta{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);gap:12px}.guide-entry-meta span:last-child{color:#27774d}.guide-card h2{font-size:20px;line-height:1.55;margin:18px 0 12px;overflow-wrap:anywhere}.guide-card>p{font-size:13px;line-height:1.9;color:var(--muted);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}.guide-tags{display:flex;gap:7px;flex-wrap:wrap;margin:18px 0}.guide-tags span{font-size:10px;padding:5px 8px;background:#f5f5f7;border-radius:6px;color:#62646b}.guide-card summary{cursor:pointer;font-size:12px;color:#0066cc;padding:10px 0}.guide-original{font-size:13px;line-height:1.9;overflow-wrap:anywhere;border-top:1px solid var(--border);padding-top:16px}.guide-original :deep(h3){font-size:16px}.guide-original :deep(li){margin-bottom:16px}.guide-intro,.guide-explainer{background:#fff;border:1px solid var(--border);border-radius:20px;padding:25px;margin:20px 0}.guide-explainer h2{font-size:22px}.guide-explainer p,.guide-attribution{font-size:12px;line-height:1.9;color:var(--muted)}.guide-attribution{padding:20px 0;overflow-wrap:anywhere}.guide-attribution a{color:#0066cc;text-decoration:underline}.guide-pagination{display:flex;justify-content:center;gap:20px;align-items:center;margin:25px;font-size:12px}.guide-pagination button{border:1px solid var(--border);background:#fff;border-radius:99px;padding:10px 18px;color:var(--ink);cursor:pointer}.guide-pagination button:disabled{opacity:.4;cursor:default}@media(max-width:700px){.guide-filters{grid-template-columns:repeat(2,minmax(0,1fr));padding:18px}.guide-results{grid-template-columns:1fr}.guide-meta{flex-direction:column;gap:8px}.guide-card{padding:20px}.guide-filters button{grid-column:1/-1}}
</style>
