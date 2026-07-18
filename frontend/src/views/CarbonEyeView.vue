<template>
  <main class="content-page">
    <section class="carbon-eye-page">
      <header class="carbon-topbar">
        <RouterLink class="back-link" to="/projects">返回项目</RouterLink>
        <span>数据版本 {{ overview?.dataVersion?.system_version || '-' }}</span>
      </header>

      <section class="carbon-header">
        <div>
          <p class="eyebrow">Carbon Eye / v2.0</p>
          <h1>园区碳眼</h1>
          <p>{{ overview?.positioning }}</p>
        </div>
        <div class="boundary-banner">
          城市空气质量仅作区域背景；园区碳结果为购电间接排放位置法代理估算，不代表园区总碳排放或正式碳核算。
        </div>
      </section>

      <div v-if="loading" class="carbon-state">正在加载专题数据...</div>
      <div v-else-if="error" class="carbon-error">{{ error }}</div>

      <template v-else>
        <section class="metric-grid" aria-label="专题驾驶舱">
          <article class="metric-card">
            <span>实时 AQI 状态</span>
            <strong>{{ realtimeAqi?.status === 'ok' ? realtimeAqi?.items?.find((item) => item.pollutant === 'aqi')?.current_value ?? '-' : '暂不可用' }}</strong>
            <p>{{ realtimeStatus }}</p>
          </article>
          <article class="metric-card">
            <span>最新完整月 PRI</span>
            <strong>{{ latestMonthly?.absolute_risk_score ?? '-' }}</strong>
            <p>{{ latestMonthly?.date }} · {{ latestMonthly?.absolute_risk_level }} · {{ latestMonthly?.main_contributor }}</p>
          </article>
          <article class="metric-card">
            <span>最新购电间接排放代理</span>
            <strong>{{ latestParkProxy?.total_purchased_electricity_scope2_10k_tco2 ?? '-' }}</strong>
            <p>万吨 CO2 · {{ latestParkProxy?.year || '-' }} 年</p>
          </article>
          <article class="metric-card">
            <span>年度 EAI / CEI</span>
            <strong>{{ latestAnnualDimension ? `${latestAnnualDimension.eai} / ${latestAnnualDimension.cei}` : '-' }}</strong>
            <p>{{ latestAnnualDimension?.year || '-' }} 年年度能源活动 / 排放强度代理</p>
          </article>
          <article class="metric-card">
            <span>数据质量</span>
            <strong>{{ dataQuality?.weather_months ?? '-' }}</strong>
            <p>气象月度记录 · 6 点位 · {{ dataQuality?.snapshot_records ?? '-' }} 条快照记录</p>
          </article>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">City Background</p>
              <h2>城市长期空气质量与污染压力</h2>
            </div>
            <p>单位：AQI 或 µg/m3；时间：2013-12 至 2026-07。月度空气质量为苏州市级背景，风险指数用于排序和解释。</p>
          </div>
          <div class="section-note">
            最新部分月 <b>2026-07</b> 已标记，不参与年度统计、历史阈值、训练基线或气象相关分析。
          </div>
          <div v-if="monthlyTrends.length" ref="trendChartRef" class="chart chart-tall"></div>
          <div v-else class="chart-empty">暂无城市长期趋势数据</div>
        </section>

        <section class="two-column">
          <article class="carbon-section compact-section">
            <div class="section-heading">
              <div>
                <p class="eyebrow">Weather</p>
                <h2>园区六点位 ERA5 长期气象</h2>
              </div>
              <p>单位：°C、mm、km/h；2013-12 至 2026-06；六个官方点位空间平均。</p>
            </div>
            <div v-if="weatherRecords.length" ref="weatherChartRef" class="chart chart-medium"></div>
            <div v-else class="chart-empty">暂无长期气象数据</div>
            <p class="figure-note">气象变量只用于描述性解释，相关不等于因果。</p>
          </article>

          <article class="carbon-section compact-section">
            <div class="section-heading">
              <div>
                <p class="eyebrow">Correlation</p>
                <h2>气象-污染描述性相关</h2>
              </div>
              <p>展示去季节 Pearson r；每格同时保留 Pearson、Spearman、样本量和非因果警告。</p>
            </div>
            <div v-if="weatherCorrelations.length" ref="correlationChartRef" class="chart chart-medium"></div>
            <div v-else class="chart-empty">暂无相关性分析结果</div>
            <p class="figure-note">重点对包括 O3-温度/日照/短波辐射、PM2.5-风速/降水/湿度、NO2-风速/气压。</p>
          </article>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Park Snapshot</p>
              <h2>2026年6月园区六点位特征因子监测快照</h2>
            </div>
            <p>{{ parkSnapshot?.site_count || 0 }} 点位 · {{ parkSnapshot?.monitoring_days || 0 }} 天 · {{ parkSnapshot?.pollutant_count || 0 }} 项因子 · {{ parkSnapshot?.records?.length || 0 }} 条记录。</p>
          </div>
          <div class="section-note warning-note">本模块为官方短期补充监测快照，不代表全年均值或实时序列；不基于此快照识别具体污染企业。</div>
          <div class="site-layout">
            <div class="site-list">
              <button
                v-for="site in parkSnapshot?.sites || []"
                :key="site.site_id"
                class="site-button"
                :class="{ active: selectedSiteId === site.site_id }"
                type="button"
                @click="selectedSiteId = site.site_id"
              >
                <strong>{{ site.site_id }}</strong>
                <span>{{ site.site_name }}</span>
                <small>{{ site.functional_zone }}</small>
              </button>
            </div>
            <div class="snapshot-detail">
              <div class="snapshot-selected">
                <div>
                  <span>当前点位</span>
                  <strong>{{ selectedSnapshotSite?.site_name || '-' }}</strong>
                </div>
                <p>{{ selectedSnapshotSite?.functional_zone }}</p>
              </div>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>特征因子</th>
                      <th>观测范围</th>
                      <th>评价限值</th>
                      <th>单位</th>
                      <th>状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in selectedSnapshotRecords" :key="`${item.site_id}-${item.pollutant}`">
                      <td>{{ item.pollutant }}</td>
                      <td>{{ displaySnapshotRange(item.observed_range) }}</td>
                      <td>{{ item.reference_limit ?? '-' }}</td>
                      <td>{{ item.unit }}</td>
                      <td>{{ item.compliance }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        <section class="two-column">
          <article class="carbon-section compact-section">
            <div class="section-heading">
              <div>
                <p class="eyebrow">City CO2 Background</p>
                <h2>苏州市年度 CO2 背景</h2>
              </div>
              <p>城市级年度背景；不代表园区碳排放，不参与日级预警。</p>
            </div>
            <div v-if="cityCarbon.length" ref="cityCarbonChartRef" class="chart chart-medium"></div>
            <div v-else class="chart-empty">暂无城市 CO2 背景数据</div>
          </article>

          <article class="carbon-section compact-section">
            <div class="section-heading">
              <div>
                <p class="eyebrow">Electricity Proxy</p>
                <h2>苏州工业园区购电间接排放估算（位置法代理值）</h2>
              </div>
              <p>单位：亿 kWh、万吨 CO2；2019、2023-2025 有值，2020-2022 为真实缺口。</p>
            </div>
            <div v-if="parkElectricityRecords.length" ref="parkCarbonChartRef" class="chart chart-medium"></div>
            <div v-else class="chart-empty">暂无园区购电代理数据</div>
          </article>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Intensity</p>
              <h2>园区用电与购电间接排放强度代理</h2>
            </div>
            <p>每万元 GDP 或规上工业总产值的宏观代理指标；不能替代企业或产品碳强度。</p>
          </div>
          <div v-if="economicIntensityRecords.length" ref="intensityChartRef" class="chart chart-medium"></div>
          <div v-else class="chart-empty">暂无经济强度代理数据</div>
          <div class="section-note">固定电力排放因子：2023 江苏 0.5827 kgCO2/kWh。2019、2024、2025采用统一因子横向比较情景，不是对应年度正式清单。</div>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Three Dimensions</p>
              <h2>PRI / EAI / CEI 三维协同态势</h2>
            </div>
            <p>PRI 为月度污染压力；EAI 和 CEI 为年度背景。默认展示三维态势，避免将高度相关的用电与购电代理简单重复计量。</p>
          </div>
          <div v-if="cdciRecords.length" ref="cdciChartRef" class="chart chart-tall"></div>
          <div v-else class="chart-empty">暂无实验性协同态势数据</div>
          <div class="experimental-note">
            <b>减污降碳协同态势指数（实验性原型）</b>：{{ cdci?.formula }}。仅对 2019、2023、2024、2025 的可用年度背景计算；月份映射年度背景属于混合时间频率，不是实时 CDCI。
          </div>
          <div class="table-wrap sensitivity-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>权重方案</th>
                  <th>排名 Spearman</th>
                  <th>高风险月重合率</th>
                  <th>等级变化率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in cdciSensitivity?.comparisons || []" :key="item.scenario">
                  <td>{{ item.scenario }}</td>
                  <td>{{ item.rank_spearman ?? '-' }}</td>
                  <td>{{ percent(item.high_risk_month_overlap_rate) }}</td>
                  <td>{{ percent(item.level_change_rate) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Warning Review</p>
              <h2>相对异常与绝对风险</h2>
            </div>
            <p>同月历史阈值超出与当前污染压力等级为两项独立判断。</p>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>月份</th>
                  <th>是否超过历史同月阈值</th>
                  <th>触发项</th>
                  <th>绝对风险</th>
                  <th>主要贡献污染物</th>
                  <th>适用治理建议</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in warnings" :key="item.date">
                  <td>{{ item.date }}</td>
                  <td>是</td>
                  <td>{{ item.anomaly_items?.join('；') }}</td>
                  <td>{{ item.absolute_risk_score }} · {{ item.absolute_risk_level }}</td>
                  <td>{{ item.main_contributor }} · {{ item.main_risk_type }}</td>
                  <td>{{ item.governance_advice }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Daily Replay</p>
              <h2>日级历史案例回放</h2>
            </div>
            <p>时间范围：2013-12-02 至 2015-07-31。日表 20 个月中 18 个月完成字段纠偏，平均相对误差约 0.0182。</p>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>AQI</th>
                  <th>PM2.5</th>
                  <th>O3_8h</th>
                  <th>绝对风险</th>
                  <th>风险类型</th>
                  <th>建议</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in dailyCases" :key="item.date">
                  <td>{{ item.date }}</td>
                  <td>{{ item.aqi }}</td>
                  <td>{{ item.pm25 }}</td>
                  <td>{{ item.o3_8h }}</td>
                  <td>{{ item.absolute_risk_score }} · {{ item.absolute_risk_level }}</td>
                  <td>{{ item.main_risk_type }}</td>
                  <td>{{ item.advice }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Industry</p>
              <h2>园区产业画像与规则模板</h2>
            </div>
            <p>产业分类和政策方向来自官方资料；能碳特征、KPI 与建议属于专家规则模板。</p>
          </div>
          <div class="industry-grid">
            <article v-for="item in industryProfiles" :key="item.industry" class="industry-item">
              <h3>{{ item.industry }}</h3>
              <p><b>官方定位：</b>{{ item.official_basis || item.official_direction || '-' }}</p>
              <p><b>规则模板：</b>{{ item.energy_carbon_feature || item.carbon_feature || item.energy_feature || '-' }}</p>
              <p><b>建议方向：</b>{{ item.governance_advice || item.governance || '-' }}</p>
              <small>需结合企业能源与现场审计数据后再形成具体方案。</small>
            </article>
          </div>
        </section>

        <section class="two-column">
          <article class="carbon-section compact-section">
            <div class="section-heading">
              <div>
                <p class="eyebrow">Governance</p>
                <h2>治理建议解释</h2>
              </div>
              <p>规则匹配，不做企业责任认定。</p>
            </div>
            <div class="governance-context">
              <strong>{{ governance?.latest_context?.date || '-' }}</strong>
              <p>{{ governance?.latest_context?.advice }}</p>
              <small>数据缺口：{{ governance?.latest_context?.data_gap }}</small>
            </div>
            <ul class="governance-list">
              <li v-for="rule in governance?.rules || []" :key="rule.trigger_basis">
                <b>{{ rule.trigger_basis }}</b>
                <span>{{ rule.action }}</span>
                <small>适用：{{ rule.applicable_industries }}；缺口：{{ rule.data_gap }}</small>
              </li>
            </ul>
          </article>

          <article class="carbon-section compact-section">
            <div class="section-heading">
              <div>
                <p class="eyebrow">Quality & Sources</p>
                <h2>方法、质量与来源</h2>
              </div>
              <p>所有指标均注明时间尺度、边界与不确定性。</p>
            </div>
            <ul class="method-list">
              <li>{{ methodology?.pri_formula }}</li>
              <li>{{ methodology?.experimental_cdci }}</li>
              <li>{{ methodology?.anomaly_rule }}</li>
              <li>{{ methodology?.weather_rule }}</li>
            </ul>
            <div class="source-list">
              <template v-for="source in sources.slice(0, 5)" :key="source.source_id">
                <a v-if="sourceHref(source)" :href="sourceHref(source)" target="_blank" rel="noreferrer">
                  {{ source.source_id }} · {{ source.dataset }} · {{ source.publisher }}
                </a>
                <span v-else>{{ source.source_id }} · {{ source.dataset }} · {{ source.publisher }}（项目本地原始数据，待补原始平台信息）</span>
              </template>
              <details v-if="sources.length > 5" class="source-details">
                <summary>展开全部 {{ sources.length }} 项数据来源</summary>
                <div class="source-list source-list-expanded">
                  <template v-for="source in sources.slice(5)" :key="source.source_id">
                    <a v-if="sourceHref(source)" :href="sourceHref(source)" target="_blank" rel="noreferrer">
                      {{ source.source_id }} · {{ source.dataset }} · {{ source.publisher }}
                    </a>
                    <span v-else>{{ source.source_id }} · {{ source.dataset }} · {{ source.publisher }}（项目本地原始数据，待补原始平台信息）</span>
                  </template>
                </div>
              </details>
            </div>
          </article>
        </section>

        <section class="carbon-section boundary-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Boundary</p>
              <h2>数据边界与不确定性</h2>
            </div>
            <p>数据构建时间：{{ overview?.dataVersion?.build_time || '-' }}</p>
          </div>
          <ul class="boundary-list">
            <li v-for="item in overview?.limitations || []" :key="item">{{ item }}</li>
            <li v-for="item in parkElectricity?.limitations || []" :key="item">{{ item }}</li>
          </ul>
        </section>

        <footer class="carbon-footer">本系统是减污降碳协同预警与治理决策原型，不是正式碳核算系统。</footer>
      </template>
    </section>
  </main>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  getCarbonEyeCarbonEmissions,
  getCarbonEyeCdci,
  getCarbonEyeCdciSensitivity,
  getCarbonEyeDailyCases,
  getCarbonEyeDataQuality,
  getCarbonEyeEconomicCarbonIntensity,
  getCarbonEyeGovernanceExplanation,
  getCarbonEyeIndustryProfile,
  getCarbonEyeMethodology,
  getCarbonEyeMonthlyTrends,
  getCarbonEyeOverview,
  getCarbonEyeParkElectricityEmissions,
  getCarbonEyeParkEnvironmentSnapshot,
  getCarbonEyeRealtimeAqi,
  getCarbonEyeSources,
  getCarbonEyeWarnings,
  getCarbonEyeWeatherCorrelations,
  getCarbonEyeWeatherLongTerm,
} from '../api/carbonEye'

const overview = ref(null)
const monthlyTrends = ref([])
const cityCarbon = ref([])
const warnings = ref([])
const dailyCases = ref([])
const methodology = ref(null)
const realtimeAqi = ref(null)
const parkElectricity = ref(null)
const economicIntensity = ref(null)
const parkSnapshot = ref(null)
const weatherLongTerm = ref(null)
const weatherCorrelationPayload = ref(null)
const cdci = ref(null)
const cdciSensitivity = ref(null)
const industryProfile = ref(null)
const governance = ref(null)
const dataQuality = ref(null)
const sources = ref([])
const selectedSiteId = ref('')
const loading = ref(true)
const error = ref('')

const trendChartRef = ref(null)
const weatherChartRef = ref(null)
const correlationChartRef = ref(null)
const cityCarbonChartRef = ref(null)
const parkCarbonChartRef = ref(null)
const intensityChartRef = ref(null)
const cdciChartRef = ref(null)
let charts = []

const latestMonthly = computed(() => overview.value?.latestMonthly || null)
const latestParkProxy = computed(() => overview.value?.latestParkElectricityProxy || parkElectricity.value?.records?.at(-1) || null)
const latestAnnualDimension = computed(() => cdci.value?.annual_dimensions?.at(-1) || null)
const weatherRecords = computed(() => weatherLongTerm.value?.records || [])
const weatherCorrelations = computed(() => weatherCorrelationPayload.value?.correlations || [])
const parkElectricityRecords = computed(() => parkElectricity.value?.year_slots || parkElectricity.value?.records || [])
const economicIntensityRecords = computed(() => economicIntensity.value?.records || [])
const cdciRecords = computed(() => cdci.value?.records || [])
const industryProfiles = computed(() => industryProfile.value?.profiles || industryProfile.value?.industries || [])
const selectedSnapshotSite = computed(() => (parkSnapshot.value?.sites || []).find((site) => site.site_id === selectedSiteId.value))
const selectedSnapshotRecords = computed(() => (parkSnapshot.value?.records || []).filter((item) => item.site_id === selectedSiteId.value))
const realtimeStatus = computed(() => {
  if (!realtimeAqi.value) return '未返回实时接口状态'
  if (realtimeAqi.value.status === 'ok') return realtimeAqi.value.cached ? '内存缓存，10分钟内有效' : '正式 API 获取成功'
  if (realtimeAqi.value.status === 'stale') return '接口刷新失败，展示最近缓存'
  return realtimeAqi.value.message || '实时数据暂不可用'
})

function sourceHref(source) {
  const href = source?.url_or_path || ''
  return /^https?:\/\//.test(href) ? href : ''
}

onMounted(async () => {
  await loadData()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [
      overviewData,
      trendData,
      cityCarbonData,
      warningData,
      dailyData,
      methodologyData,
      realtimeData,
      electricityData,
      intensityData,
      snapshotData,
      weatherData,
      correlationsData,
      cdciData,
      sensitivityData,
      industryData,
      governanceData,
      qualityData,
      sourceData,
    ] = await Promise.all([
      getCarbonEyeOverview(),
      getCarbonEyeMonthlyTrends(),
      getCarbonEyeCarbonEmissions(),
      getCarbonEyeWarnings(),
      getCarbonEyeDailyCases(),
      getCarbonEyeMethodology(),
      getCarbonEyeRealtimeAqi(),
      getCarbonEyeParkElectricityEmissions(),
      getCarbonEyeEconomicCarbonIntensity(),
      getCarbonEyeParkEnvironmentSnapshot(),
      getCarbonEyeWeatherLongTerm(),
      getCarbonEyeWeatherCorrelations(),
      getCarbonEyeCdci(),
      getCarbonEyeCdciSensitivity(),
      getCarbonEyeIndustryProfile(),
      getCarbonEyeGovernanceExplanation(),
      getCarbonEyeDataQuality(),
      getCarbonEyeSources(),
    ])
    overview.value = overviewData
    monthlyTrends.value = trendData
    cityCarbon.value = cityCarbonData
    warnings.value = warningData
    dailyCases.value = dailyData
    methodology.value = methodologyData
    realtimeAqi.value = realtimeData
    parkElectricity.value = electricityData
    economicIntensity.value = intensityData
    parkSnapshot.value = snapshotData
    weatherLongTerm.value = weatherData
    weatherCorrelationPayload.value = correlationsData
    cdci.value = cdciData
    cdciSensitivity.value = sensitivityData
    industryProfile.value = industryData
    governance.value = governanceData
    dataQuality.value = qualityData
    sources.value = sourceData
    selectedSiteId.value = snapshotData.sites?.[0]?.site_id || ''
    loading.value = false
    await nextTick()
    requestAnimationFrame(renderCharts)
  } catch (requestError) {
    error.value = requestError.message || '专题数据加载失败，请检查后端静态数据状态。'
    loading.value = false
  }
}

function disposeCharts() {
  charts.forEach((chart) => chart?.dispose())
  charts = []
}

function resizeCharts() {
  charts.forEach((chart) => chart?.resize())
}

function registerChart(element) {
  if (!element) return null
  const chart = echarts.init(element)
  charts.push(chart)
  return chart
}

function axisOptions() {
  return {
    backgroundColor: 'transparent',
    animation: false,
    textStyle: { color: '#dbeafe', fontFamily: 'Microsoft YaHei, Segoe UI, sans-serif' },
    tooltip: { trigger: 'axis', backgroundColor: '#101b2d', borderColor: '#38516e', textStyle: { color: '#f8fafc' } },
    legend: { top: 28, textStyle: { color: '#cbd5e1' }, type: 'scroll' },
    grid: { top: 76, left: 56, right: 28, bottom: 52, containLabel: false },
    xAxis: { type: 'category', axisLabel: { color: '#9fb3c8' }, axisLine: { lineStyle: { color: '#3c5067' } } },
    yAxis: { type: 'value', axisLabel: { color: '#9fb3c8' }, splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.15)' } } },
  }
}

function renderCharts() {
  disposeCharts()
  renderTrendChart()
  renderWeatherChart()
  renderCorrelationChart()
  renderCityCarbonChart()
  renderParkCarbonChart()
  renderIntensityChart()
  renderCdciChart()
  resizeCharts()
}

function renderTrendChart() {
  const chart = registerChart(trendChartRef.value)
  if (!chart) return
  const dates = monthlyTrends.value.map((item) => item.date)
  chart.setOption({
    ...axisOptions(),
    title: { text: 'AQI、PM2.5、O3 与 PRI（月度）', left: 0, textStyle: { color: '#fff', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: dates },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, textStyle: { color: '#9fb3c8' } }],
    series: [
      { name: 'AQI', type: 'line', symbol: 'none', smooth: true, data: monthlyTrends.value.map((item) => item.aqi), color: '#60a5fa' },
      { name: 'PM2.5', type: 'line', symbol: 'none', smooth: true, data: monthlyTrends.value.map((item) => item.pm25), color: '#5eead4' },
      { name: 'O3', type: 'line', symbol: 'none', smooth: true, data: monthlyTrends.value.map((item) => item.o3), color: '#fbbf24' },
      { name: 'PRI', type: 'line', symbol: 'none', smooth: true, data: monthlyTrends.value.map((item) => item.absolute_risk_score), color: '#fb7185' },
    ],
  })
}

function renderWeatherChart() {
  const chart = registerChart(weatherChartRef.value)
  if (!chart) return
  const records = weatherRecords.value
  chart.setOption({
    ...axisOptions(),
    title: { text: '温度、降水与风速（月度）', left: 0, textStyle: { color: '#fff', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: records.map((item) => item.month) },
    yAxis: [
      { ...axisOptions().yAxis, name: '°C / km/h', nameTextStyle: { color: '#9fb3c8' } },
      { ...axisOptions().yAxis, name: 'mm', nameTextStyle: { color: '#9fb3c8' } },
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, textStyle: { color: '#9fb3c8' } }],
    series: [
      { name: '平均气温', type: 'line', symbol: 'none', smooth: true, data: records.map((item) => item.avg_temp_c), color: '#fbbf24' },
      { name: '平均风速', type: 'line', symbol: 'none', smooth: true, data: records.map((item) => item.avg_wind_speed_kmh), color: '#60a5fa' },
      { name: '降水量', type: 'bar', yAxisIndex: 1, data: records.map((item) => item.precipitation_mm), color: '#22d3ee' },
    ],
  })
}

function renderCorrelationChart() {
  const chart = registerChart(correlationChartRef.value)
  if (!chart) return
  const variables = ['avg_temp_c', 'sunshine_hours', 'shortwave_radiation_mj_m2', 'avg_wind_speed_kmh', 'precipitation_mm', 'relative_humidity_pct', 'pressure_msl_hpa']
  const pollutants = ['o3', 'pm25', 'no2']
  const labels = { o3: 'O3', pm25: 'PM2.5', no2: 'NO2', avg_temp_c: '温度', sunshine_hours: '日照', shortwave_radiation_mj_m2: '短波辐射', avg_wind_speed_kmh: '风速', precipitation_mm: '降水', relative_humidity_pct: '湿度', pressure_msl_hpa: '气压' }
  const lookup = new Map(weatherCorrelations.value.map((item) => [`${item.pollutant}:${item.weather_variable}`, item]))
  const data = []
  pollutants.forEach((pollutant, x) => variables.forEach((variable, y) => {
    const result = lookup.get(`${pollutant}:${variable}`)
    data.push([x, y, result?.season_adjusted_pearson_r ?? '-', result?.n ?? 0, result?.pearson_r, result?.spearman_rho])
  }))
  chart.setOption({
    backgroundColor: 'transparent',
    title: { text: '去季节 Pearson r', left: 0, textStyle: { color: '#fff', fontSize: 15, fontWeight: 600 } },
    tooltip: { formatter: (params) => `${labels[pollutants[params.value[0]]]} · ${labels[variables[params.value[1]]]}<br/>去季节 r：${params.value[2]}<br/>Pearson：${params.value[4]}<br/>Spearman：${params.value[5]}<br/>n：${params.value[3]}<br/>描述性相关，不代表因果。` },
    grid: { top: 48, left: 90, right: 16, bottom: 44 },
    xAxis: { type: 'category', data: pollutants.map((item) => labels[item]), axisLabel: { color: '#cbd5e1' }, axisLine: { lineStyle: { color: '#3c5067' } } },
    yAxis: { type: 'category', data: variables.map((item) => labels[item]), axisLabel: { color: '#cbd5e1' }, axisLine: { lineStyle: { color: '#3c5067' } } },
    visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, textStyle: { color: '#cbd5e1' }, inRange: { color: ['#2563eb', '#dbeafe', '#fca5a5', '#dc2626'] } },
    series: [{ type: 'heatmap', data, label: { show: true, color: '#0f172a', formatter: (params) => params.value[2] }, emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,.45)' } } }],
  })
}

function renderCityCarbonChart() {
  const chart = registerChart(cityCarbonChartRef.value)
  if (!chart) return
  chart.setOption({
    ...axisOptions(),
    title: { text: '苏州市 CO2 年度背景', left: 0, textStyle: { color: '#fff', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: cityCarbon.value.map((item) => item.year) },
    yAxis: { ...axisOptions().yAxis, name: cityCarbon.value[0]?.unit || 'CO2', nameTextStyle: { color: '#9fb3c8' } },
    series: [{ name: '苏州市 CO2 背景', type: 'bar', data: cityCarbon.value.map((item) => item.co2_emission), color: '#60a5fa' }],
  })
}

function renderParkCarbonChart() {
  const chart = registerChart(parkCarbonChartRef.value)
  if (!chart) return
  const years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  const byYear = new Map(parkElectricityRecords.value.map((item) => [item.year, item]))
  chart.setOption({
    ...axisOptions(),
    title: { text: '用电量与购电间接排放代理', left: 0, textStyle: { color: '#fff', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: years },
    yAxis: [
      { ...axisOptions().yAxis, name: '亿 kWh', nameTextStyle: { color: '#9fb3c8' } },
      { ...axisOptions().yAxis, name: '万吨 CO2', nameTextStyle: { color: '#9fb3c8' } },
    ],
    series: [
      { name: '全社会用电量', type: 'bar', data: years.map((year) => byYear.get(year)?.total_electricity_100m_kwh ?? null), color: '#60a5fa' },
      { name: '工业用电量', type: 'bar', data: years.map((year) => byYear.get(year)?.industrial_electricity_100m_kwh ?? null), color: '#5eead4' },
      { name: '全社会购电间接排放代理', type: 'line', yAxisIndex: 1, connectNulls: false, symbolSize: 7, data: years.map((year) => byYear.get(year)?.total_purchased_electricity_scope2_10k_tco2 ?? null), color: '#fbbf24' },
      { name: '工业购电间接排放代理', type: 'line', yAxisIndex: 1, connectNulls: false, symbolSize: 7, data: years.map((year) => byYear.get(year)?.industrial_electricity_scope2_10k_tco2 ?? null), color: '#fb7185' },
    ],
  })
}

function renderIntensityChart() {
  const chart = registerChart(intensityChartRef.value)
  if (!chart) return
  const years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  const byYear = new Map(economicIntensityRecords.value.map((item) => [item.year, item]))
  chart.setOption({
    ...axisOptions(),
    title: { text: '宏观用电与购电代理强度', left: 0, textStyle: { color: '#fff', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: years },
    yAxis: [
      { ...axisOptions().yAxis, name: 'kWh / 万元', nameTextStyle: { color: '#9fb3c8' } },
      { ...axisOptions().yAxis, name: 'tCO2 / 万元', nameTextStyle: { color: '#9fb3c8' } },
    ],
    series: [
      { name: '每万元 GDP 用电量', type: 'line', connectNulls: false, data: years.map((year) => byYear.get(year)?.total_electricity_kwh_per_10k_gdp ?? null), color: '#60a5fa' },
      { name: '每万元规上工业产值用电量', type: 'line', connectNulls: false, data: years.map((year) => byYear.get(year)?.industrial_electricity_kwh_per_10k_output ?? null), color: '#5eead4' },
      { name: '每万元 GDP 购电代理强度', type: 'line', yAxisIndex: 1, connectNulls: false, data: years.map((year) => byYear.get(year)?.total_scope2_tco2_per_10k_gdp ?? null), color: '#fbbf24' },
      { name: '每万元规上工业产值购电代理强度', type: 'line', yAxisIndex: 1, connectNulls: false, data: years.map((year) => byYear.get(year)?.industrial_scope2_tco2_per_10k_output ?? null), color: '#fb7185' },
    ],
  })
}

function renderCdciChart() {
  const chart = registerChart(cdciChartRef.value)
  if (!chart) return
  const records = cdciRecords.value
  chart.setOption({
    ...axisOptions(),
    title: { text: 'PRI / EAI / CEI 与实验性 CDCI', left: 0, textStyle: { color: '#fff', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: records.map((item) => item.date) },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, textStyle: { color: '#9fb3c8' } }],
    series: [
      { name: 'PRI（月度）', type: 'line', symbol: 'none', data: records.map((item) => item.pri), color: '#fb7185' },
      { name: 'EAI（年度背景）', type: 'line', symbol: 'none', data: records.map((item) => item.eai), color: '#a78bfa' },
      { name: 'CEI（年度背景）', type: 'line', symbol: 'none', data: records.map((item) => item.cei), color: '#fbbf24' },
      { name: '实验性 CDCI', type: 'line', symbol: 'none', data: records.map((item) => item.cdci), color: '#2dd4bf', lineStyle: { width: 3 } },
    ],
  })
}

function percent(value) {
  return value === null || value === undefined ? '-' : `${(Number(value) * 100).toFixed(1)}%`
}

function displaySnapshotRange(value) {
  return String(value || '-').replaceAll('ND', '未检出')
}
</script>

<style scoped>
.carbon-eye-page { display: grid; gap: 18px; min-width: 0; color: #e6edf7; }
.carbon-topbar { display: flex; justify-content: space-between; gap: 12px; align-items: center; color: #9fb3c8; font-size: 13px; }
.back-link { color: #7dd3fc; text-decoration: none; }
.carbon-header { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(280px, .7fr); gap: 24px; align-items: end; padding: 8px 0 14px; border-bottom: 1px solid #26384d; }
.eyebrow { margin: 0 0 8px; color: #4ade80; font-size: 12px; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }
h1, h2, h3, p { margin-top: 0; }
h1 { margin-bottom: 8px; font-size: 30px; line-height: 1.2; letter-spacing: 0; }
h2 { margin-bottom: 6px; font-size: 20px; line-height: 1.3; letter-spacing: 0; }
h3 { font-size: 16px; line-height: 1.35; letter-spacing: 0; }
.carbon-header p, .section-heading > p, .figure-note, .section-note, .experimental-note { color: #a7bdd0; line-height: 1.65; }
.boundary-banner { border-left: 3px solid #fbbf24; padding: 10px 12px; background: #172637; color: #dceaf6; line-height: 1.6; font-size: 13px; }
.carbon-state, .carbon-error, .chart-empty { padding: 22px; border: 1px solid #32445b; background: #101b2d; color: #cbd5e1; }
.carbon-error { border-color: #be4b57; color: #fecdd3; }
.metric-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.metric-card { min-height: 132px; display: flex; flex-direction: column; gap: 8px; padding: 16px; border: 1px solid #2c4058; background: #101b2d; }
.metric-card span { color: #94a9be; font-size: 13px; }
.metric-card strong { color: #f8fafc; font-size: 25px; line-height: 1.15; overflow-wrap: anywhere; }
.metric-card p { margin: 0; color: #aac0d4; font-size: 12px; line-height: 1.55; }
.carbon-section { min-width: 0; padding: 20px; border: 1px solid #2a3f57; background: #0e1928; }
.section-heading { display: flex; justify-content: space-between; gap: 18px; align-items: start; margin-bottom: 12px; }
.section-heading > div { min-width: 0; }
.carbon-eye-page .section-heading h2 { margin: 0 0 6px; font-size: 20px; line-height: 1.3; letter-spacing: 0; overflow-wrap: anywhere; word-break: break-word; }
.section-heading > p { max-width: 48ch; margin-bottom: 0; font-size: 13px; }
.section-note, .experimental-note { margin: 0 0 14px; padding: 10px 12px; border-left: 3px solid #38bdf8; background: #122238; font-size: 13px; }
.warning-note { border-left-color: #fbbf24; }
.chart { width: 100%; min-height: 320px; }
.chart-tall { min-height: 380px; }
.chart-medium { min-height: 330px; }
.two-column { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.compact-section { min-height: 0; }
.site-layout { display: grid; grid-template-columns: minmax(230px, .6fr) minmax(0, 1.4fr); gap: 18px; }
.site-list { display: grid; gap: 8px; align-content: start; }
.site-button { display: grid; grid-template-columns: 32px minmax(0, 1fr); text-align: left; gap: 3px 8px; padding: 10px; color: #dceaf6; border: 1px solid #2d435d; background: #132238; cursor: pointer; }
.site-button:hover, .site-button.active { border-color: #38bdf8; background: #18314c; }
.site-button strong { grid-row: span 2; color: #5eead4; }
.site-button span, .site-button small { min-width: 0; overflow-wrap: anywhere; }
.site-button small { color: #9eb4c9; font-size: 11px; }
.snapshot-detail { min-width: 0; }
.snapshot-selected { display: flex; justify-content: space-between; gap: 14px; align-items: end; margin-bottom: 12px; }
.snapshot-selected span, .snapshot-selected p { color: #9eb4c9; font-size: 12px; }
.snapshot-selected strong { display: block; margin-top: 4px; }
.table-wrap { max-width: 100%; overflow-x: auto; border: 1px solid #2a3f57; }
.data-table { width: 100%; min-width: 700px; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { padding: 10px 11px; text-align: left; vertical-align: top; border-bottom: 1px solid #263a51; line-height: 1.5; }
.data-table th { position: sticky; top: 0; background: #14243a; color: #d9e8f5; white-space: nowrap; }
.data-table td { color: #b8cadd; }
.sensitivity-wrap { margin-top: 14px; }
.industry-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.industry-item { padding: 14px; border: 1px solid #2a3f57; background: #132238; min-width: 0; }
.industry-item h3 { color: #dff7ea; margin-bottom: 10px; }
.industry-item p { color: #adc1d3; font-size: 13px; line-height: 1.6; }
.industry-item b { color: #e6edf7; }
.industry-item small { color: #7f99b1; line-height: 1.5; }
.governance-context { padding: 12px; margin-bottom: 12px; border-left: 3px solid #4ade80; background: #132238; }
.governance-context p, .governance-context small { color: #b5c9d9; line-height: 1.6; }
.governance-list, .method-list, .boundary-list { display: grid; gap: 10px; padding-left: 18px; margin: 0; }
.governance-list li { display: grid; gap: 4px; color: #c4d5e4; line-height: 1.55; }
.governance-list small { color: #879eb3; }
.method-list li, .boundary-list li { color: #b8cadd; line-height: 1.6; }
.source-list { display: grid; gap: 8px; margin-top: 16px; }
.source-list a, .source-list span { color: #7dd3fc; font-size: 12px; line-height: 1.5; overflow-wrap: anywhere; }
.source-list span { color: #a7b8c9; }
.source-details { margin-top: 4px; }
.source-details summary { color: #d9e7f5; cursor: pointer; font-size: 13px; }
.source-list-expanded { margin-top: 10px; }
.boundary-section { border-color: #4c5966; }
.carbon-footer { padding: 15px 0 4px; color: #9fb3c8; font-size: 13px; text-align: center; }

@media (max-width: 1100px) {
  .metric-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .industry-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
  .carbon-topbar, .carbon-header, .section-heading, .snapshot-selected { align-items: start; flex-direction: column; }
  .carbon-header, .two-column, .site-layout { grid-template-columns: 1fr; }
  .metric-grid, .industry-grid { grid-template-columns: 1fr; }
  .metric-card { min-height: 106px; }
  .carbon-section { padding: 15px; }
  .chart, .chart-medium, .chart-tall { min-height: 300px; }
  .section-heading > p { max-width: none; }
  h1 { font-size: 27px; }
  .carbon-eye-page .section-heading h2 { font-size: 19px; line-height: 1.35; }
}
</style>
