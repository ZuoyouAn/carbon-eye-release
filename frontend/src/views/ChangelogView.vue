<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Changelog</p>
        <h1>站点更新日志</h1>
        <p>以后每做一个版本，都可以在这里记下来。</p>
      </div>

      <div class="timeline-list">
        <article v-for="log in logs" :key="log.version" class="content-card">
          <div class="card-meta">
            <span>{{ log.version }}</span>
            <span>{{ log.date }}</span>
          </div>
          <h2>{{ log.title }}</h2>
          <p>{{ log.text }}</p>
          <div class="tag-list">
            <span v-for="tag in log.tags" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'

const logs = [
  { version: 'v6', date: '2026-10-05', title: '建一座营地，看懂一次运算', text: '末世游戏新主玩法改为余烬营地：采集、五类建造、供电、补给生产、维修、三夜防卫及黎明升级，保留城市探索和旧剧情。新增浏览器本地 PDF / Word 转换，预览后导出，明确扫描件与排版限制；新增七类密码算法实验，显示真实矩阵、寄存器、模幂轨迹、单步播放和原理流程图。文件与实验输入不上传，不新增收费服务。', tags: ['Base Survival', 'Local Conversion', 'Crypto Visualization', 'Privacy'] },
  { version: 'v5.2', date: '2026-10-05', title: '看得清，也玩得顺', text: '全站正文、标签与输入字号放大，窄屏导航同步调整。末世探索加入固定北向战术地图、下一目标、就近拾取、健康体力条、五分钟练习模式和场景展开；太阳系加入原创程序化表面、俯视与跟随观察、轨道开关、示意时间拖动及标签避让。参考站未找到站点级复用许可，未复制其业务代码或素材。', tags: ['Readability', 'Game Navigation', 'Planet Surfaces', 'Camera Controls'] },
  { version: 'v5.1', date: '2026-10-05', title: '从探索，到持续阅读', text: '太阳系新增十个历史航天任务档案、目标筛选和图谱标记，每项附 NASA 来源，不冒充实时轨迹。人生指南逐章展示并复用内存索引，保留失败章节重试；支持条目分享、筛选链接、可选本机收藏与继续阅读，默认不保存记录。', tags: ['Mission Archive', 'Progressive Reading', 'Local Privacy'] },
  { version: 'v5', date: '2026-10-05', title: '浅色 Space：探索城市、宇宙与生活', text: '整体界面升级为浅色留白与轻动效；末世模拟器加入原创低多边形3D城市，可键盘和摇杆探索，保留三十天剧情与旧存档。新增原创太阳系图谱与人生指南原文检索，明确示意比例、来源和开放许可；不新增付费服务。', tags: ['Light Design', 'Three.js', 'Solar Atlas', 'Life Guide'] },
  { version: 'v4.2', date: '2026-10-05', title: '阅读更稳，弱网可恢复', text: '小说列表不再下载所有正文；文章和帖子详情减少无关请求。快速切换和搜索只采用最新结果，读取失败明确提示并支持重试，搜索支持回车。公开读取移除不必要的跨域预检请求头。', tags: ['Reading', 'Resilience', 'Network'] },
  { version: 'v4.1', date: '2026-10-05', title: '加载更轻，聊天更顺', text: '组件样式按页面加载；聊天支持历史阅读位置保留、新消息提示和切换会话暂存草稿，明确私聊发送状态，网络失败自动退避。游戏遵循减少动态效果偏好。', tags: ['Performance', 'Chat UX', 'Accessibility'] },
  { version: 'v4', date: '2026-10-04', title: '左右的Space：连接与冒险', text: '统一Space品牌，新增持久化用户头像、公共大厅、邀请制小群和双向同意私聊；上线原创文字游戏末世模拟器，支持本机存档与生存日记。', tags: ['Avatar', 'Chat', 'Wasteland'] },
  { version: 'v3', date: '2026-05-28', title: '内容管理完整化', text: '新增后台内容管理、留言板、分页、软删除和 Element Plus 交互。', tags: ['Admin', 'Messages', 'Pagination'] },
  { version: 'v2', date: '2026-05-27', title: 'Space 全栈化', text: '新增 Vue Router、文章、帖子、小说阅读、点赞收藏和个人中心。', tags: ['Vue Router', 'FastAPI', 'MySQL'] },
  { version: 'v1', date: '2026-05-24', title: '首页搭建', text: '完成 Space 首页和基础视觉。', tags: ['HTML', 'CSS', 'Vue'] },
]
</script>
