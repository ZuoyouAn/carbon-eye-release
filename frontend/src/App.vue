<template>
  <div class="app-shell">
    <header class="site-header">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">左</span>
        <span>左右的个人网站</span>
      </RouterLink>

      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/novels">小说</RouterLink>
        <RouterLink to="/posts">帖子</RouterLink>
        <RouterLink to="/articles">文章</RouterLink>
        <RouterLink to="/roadmap">路线</RouterLink>
        <RouterLink to="/projects">项目</RouterLink>
        <RouterLink to="/timeline">时间线</RouterLink>
        <RouterLink to="/messages">留言板</RouterLink>
        <RouterLink to="/changelog">更新日志</RouterLink>
        <RouterLink to="/secure-geometry">安全计算</RouterLink>
        <RouterLink v-if="isLoggedIn" to="/profile">个人中心</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin">管理后台</RouterLink>
        <RouterLink v-if="isAdmin" class="nav-strong" to="/admin/articles/new">写文章</RouterLink>
        <RouterLink v-if="!isLoggedIn" class="nav-strong" to="/login">登录</RouterLink>
        <RouterLink v-if="!isLoggedIn" to="/register">注册</RouterLink>
        <button v-else type="button" class="nav-button" @click="handleLogout">退出</button>
      </nav>
    </header>

    <div class="status-strip">
      <span v-if="isLoggedIn">当前登录：{{ authState.user.username }} / {{ isAdmin ? '管理员' : '普通用户' }}</span>
      <span v-else>游客模式：可以浏览内容，发布、评论、点赞和收藏需要登录。</span>
      <strong v-if="isMuted">你已被禁言，不能发帖或评论。</strong>
    </div>

    <RouterView v-slot="{ Component }">
      <Transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { authState, isAdmin, isLoggedIn, isMuted, logout, refreshMe } from './stores/auth'

const router = useRouter()

onMounted(() => {
  refreshMe()
})

async function handleLogout() {
  await logout()
  router.push('/')
}
</script>
