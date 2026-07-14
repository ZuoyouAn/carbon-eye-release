<template>
  <main class="content-page">
    <section class="panel narrow-panel">
      <RouterLink class="back-button" to="/">返回首页</RouterLink>
      <p class="eyebrow">Login</p>
      <h1>登录</h1>
      <p class="panel-text">普通用户可以发帖、评论、点赞和收藏。管理员账号是 root，密码是 123456。</p>

      <form class="form-stack" @submit.prevent="submitLogin">
        <label>
          用户名
          <input v-model="form.username" type="text" autocomplete="username" placeholder="请输入用户名">
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" autocomplete="current-password" placeholder="请输入密码">
        </label>
        <button class="button button-primary" type="submit">登录</button>
      </form>

      <RouterLink class="text-button" to="/register">没有账号？去注册</RouterLink>
      <p v-if="message" class="message">{{ message }}</p>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { login } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const message = ref('')
const form = ref({ username: '', password: '' })

async function submitLogin() {
  message.value = ''
  try {
    await login(form.value)
    router.push(route.query.redirect || '/')
  } catch (error) {
    message.value = error.message
  }
}
</script>
