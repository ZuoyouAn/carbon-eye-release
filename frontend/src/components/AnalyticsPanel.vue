<template>
  <section class="traffic-panel" aria-label="访问统计">
    <div class="traffic-heading"><div><h2>访问统计</h2><p>页面浏览与匿名访客 · 北京时间</p></div><div class="traffic-filters"><label>站点<select v-model="site"><option value="all">全部站点</option><option value="space">左右的Space</option><option value="video">左右视频站</option></select></label><label>范围<select v-model="days"><option :value="7">近 7 天</option><option :value="30">近 30 天</option><option :value="90">近 90 天</option></select></label><button class="button button-secondary" :disabled="loading" @click="load">刷新</button></div></div>
    <p v-if="error" role="alert" class="traffic-error">{{ error }}</p>
    <p v-if="loading" role="status">正在读取统计…</p>
    <template v-if="data">
      <div class="traffic-cards"><article><span>今日浏览 · PV</span><strong>{{ number(data.today.pv) }}</strong></article><article><span>今日访客 · UV</span><strong>{{ number(data.today.uv) }}</strong></article><article><span>近 {{ data.days }} 天浏览</span><strong>{{ number(data.totals.pv) }}</strong></article><article><span>近 {{ data.days }} 天访客</span><strong>{{ number(data.totals.uv) }}</strong></article></div>
      <div class="traffic-sites"><span v-for="item in data.sites" :key="item.site">{{ siteName(item.site) }}：{{ number(item.pv) }} 次浏览 / {{ number(item.uv) }} 个匿名访客</span></div>
      <section class="traffic-chart"><h3>浏览趋势</h3><p v-if="!data.totals.pv">当前范围暂无记录。上线前的访问量不会补算。</p><div class="traffic-bars" role="img" :aria-label="chartLabel"><div v-for="day in data.series" :key="day.date" class="traffic-bar-column" :title="`${day.date}：PV ${day.pv} / UV ${day.uv}`"><div class="traffic-bar-space"><i :style="{ height: day.pv ? `${Math.max(2, day.pv / peak * 100)}%` : '0%' }"></i></div><small v-if="data.days <= 7">{{ day.date.slice(5) }}</small></div></div><p class="traffic-chart-range">{{ data.from }} — {{ data.to }} · 悬停查看每日 PV / UV</p></section>
      <section class="traffic-pages"><h3>热门页面</h3><div class="traffic-table-wrap"><table><thead><tr><th>站点</th><th>页面</th><th>浏览 PV</th><th>访客 UV</th></tr></thead><tbody><tr v-for="row in data.top_pages" :key="`${row.site}:${row.path}`"><td>{{ siteName(row.site) }}</td><td>{{ pageName(row.path) }}<small>{{ row.path }}</small></td><td>{{ number(row.pv) }}</td><td>{{ number(row.uv) }}</td></tr><tr v-if="!data.top_pages.length"><td colspan="4">暂无访问记录</td></tr></tbody></table></div></section>
      <p class="traffic-footnote">开始记录：{{ formatDate(data.started_at) }}；保留 {{ data.retention_days }} 天。UV 是匿名浏览器估计，不等于真实人数；两站分别去重，清除存储或 30 天标识轮换可能产生新访客。放映厅轮询、视频分片、管理员、自动化测试及选择退出的浏览器不计入。公开上报可被伪造，不用于计费或安全审计。</p>
    </template>
  </section>
</template>
<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { apiRequest } from '../api/client'
const site = ref('all'), days = ref(7), data = ref(null), loading = ref(false), error = ref('')
let abort = null
const peak = computed(() => Math.max(1, ...(data.value?.series || []).map(day => day.pv)))
const chartLabel = computed(() => (data.value?.series || []).map(day => `${day.date} 浏览 ${day.pv} 访客 ${day.uv}`).join('；'))
const number = value => new Intl.NumberFormat('zh-CN').format(value || 0)
const siteName = value => value === 'space' ? '左右的Space' : '左右视频站'
const names = { '/': '首页', '/watch': '视频播放', '/cinema': '放映厅', '/libretv': '视频站入口', '/live': '直播', '/about': '关于', '/projects': '项目', '/human3': '成长评估', '/articles': '文章', '/articles/:id': '文章详情', '/posts/:id': '帖子详情', '/novels/:id': '小说阅读', '/games': '游戏大厅', '/games/swarm': '星潮幸存者', '/games/winter': '寒境火种', '/solar-system': '太阳系图谱' }
const pageName = path => names[path] || path
const formatDate = value => new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
async function load() {
  abort?.abort(); const current = new AbortController(); abort = current
  loading.value = true; error.value = ''; data.value = null
  try { const result = await apiRequest(`/api/admin/analytics?site=${site.value}&days=${days.value}`, { signal: current.signal }); if (!current.signal.aborted) data.value = result }
  catch (failure) { if (!current.signal.aborted) error.value = failure.message || '统计读取失败，请稍后重试' }
  finally { if (abort === current) loading.value = false }
}
watch([site, days], load, { immediate: true })
onBeforeUnmount(() => abort?.abort())
</script>
<style scoped>
.traffic-panel{padding:18px 0}.traffic-heading{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;align-items:center}.traffic-heading h2{font-size:26px;margin:0 0 8px}.traffic-heading p,.traffic-footnote,.traffic-chart-range{color:#68758b;font-size:14px;line-height:1.8}.traffic-filters{display:flex;flex-wrap:wrap;align-items:end;gap:12px}.traffic-filters label{display:grid;gap:6px;font-size:13px}.traffic-filters select{padding:9px 12px;border:1px solid #ccd5e3;border-radius:9px;background:white;color:#253650}.traffic-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:26px 0 16px}.traffic-cards article{padding:22px;border:1px solid #dfe6f0;border-radius:17px;background:linear-gradient(145deg,#f8faff,white)}.traffic-cards span{color:#60718d;font-size:14px}.traffic-cards strong{display:block;font-size:34px;margin-top:14px;color:#254d94;font-variant-numeric:tabular-nums}.traffic-sites{display:flex;gap:22px;flex-wrap:wrap;font-size:14px;color:#5b6d86}.traffic-chart,.traffic-pages{border:1px solid #e0e5ed;border-radius:17px;padding:24px;margin-top:24px;background:#fff}.traffic-panel h3{font-size:18px;margin:0 0 18px}.traffic-bars{display:flex;align-items:stretch;gap:clamp(2px,1vw,14px);height:185px}.traffic-bar-column{flex:1;min-width:0;display:flex;flex-direction:column;gap:8px;text-align:center}.traffic-bar-space{height:155px;display:flex;align-items:end;background:linear-gradient(#f6f8fd,#f6f8fd);border-bottom:1px solid #d3dcea;border-radius:7px 7px 0 0}.traffic-bar-space i{display:block;background:linear-gradient(#6f9be7,#3567bb);width:100%;border-radius:5px 5px 0 0}.traffic-bar-column small{font-size:11px;color:#64768f}.traffic-table-wrap{overflow-x:auto}.traffic-pages table{width:100%;border-collapse:collapse;text-align:left;font-size:14px;min-width:360px}.traffic-pages th,.traffic-pages td{padding:14px 10px;border-bottom:1px solid #e9edf3}.traffic-pages th{color:#63748c;font-weight:500}.traffic-pages td small{display:block;color:#8290a5;font-size:12px;margin-top:6px}.traffic-footnote{margin-top:22px}.traffic-error{background:#fff2ef;color:#a53b2e;padding:14px;border-radius:10px}@media(max-width:700px){.traffic-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.traffic-cards article{padding:16px}.traffic-cards strong{font-size:29px}.traffic-chart,.traffic-pages{padding:16px}.traffic-filters{gap:9px}.traffic-filters select{max-width:150px}.traffic-sites{gap:8px;flex-direction:column}}
</style>
