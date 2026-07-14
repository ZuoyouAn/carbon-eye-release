<template>
  <main class="content-page">
    <section class="panel secure-lab-page">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Secure Geometry Lab</p>
        <h1>安全多方计算实验室</h1>
        <p>把论文里的保密内积协议做成一个可交互演示：Alice 和 Bob 各自输入秘密几何对象，页面只展示最终位置关系。</p>
        <RouterLink class="text-button" to="/secure-geometry/paper">阅读论文笔记</RouterLink>
      </div>

      <div class="secure-tabs">
        <button
          v-for="relation in relations"
          :key="relation.id"
          type="button"
          :class="{ active: relation.id === activeRelationId }"
          @click="selectRelation(relation.id)"
        >
          <span>{{ relation.badge }}</span>
          {{ relation.title }}
        </button>
      </div>

      <div class="secure-lab-grid">
        <section class="secure-box alice-box">
          <div class="secure-box-head">
            <span>Alice</span>
            <strong>{{ activeRelation.aliceLabel }}</strong>
          </div>
          <p>{{ activeRelation.aliceHint }}</p>
          <textarea v-model="aliceInput" spellcheck="false"></textarea>
        </section>

        <section class="secure-box bob-box">
          <div class="secure-box-head">
            <span>Bob</span>
            <strong>{{ activeRelation.bobLabel }}</strong>
          </div>
          <p>{{ activeRelation.bobHint }}</p>
          <textarea v-model="bobInput" spellcheck="false"></textarea>
        </section>

        <section class="secure-box result-box">
          <div class="secure-box-head">
            <span>Result</span>
            <strong>{{ activeRelation.title }}</strong>
          </div>
          <p>点击计算后，前端会把 JSON 参数发给 FastAPI，后端调用算法模块实时计算。</p>
          <button class="button button-primary" type="button" :disabled="loading" @click="calculate">
            {{ loading ? '正在计算...' : '执行安全计算模拟' }}
          </button>

          <div v-if="error" class="secure-error">{{ error }}</div>
          <div v-if="result" class="secure-result">
            <span>计算结果</span>
            <strong>{{ result.result }}</strong>
            <p>{{ result.note }}</p>
          </div>
        </section>
      </div>

      <div class="secure-example-bar">
        <span>示例参数</span>
        <button
          v-for="example in activeRelation.examples"
          :key="example.name"
          type="button"
          class="mini-button"
          :class="{ active: example.name === currentExampleName }"
          @click="loadExample(example)"
        >
          {{ example.name }}
        </button>
      </div>

      <div class="secure-info-grid">
        <article class="content-card">
          <div class="card-meta">
            <span>Protocol</span>
            <span>{{ activeRelation.badge }}</span>
          </div>
          <h2>协议步骤</h2>
          <ol class="secure-step-list">
            <li v-for="step in shownSteps" :key="step">{{ step }}</li>
          </ol>
        </article>

        <article class="content-card">
          <div class="card-meta">
            <span>Input Format</span>
            <span>JSON</span>
          </div>
          <h2>输入格式</h2>
          <p>点写成 <code>[x, y, z]</code>，平面写成 <code>[A, B, C, D]</code>，表示 <code>Ax + By + Cz + D = 0</code>。</p>
          <p>直线用两个平面的交线表示：<code>[[A1,B1,C1,D1], [A2,B2,C2,D2]]</code>。</p>
        </article>

        <article class="content-card">
          <div class="card-meta">
            <span>Note</span>
            <span>Teaching Demo</span>
          </div>
          <h2>实验定位</h2>
          <p>这一版演示的是论文思路和计算流程，不保存 Alice/Bob 输入，也不把它当生产级密码系统使用。</p>
          <p>可以先阅读论文笔记理解背景，再回来用示例参数跑完整协议流程。</p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { postJson } from '../api/client'

const relations = [
  {
    id: 'point_line',
    title: '点线关系',
    badge: '协议 1',
    aliceLabel: '秘密点',
    bobLabel: '秘密直线',
    aliceHint: 'Alice 输入自己的空间点，例如 {"point":[0,0,3]}。',
    bobHint: 'Bob 输入自己的直线，两条平面方程的交线就是直线。',
    examples: [
      { name: '点在直线上', alice: { point: [0, 0, 3] }, bob: { line: [[1, 0, 0, 0], [0, 1, 0, 0]] } },
      { name: '点不在直线上', alice: { point: [1, 0, 3] }, bob: { line: [[1, 0, 0, 0], [0, 1, 0, 0]] } },
    ],
  },
  {
    id: 'point_plane',
    title: '点面关系',
    badge: '协议 2',
    aliceLabel: '秘密点',
    bobLabel: '秘密平面',
    aliceHint: 'Alice 输入自己的空间点。',
    bobHint: 'Bob 输入自己的平面方程 Ax + By + Cz + D = 0。',
    examples: [
      { name: '点在平面上', alice: { point: [0, 2, 3] }, bob: { plane: [1, 0, 0, 0] } },
      { name: '点不在平面上', alice: { point: [1, 2, 3] }, bob: { plane: [1, 0, 0, 0] } },
    ],
  },
  {
    id: 'line_line',
    title: '线线关系',
    badge: '协议 3',
    aliceLabel: '秘密直线',
    bobLabel: '秘密直线',
    aliceHint: 'Alice 输入自己的直线。',
    bobHint: 'Bob 输入自己的直线，系统会判断重合、平行、相交或异面。',
    examples: [
      { name: '相交', alice: { line: [[1, 0, 0, 0], [0, 1, 0, 0]] }, bob: { line: [[0, 1, 0, 0], [0, 0, 1, 0]] } },
      { name: '平行', alice: { line: [[1, 0, 0, 0], [0, 1, 0, 0]] }, bob: { line: [[1, 0, 0, -1], [0, 1, 0, 0]] } },
      { name: '异面', alice: { line: [[0, 1, 0, 0], [0, 0, 1, 0]] }, bob: { line: [[1, 0, 0, 0], [0, 0, 1, -1]] } },
    ],
  },
  {
    id: 'line_plane',
    title: '线面关系',
    badge: '协议 4',
    aliceLabel: '秘密直线',
    bobLabel: '秘密平面',
    aliceHint: 'Alice 输入自己的直线。',
    bobHint: 'Bob 输入自己的平面，系统会判断重合、平行或相交。',
    examples: [
      { name: '重合', alice: { line: [[1, 0, 0, 0], [0, 1, 0, 0]] }, bob: { plane: [1, 0, 0, 0] } },
      { name: '平行', alice: { line: [[1, 0, 0, -1], [0, 1, 0, 0]] }, bob: { plane: [1, 0, 0, 0] } },
      { name: '相交', alice: { line: [[0, 1, 0, 0], [0, 0, 1, 0]] }, bob: { plane: [1, 0, 0, -1] } },
    ],
  },
  {
    id: 'plane_plane',
    title: '面面关系',
    badge: '协议 5',
    aliceLabel: '秘密平面',
    bobLabel: '秘密平面',
    aliceHint: 'Alice 输入自己的平面。',
    bobHint: 'Bob 输入自己的平面，系统会判断重合、平行或相交。',
    examples: [
      { name: '重合', alice: { plane: [1, 0, 0, 0] }, bob: { plane: [2, 0, 0, 0] } },
      { name: '平行', alice: { plane: [1, 0, 0, 0] }, bob: { plane: [1, 0, 0, -1] } },
      { name: '相交', alice: { plane: [1, 0, 0, 0] }, bob: { plane: [0, 1, 0, 0] } },
    ],
  },
]

const activeRelationId = ref('point_line')
const aliceInput = ref('')
const bobInput = ref('')
const currentExampleName = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)

const activeRelation = computed(() => relations.find((relation) => relation.id === activeRelationId.value) || relations[0])
const shownSteps = computed(() => result.value?.steps || ['选择一种位置关系实验。', '套用示例或手动填写 Alice/Bob 输入。', '点击按钮查看后端计算结果。'])

watch(activeRelationId, () => {
  loadExample(activeRelation.value.examples[0])
}, { immediate: true })

function selectRelation(relationId) {
  activeRelationId.value = relationId
}

function formatJson(value) {
  return JSON.stringify(value, null, 2)
}

function loadExample(example) {
  aliceInput.value = formatJson(example.alice)
  bobInput.value = formatJson(example.bob)
  currentExampleName.value = example.name
  result.value = null
  error.value = ''
}

function parseInput(text, label) {
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`${label} 不是合法 JSON，请检查括号、逗号和引号`)
  }
}

async function calculate() {
  error.value = ''
  result.value = null
  loading.value = true

  try {
    const payload = {
      relation: activeRelation.value.id,
      alice: parseInput(aliceInput.value, 'Alice 输入'),
      bob: parseInput(bobInput.value, 'Bob 输入'),
    }
    result.value = await postJson('/api/secure-geometry/calculate', payload)
    ElMessage.success(`计算完成：${result.value.result}`)
  } catch (err) {
    error.value = err.message
    ElMessage.error(err.message)
  } finally {
    loading.value = false
  }
}
</script>
