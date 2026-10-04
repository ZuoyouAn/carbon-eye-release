<template>
  <main class="content-page">
    <section class="carbon-eye-page">
      <header class="carbon-topbar">
        <RouterLink class="back-link" to="/projects">返回项目</RouterLink>
        <span>数据版本 {{ overview?.dataVersion?.system_version || '-' }}</span>
      </header>

      <section class="carbon-header">
        <div>
          <p class="eyebrow">Carbon Eye / 焦作应用示范版</p>
          <h1>焦作园区碳眼</h1>
          <p>面向焦作工业园区减污降碳协同治理场景的应用示范。当前版本沿用苏州公开数据验证系统功能，待接入焦作本地监测、用电与产业数据后形成焦作实证结果。</p>
        </div>
        <div class="boundary-banner">
          当前为焦作应用示范界面，页面数值仍来自苏州样例数据；购电间接排放位置法代理估算不代表焦作或园区总碳排放。
        </div>
      </section>

      <div v-if="loading" class="carbon-state">正在加载专题数据...</div>
      <div v-else-if="error" class="carbon-error">{{ error }}</div>

      <template v-else>
        <section class="metric-grid" aria-label="专题驾驶舱">
          <article class="metric-card">
            <span>实时 AQI 状态（苏州样例站）</span>
            <strong>{{ realtimeAqiValue }}</strong>
            <p>{{ realtimeStatus }}</p>
          </article>
          <article class="metric-card">
            <span>最新完整月 PRI（苏州样例）</span>
            <strong>{{ latestMonthly?.absolute_risk_score ?? '-' }}</strong>
            <p>{{ latestMonthly?.date }} · {{ latestMonthly?.absolute_risk_level }} · {{ latestMonthly?.main_contributor }}</p>
          </article>
          <article class="metric-card">
            <span>最新购电间接排放代理（苏州样例）</span>
            <strong>{{ latestParkProxy?.total_purchased_electricity_scope2_10k_tco2 ?? '-' }}</strong>
            <p>万吨 CO2 · {{ latestParkProxy?.year || '-' }} 年</p>
          </article>
          <article class="metric-card">
            <span>PRI / EAI / CEI 三维态势（样例）</span>
            <strong>{{ threeDimensionSummary }}</strong>
            <p>PRI 为月度；EAI、CEI 为 {{ latestAnnualDimension?.year || '-' }} 年年度背景</p>
          </article>
        </section>
        <details class="dashboard-boundary">
          <summary>查看驾驶舱的数据时间尺度与边界</summary>
          <p>当前实时 AQI、PRI、购电间接排放代理、EAI 与 CEI 均沿用苏州公开数据，用于验证焦作版系统交互和分析流程，不代表焦作当前环境或能碳状态；各指标时间尺度也不相同。</p>
        </details>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">City Background</p>
              <h2>焦作应用示范：城市长期空气质量</h2>
            </div>
            <p>苏州样例数据；单位：AQI 或 µg/m3；时间：2013-12 至 2026-07。仅用于演示焦作版的长期趋势和污染压力分析流程。</p>
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
                <h2>长期气象解释样例</h2>
              </div>
              <p>苏州六点位 ERA5 样例；单位：°C、mm、km/h；2013-12 至 2026-06。</p>
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
              <h2>焦作六区域部署占位与特征因子样例</h2>
            </div>
            <p>界面按焦作六区域设置部署占位；数值仍为苏州2026年6月短期快照：{{ parkSnapshot?.site_count || 0 }} 点位 · {{ parkSnapshot?.monitoring_days || 0 }} 天 · {{ parkSnapshot?.pollutant_count || 0 }} 项因子。</p>
          </div>
          <div class="section-note warning-note">焦作区域名称仅为未来部署占位，不是焦作实测点位；表中数值来自苏州官方短期补充监测快照，不代表焦作或苏州全年均值、实时序列，也不用于识别具体企业。</div>
          <div class="site-layout">
            <div class="site-overview">
              <div class="site-map" aria-label="焦作六区域部署示意图">
                <span class="map-title">焦作部署示意（非实测坐标）</span>
                <span class="map-scale map-scale-north">北</span>
                <span class="map-scale map-scale-south">南</span>
                <button
                  v-for="site in parkSnapshot?.sites || []"
                  :key="`map-${site.site_id}`"
                  class="site-marker"
                  :class="{ active: selectedSiteId === site.site_id }"
                  :style="siteMarkerStyle(site)"
                  type="button"
                  :aria-label="`查看${siteDisplayName(site)}`"
                  @click="selectedSiteId = site.site_id"
                >{{ site.site_id }}</button>
              </div>
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
                  <span>{{ siteDisplayName(site) }}</span>
                  <small>部署占位 · 数据源为苏州样例</small>
                </button>
              </div>
            </div>
            <div class="snapshot-detail">
              <div class="snapshot-selected">
                <div>
                  <span>当前点位</span>
                  <strong>{{ siteDisplayName(selectedSnapshotSite) }}</strong>
                </div>
                <p>焦作部署占位；样例原点位：{{ selectedSnapshotSite?.site_name || '-' }}</p>
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
                <h2>苏州市年度 CO2 样例背景</h2>
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
                <h2>苏州工业园区购电间接排放样例（位置法代理值）</h2>
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
              <h2>园区用电与购电间接排放强度代理（苏州样例）</h2>
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
          <p class="section-note warning-note">点击任一异常月份，查看相对异常、历史同月阈值、绝对风险、主要贡献和适用治理建议。</p>
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
                <tr
                  v-for="item in warnings"
                  :key="item.date"
                  class="warning-row"
                  :class="{ active: selectedWarningDate === item.date }"
                  role="button"
                  tabindex="0"
                  @click="selectedWarningDate = item.date"
                  @keydown.enter="selectedWarningDate = item.date"
                >
                  <td>{{ item.date }}</td>
                  <td>{{ item.relative_anomaly ? '超过' : '未超过' }}</td>
                  <td>{{ item.anomaly_items?.join('；') }}</td>
                  <td>{{ item.absolute_risk_score }} · {{ item.absolute_risk_level }}</td>
                  <td>{{ item.main_contributor }} · {{ item.main_risk_type }}</td>
                  <td>{{ item.governance_advice }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <article v-if="selectedWarning" class="warning-workbench">
            <div>
              <p class="eyebrow">Selected Month / {{ selectedWarning.date }}</p>
              <h3>预警工作台</h3>
            </div>
            <dl class="warning-detail-grid">
              <div>
                <dt>相对异常</dt>
                <dd>{{ selectedWarning.relative_anomaly ? '超过历史同月 90% 分位阈值' : '未超过历史同月阈值' }}</dd>
              </div>
              <div>
                <dt>触发污染物与历史阈值</dt>
                <dd>{{ selectedWarning.anomaly_items?.join('；') || '-' }}</dd>
              </div>
              <div>
                <dt>绝对风险等级</dt>
                <dd>{{ selectedWarning.absolute_risk_score }} · {{ selectedWarning.absolute_risk_level }}</dd>
              </div>
              <div>
                <dt>主要贡献</dt>
                <dd>{{ selectedWarning.main_contributor }} · {{ selectedWarning.main_risk_type }}</dd>
              </div>
              <div>
                <dt>适用治理建议</dt>
                <dd>{{ selectedWarning.governance_advice }}</dd>
              </div>
              <div>
                <dt>数据时间尺度</dt>
                <dd>{{ selectedWarning.time_scale }} · {{ selectedWarning.data_scope }}</dd>
              </div>
            </dl>
          </article>
        </section>

        <section class="carbon-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Daily Replay</p>
              <h2>日级历史案例回放</h2>
            </div>
            <p>历史回放：2013-12-02 至 2015-07-31。日表 20 个月中 18 个月完成字段纠偏，平均相对误差约 0.0182；不等于实时园区预警。</p>
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
              <h2>产业画像与规则模板（苏州样例）</h2>
            </div>
            <p>产业分类和政策方向来自官方资料；能碳特征、KPI 与建议属于专家规则模板。</p>
          </div>
          <div class="industry-grid">
            <article v-for="item in industryProfiles" :key="item.industry" class="industry-item">
              <h3>{{ item.industry }}</h3>
              <p><b>官方定位：</b>{{ item.official_basis || item.official_direction || '-' }}</p>
              <p><b>规则模板：</b>{{ item.energy_carbon_feature || item.carbon_feature || item.energy_feature || '-' }}</p>
              <p><b>建议方向：</b>{{ item.governance_advice || item.governance || '-' }}</p>
              <p><b>关联展示：</b>{{ industryLinkText(item) }}</p>
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
              <strong>{{ governanceContext.date || '-' }}</strong>
              <p>{{ governanceContext.advice }}</p>
              <small>数据缺口：{{ governanceContext.data_gap }}</small>
            </div>
            <ul class="governance-list">
              <li v-for="rule in governance?.rules || []" :key="rule.trigger_basis">
                <span><b>触发依据：</b>{{ rule.trigger_basis }}</span>
                <span><b>适用产业：</b>{{ rule.applicable_industries }}</span>
                <span><b>建议动作：</b>{{ rule.action }}</span>
                <small><b>数据缺口：</b>{{ rule.data_gap }}</small>
                <small>本规则不能替代现场审计、源解析或具体企业责任认定。</small>
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

        <footer class="carbon-footer">本系统为焦作园区减污降碳应用示范原型；当前数据来自苏州公开样例，不代表焦作实测结果，也不是正式碳核算系统。</footer>
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
const selectedWarningDate = ref('')
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
let realtimeTimer = null

const jiaozuoSiteAliases = {
  G1: '焦作部署占位·解放区',
  G2: '焦作部署占位·山阳区',
  G3: '焦作部署占位·中站区',
  G4: '焦作部署占位·马村区',
  G5: '焦作部署占位·城乡一体化示范区',
  G6: '焦作部署占位·修武县',
}

const jiaozuoMarkerPositions = {
  G1: { left: '20%', top: '34%' },
  G2: { left: '46%', top: '20%' },
  G3: { left: '74%', top: '34%' },
  G4: { left: '26%', top: '70%' },
  G5: { left: '52%', top: '58%' },
  G6: { left: '78%', top: '72%' },
}

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
const selectedWarning = computed(() => warnings.value.find((item) => item.date === selectedWarningDate.value) || warnings.value[0] || null)
const realtimeAqiValue = computed(() => {
  if (!['ok', 'stale'].includes(realtimeAqi.value?.status)) return '暂不可用'
  return realtimeAqi.value?.items?.find((item) => item.pollutant === 'aqi')?.current_value ?? '暂不可用'
})
const threeDimensionSummary = computed(() => {
  if (!latestMonthly.value || !latestAnnualDimension.value) return '-'
  return `${latestMonthly.value.absolute_risk_score} / ${latestAnnualDimension.value.eai} / ${latestAnnualDimension.value.cei}`
})
const governanceContext = computed(() => {
  if (selectedWarning.value) {
    return {
      date: selectedWarning.value.date,
      advice: selectedWarning.value.governance_advice,
      data_gap: '缺少企业级用电、燃料、排放清单、工况与现场审计数据。',
    }
  }
  return governance.value?.latest_context || {}
})
const realtimeStatus = computed(() => {
  if (!realtimeAqi.value) return '未返回实时接口状态'
  if (realtimeAqi.value.status === 'ok') return realtimeAqi.value.cached ? '一小时内存缓存' : '公开页面抓取成功'
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
  realtimeTimer = window.setInterval(refreshRealtimeAqi, 60 * 60 * 1000)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  window.clearInterval(realtimeTimer)
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
    selectedWarningDate.value = warningData[0]?.date || ''
    loading.value = false
    await nextTick()
    requestAnimationFrame(renderCharts)
  } catch (requestError) {
    error.value = requestError.message || '专题数据加载失败，请检查后端静态数据状态。'
    loading.value = false
  }
}

async function refreshRealtimeAqi() {
  try {
    realtimeAqi.value = await getCarbonEyeRealtimeAqi()
  } catch {
    // Keep the last known response visible if a transient request fails.
  }
}

function siteMarkerStyle(site) {
  return jiaozuoMarkerPositions[site.site_id] || { left: '50%', top: '50%' }
}

function siteDisplayName(site) {
  if (!site) return '-'
  return jiaozuoSiteAliases[site.site_id] || `焦作部署占位·${site.site_id}`
}

function industryLinkText(item) {
  const characteristics = item.energy_carbon_characteristics || []
  const electricityYear = latestParkProxy.value?.year
  const scope2 = latestParkProxy.value?.total_purchased_electricity_scope2_10k_tco2
  const electricityContext = electricityYear && scope2 ? `园区 ${electricityYear} 年全社会购电代理为 ${scope2} 万吨 CO2。` : '园区年度购电代理数据存在时间缺口。'
  return `${characteristics[0] || '行业能碳特征待补'}；${electricityContext} 此为产业规则与园区宏观指标的关联展示，不对应具体企业。`
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
    textStyle: { color: '#41434a', fontFamily: 'Microsoft YaHei, Segoe UI, sans-serif', fontSize: 14 },
    tooltip: { trigger: 'axis', backgroundColor: '#ffffff', borderColor: '#e2e4e8', textStyle: { color: '#41434a', fontSize: 14 } },
    legend: { top: 30, textStyle: { color: '#62646b', fontSize: 14 }, type: 'scroll' },
    grid: { top: 84, left: 20, right: 20, bottom: 54, containLabel: true },
    xAxis: { type: 'category', axisLabel: { color: '#62646b', fontSize: 14, hideOverlap: true }, axisLine: { lineStyle: { color: '#d0d4dc' } } },
    yAxis: { type: 'value', axisLabel: { color: '#62646b', fontSize: 14 }, splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.15)' } } },
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
    title: { text: 'AQI、PM2.5、O3 与 PRI（月度）', left: 0, textStyle: { color: '#1d1d1f', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: dates },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, textStyle: { color: '#62646b' } }],
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
    title: { text: '温度、降水与风速（月度）', left: 0, textStyle: { color: '#1d1d1f', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: records.map((item) => item.month) },
    yAxis: [
      { ...axisOptions().yAxis, name: '°C / km/h', nameTextStyle: { color: '#62646b' } },
      { ...axisOptions().yAxis, name: 'mm', nameTextStyle: { color: '#62646b' } },
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, textStyle: { color: '#62646b' } }],
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
    title: { text: '去季节 Pearson r', left: 0, textStyle: { color: '#1d1d1f', fontSize: 15, fontWeight: 600 } },
    tooltip: { formatter: (params) => `${labels[pollutants[params.value[0]]]} · ${labels[variables[params.value[1]]]}<br/>去季节 r：${params.value[2]}<br/>Pearson：${params.value[4]}<br/>Spearman：${params.value[5]}<br/>n：${params.value[3]}<br/>描述性相关，不代表因果。` },
    grid: { top: 48, left: 90, right: 16, bottom: 44 },
    xAxis: { type: 'category', data: pollutants.map((item) => labels[item]), axisLabel: { color: '#62646b' }, axisLine: { lineStyle: { color: '#d0d4dc' } } },
    yAxis: { type: 'category', data: variables.map((item) => labels[item]), axisLabel: { color: '#62646b' }, axisLine: { lineStyle: { color: '#d0d4dc' } } },
    visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, textStyle: { color: '#62646b' }, inRange: { color: ['#2563eb', '#dbeafe', '#fca5a5', '#dc2626'] } },
    series: [{ type: 'heatmap', data, label: { show: true, color: '#0f172a', formatter: (params) => params.value[2] }, emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,.45)' } } }],
  })
}

function renderCityCarbonChart() {
  const chart = registerChart(cityCarbonChartRef.value)
  if (!chart) return
  chart.setOption({
    ...axisOptions(),
    title: { text: '苏州市 CO2 年度样例背景', left: 0, textStyle: { color: '#1d1d1f', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: cityCarbon.value.map((item) => item.year) },
    yAxis: { ...axisOptions().yAxis, name: cityCarbon.value[0]?.unit || 'CO2', nameTextStyle: { color: '#62646b' } },
    series: [{ name: '苏州市 CO2 样例背景', type: 'bar', data: cityCarbon.value.map((item) => item.co2_emission), color: '#60a5fa' }],
  })
}

function renderParkCarbonChart() {
  const chart = registerChart(parkCarbonChartRef.value)
  if (!chart) return
  const years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  const byYear = new Map(parkElectricityRecords.value.map((item) => [item.year, item]))
  chart.setOption({
    ...axisOptions(),
    title: { text: '用电量与购电间接排放代理', left: 0, textStyle: { color: '#1d1d1f', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: years },
    yAxis: [
      { ...axisOptions().yAxis, name: '亿 kWh', nameTextStyle: { color: '#62646b' } },
      { ...axisOptions().yAxis, name: '万吨 CO2', nameTextStyle: { color: '#62646b' } },
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
    title: { text: '宏观用电与购电代理强度', left: 0, textStyle: { color: '#1d1d1f', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: years },
    yAxis: [
      { ...axisOptions().yAxis, name: 'kWh / 万元', nameTextStyle: { color: '#62646b' } },
      { ...axisOptions().yAxis, name: 'tCO2 / 万元', nameTextStyle: { color: '#62646b' } },
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
    title: { text: 'PRI / EAI / CEI 与实验性 CDCI', left: 0, textStyle: { color: '#1d1d1f', fontSize: 15, fontWeight: 600 } },
    xAxis: { ...axisOptions().xAxis, data: records.map((item) => item.date) },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, textStyle: { color: '#62646b' } }],
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
.carbon-eye-page { display: grid; gap: 18px; min-width: 0; color: var(--ink); }
.carbon-topbar { display: flex; justify-content: space-between; gap: 12px; align-items: center; color: var(--muted); font-size: 16px; }
.back-link { color: var(--blue); text-decoration: none; }
.carbon-header { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(280px, .7fr); gap: 24px; align-items: end; padding: 8px 0 14px; border-bottom: 1px solid var(--border); }
.eyebrow { margin: 0 0 8px; color: var(--green); font-size: 14px; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }
h1, h2, h3, p { margin-top: 0; }
h1 { margin-bottom: 8px; font-size: 30px; line-height: 1.2; letter-spacing: 0; }
h2 { margin-bottom: 6px; font-size: 20px; line-height: 1.3; letter-spacing: 0; }
h3 { font-size: 16px; line-height: 1.35; letter-spacing: 0; }
.carbon-header p, .section-heading > p, .figure-note, .section-note, .experimental-note { color: var(--muted); line-height: 1.65; }
.boundary-banner { border-left: 3px solid var(--border); padding: 10px 12px; background: var(--surface); color: var(--ink); line-height: 1.6; font-size: 16px; }
.carbon-state, .carbon-error, .chart-empty { padding: 22px; border: 1px solid var(--border); background: var(--surface); color: var(--muted); }
.carbon-error { border-color: var(--border); color: var(--ink); }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.metric-card { min-height: 132px; display: flex; flex-direction: column; gap: 8px; padding: 16px; border: 1px solid var(--border); background: var(--surface); }
.metric-card span { color: var(--muted); font-size: 16px; }
.metric-card strong { color: var(--ink); font-size: 25px; line-height: 1.15; overflow-wrap: anywhere; }
.metric-card p { margin: 0; color: var(--muted); font-size: 14px; line-height: 1.55; }
.dashboard-boundary { border: 1px solid var(--border); background: var(--surface); padding: 11px 14px; }
.dashboard-boundary summary { color: var(--ink); cursor: pointer; font-size: 16px; }
.dashboard-boundary p { margin: 10px 0 0; color: var(--muted); font-size: 16px; line-height: 1.65; }
.carbon-section { min-width: 0; padding: 20px; border: 1px solid var(--border); background: var(--surface); }
.section-heading { display: flex; justify-content: space-between; gap: 18px; align-items: start; margin-bottom: 12px; }
.section-heading > div { min-width: 0; }
.carbon-eye-page .section-heading h2 { margin: 0 0 6px; font-size: 20px; line-height: 1.3; letter-spacing: 0; overflow-wrap: anywhere; word-break: break-word; }
.section-heading > p { max-width: 48ch; margin-bottom: 0; font-size: 16px; }
.section-note, .experimental-note { margin: 0 0 14px; padding: 10px 12px; border-left: 3px solid var(--border); background: var(--surface); font-size: 16px; }
.warning-note { border-left-color: var(--border); }
.chart { width: 100%; min-height: 320px; }
.chart-tall { min-height: 380px; }
.chart-medium { min-height: 330px; }
.two-column { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.compact-section { min-height: 0; }
.site-layout { display: grid; grid-template-columns: minmax(260px, .7fr) minmax(0, 1.3fr); gap: 18px; }
.site-overview { display: grid; gap: 12px; align-content: start; }
.site-map { position: relative; min-height: 260px; border: 1px solid var(--border); background: var(--surface); overflow: hidden; }
.site-map::before, .site-map::after { content: ''; position: absolute; inset: 12% 8%; border: 1px dashed rgba(125, 211, 252, .28); transform: rotate(-12deg); }
.site-map::after { inset: 30% 16%; transform: rotate(20deg); border-color: rgba(94, 234, 212, .2); }
.map-title, .map-scale { position: absolute; z-index: 1; color: var(--muted); font-size: 14px; }
.map-title { left: 12px; top: 10px; font-weight: 700; color: var(--ink); }
.map-scale-north { right: 12px; top: 10px; }
.map-scale-south { right: 12px; bottom: 10px; }
.site-marker { position: absolute; z-index: 2; transform: translate(-50%, -50%); width: 34px; height: 34px; border: 2px solid var(--border); border-radius: 50%; background: var(--surface); color: var(--ink); font-size: 14px; font-weight: 800; cursor: pointer; }
.site-marker:hover, .site-marker.active { border-color: var(--border); background: var(--surface); box-shadow: 0 0 0 4px rgba(251, 191, 36, .16); }
.site-list { display: grid; gap: 8px; align-content: start; }
.site-button { display: grid; grid-template-columns: 32px minmax(0, 1fr); text-align: left; gap: 3px 8px; padding: 10px; color: var(--ink); border: 1px solid var(--border); background: var(--surface); cursor: pointer; }
.site-button:hover, .site-button.active { border-color: var(--border); background: var(--surface); }
.site-button strong { grid-row: span 2; color: var(--green); }
.site-button span, .site-button small { min-width: 0; overflow-wrap: anywhere; }
.site-button small { color: var(--muted); font-size: 14px; }
.snapshot-detail { min-width: 0; }
.snapshot-selected { display: flex; justify-content: space-between; gap: 14px; align-items: end; margin-bottom: 12px; }
.snapshot-selected span, .snapshot-selected p { color: var(--muted); font-size: 14px; }
.snapshot-selected strong { display: block; margin-top: 4px; }
.table-wrap { max-width: 100%; overflow-x: auto; border: 1px solid var(--border); }
.data-table { width: 100%; min-width: 700px; border-collapse: collapse; font-size: 14px; }
.data-table th, .data-table td { padding: 10px 11px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--border); line-height: 1.5; }
.data-table th { position: sticky; top: 0; background: var(--surface); color: var(--ink); white-space: nowrap; }
.data-table td { color: var(--muted); }
.warning-row { cursor: pointer; }
.warning-row:hover td, .warning-row.active td { background: var(--surface); }
.warning-workbench { margin-top: 14px; padding: 16px; border: 1px solid var(--border); background: var(--surface); }
.warning-workbench h3 { margin-bottom: 12px; color: var(--ink); }
.warning-detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 0; }
.warning-detail-grid div { min-width: 0; padding: 10px; border: 1px solid var(--border); background: var(--surface); }
.warning-detail-grid dt { color: var(--blue); font-size: 14px; margin-bottom: 5px; }
.warning-detail-grid dd { margin: 0; color: var(--muted); font-size: 16px; line-height: 1.6; overflow-wrap: anywhere; }
.sensitivity-wrap { margin-top: 14px; }
.industry-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.industry-item { padding: 14px; border: 1px solid var(--border); background: var(--surface); min-width: 0; }
.industry-item h3 { color: var(--ink); margin-bottom: 10px; }
.industry-item p { color: var(--muted); font-size: 16px; line-height: 1.6; }
.industry-item b { color: var(--ink); }
.industry-item small { color: var(--muted); line-height: 1.5; }
.governance-context { padding: 12px; margin-bottom: 12px; border-left: 3px solid var(--border); background: var(--surface); }
.governance-context p, .governance-context small { color: var(--muted); line-height: 1.6; }
.governance-list, .method-list, .boundary-list { display: grid; gap: 10px; padding-left: 18px; margin: 0; }
.governance-list li { display: grid; gap: 4px; color: var(--muted); line-height: 1.55; }
.governance-list small { color: var(--muted); }
.method-list li, .boundary-list li { color: var(--muted); line-height: 1.6; }
.source-list { display: grid; gap: 8px; margin-top: 16px; }
.source-list a, .source-list span { color: var(--blue); font-size: 14px; line-height: 1.5; overflow-wrap: anywhere; }
.source-list span { color: var(--muted); }
.source-details { margin-top: 4px; }
.source-details summary { color: var(--ink); cursor: pointer; font-size: 16px; }
.source-list-expanded { margin-top: 10px; }
.boundary-section { border-color: var(--border); }
.carbon-footer { padding: 15px 0 4px; color: var(--muted); font-size: 16px; text-align: center; }

@media (max-width: 1100px) {
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .industry-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
  .carbon-topbar, .carbon-header, .section-heading, .snapshot-selected { align-items: start; flex-direction: column; }
  .carbon-header, .two-column, .site-layout { grid-template-columns: 1fr; }
  .metric-grid, .industry-grid { grid-template-columns: 1fr; }
  .warning-detail-grid { grid-template-columns: 1fr; }
  .metric-card { min-height: 106px; }
  .carbon-section { padding: 15px; }
  .chart, .chart-medium, .chart-tall { min-height: 300px; }
  .section-heading > p { max-width: none; }
  h1 { font-size: 27px; }
  .carbon-eye-page .section-heading h2 { font-size: 19px; line-height: 1.35; }
}
</style>
