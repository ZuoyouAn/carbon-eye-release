<template>
  <main class="content-page">
    <section class="panel narrow-panel">
      <RouterLink class="back-button" to="/">返回首页</RouterLink>
      <p class="eyebrow">Register</p>
      <h1>注册</h1>
      <p class="panel-text">新账号默认低权限，可点赞、收藏和保存阅读进度。需要发布内容时，请联系管理员提升权限。</p>

      <form class="form-stack" @submit.prevent="submitRegister">
        <label>
          用户名
          <input v-model="form.username" type="text" autocomplete="username" placeholder="例如 zuoyou">
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" autocomplete="new-password" minlength="8" maxlength="80" placeholder="至少 8 个字符，不使用常见弱密码">
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
