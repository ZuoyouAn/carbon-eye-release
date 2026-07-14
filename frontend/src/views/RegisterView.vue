<template>
  <main class="content-page">
    <section class="panel narrow-panel">
      <RouterLink class="back-button" to="/">返回首页</RouterLink>
      <p class="eyebrow">Register</p>
      <h1>注册</h1>
      <p class="panel-text">注册后就是普通用户，可以进入帖子和文章评论区互动。</p>

      <form class="form-stack" @submit.prevent="submitRegister">
        <label>
          用户名
          <input v-model="form.username" type="text" autocomplete="username" placeholder="例如 zuoyou">
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 3 个字符">
        </label>
        <button class="button button-primary" type="submit">注册</button>
      </form>

      <RouterLink class="text-button" to="/login">已有账号？去登录</RouterLink>
      <p v-if="message" class="message">{{ message }}</p>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { register } from '../stores/auth'

const router = useRouter()
const message = ref('')
const form = ref({ username: '', password: '' })

async function submitRegister() {
  message.value = ''
  try {
    await register(form.value)
    router.push('/login')
  } catch (error) {
    message.value = error.message
  }
}
</script>
