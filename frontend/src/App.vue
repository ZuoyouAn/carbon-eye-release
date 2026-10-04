<template>
  <div class="app-shell">
    <a class="skip-link" href="#page-content">跳到正文</a>
    <header class="site-header">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">左</span>
        <span>左右的个人网站</span>
      </RouterLink>

      <button class="menu-toggle nav-button" type="button" aria-controls="main-navigation" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen">{{ menuOpen ? '收起导航 ×' : '浏览菜单 ☰' }}</button>
      <nav id="main-navigation" class="nav-links" :class="{ 'menu-open': menuOpen }" aria-label="主导航" @keydown.esc="menuOpen = false">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/novels">小说</RouterLink>
        <RouterLink to="/posts">帖子</RouterLink>
        <RouterLink to="/articles">文章</RouterLink>
        <RouterLink to="/projects">项目</RouterLink>
        <RouterLink to="/human3">成长评估</RouterLink>
        <RouterLink to="/store">数字商品</RouterLink>
        <details class="nav-more"><summary>更多</summary><div>
        <RouterLink to="/roadmap">学习路线</RouterLink>
        <RouterLink to="/timeline">时间线</RouterLink>
        <RouterLink to="/messages">留言板</RouterLink>
        <RouterLink to="/changelog">更新日志</RouterLink>
        <RouterLink to="/secure-geometry">安全计算</RouterLink>
        </div></details>
        <RouterLink v-if="isLoggedIn" to="/profile">个人中心</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin">管理后台</RouterLink>
        <RouterLink v-if="isAdmin" class="nav-strong" to="/admin/articles/new">写文章</RouterLink>
        <RouterLink v-if="!isLoggedIn" class="nav-strong" to="/login">登录</RouterLink>
        <RouterLink v-if="!isLoggedIn" to="/register">注册</RouterLink>
        <button v-else type="button" class="nav-button" @click="handleLogout">退出</button>
      </nav>
    </header>

    <div class="status-strip">
      <span v-if="isLoggedIn">当前登录：{{ authState.user.username }} / {{ roleLabel(authState.user.role) }}</span>
      <span v-else>游客可浏览内容；登录后可点赞和收藏，发布内容需要高权限。</span>
      <strong v-if="isMuted">你已被禁言，不能发布内容。</strong>
    </div>

    <div id="page-content" tabindex="-1"><RouterView v-slot="{ Component }">
      <Transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView></div>
    <footer class="site-footer"><span>左右 · 记录学习，连接生活。</span><div><RouterLink to="/human3">四维成长地图</RouterLink><RouterLink to="/store">数字商品 · 筹备中</RouterLink><RouterLink to="/changelog">更新记录</RouterLink></div></footer>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { authState, isAdmin, isLoggedIn, isMuted, logout, refreshMe } from './stores/auth'
import { roleLabel } from './utils/permissions'

const router = useRouter()
const menuOpen = ref(false)
watch(() => router.currentRoute.value.fullPath, () => {
  menuOpen.value = false
  document.querySelector('.nav-more')?.removeAttribute('open')
})

onMounted(() => {
  refreshMe()
  window.addEventListener('auth-invalidated', handleInvalidated)
})

onUnmounted(() => window.removeEventListener('auth-invalidated', handleInvalidated))

function handleInvalidated() {
  if (router.currentRoute.value.meta.requiresAuth) {
    router.replace({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  }
}

async function handleLogout() {
  await logout()
  router.push('/')
}
</script>
