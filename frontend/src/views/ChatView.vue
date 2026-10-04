<template>
  <main class="content-page chat-page">
    <section class="section-heading"><p class="eyebrow">SPACE / CONNECTIONS</p><h1>聊聊正在发生的事。</h1><p>公共大厅、小群与私聊。消息保留30天，连接彼此，也尊重彼此的边界。</p></section>
    <details class="chat-rules panel"><summary>聊天规则与隐私说明</summary><p>所有正常注册用户均可在大厅聊天。高权限及管理员可建小群，每群最多12人；被邀请人接受后才能读消息。私聊须双方接受，拒绝或退出后本版本不重复邀请。拉黑阻止双方私聊与新邀请，不隐藏公共群消息。</p><p>每条最多1000字，至少间隔3秒，每人每日最多200条；全站每日最多1000条。邀请操作每人每天5次。仅文字消息，不上传附件、不渲染HTML；禁言账号只能读。你可以撤回自己的消息，管理员只能治理公共大厅，不能绕过成员校验查看私聊。</p><p>消息通过HTTPS传输并存储在数据库，不是端到端加密。应用内管理员无权查看非成员私聊，但数据库运营者仍有技术访问能力，请勿发送密码或敏感隐私。超过30天的消息不可查看，并在之后发送消息时清理。仅页面可见时每12秒同步，非毫秒级即时通讯。</p></details>
    <p v-if="notice" class="message" role="status">{{ notice }}</p>
    <div class="chat-layout">
      <aside class="panel chat-sidebar"><div class="chat-sidebar-heading"><h2>我的会话</h2><button class="text-button" :disabled="busy" @click="refreshAll">刷新</button></div><p v-if="loading" role="status" class="panel-text">正在连接…免费服务首次唤醒可能稍慢。</p><button v-for="room in rooms" :key="room.id" class="room-button" :class="{ selected: room.id === selectedId }" @click="selectRoom(room.id)"><span class="room-symbol">{{ room.kind === 'direct' ? '↗' : '#' }}</span><span><strong>{{ room.name }}</strong><small>{{ roomLabel(room) }}</small></span></button>
        <form class="chat-search" @submit.prevent="searchUsers"><label for="chat-user-search">找一位朋友</label><div><input id="chat-user-search" v-model="query" maxlength="30" placeholder="输入至少2字用户名"><button class="text-button" :disabled="busy">查找</button></div></form><p v-if="searched && !users.length" class="panel-text">没有匹配的用户，或你们之间已关闭邀请。</p><div v-for="user in users" :key="user.id" class="chat-person"><UserAvatar :user="user" :size="32" /><span>{{ user.username }}</span><button class="text-button" :disabled="!canChat || busy" @click="startDirect(user.id)">私聊</button><button v-if="activeRoom?.kind === 'group' && activeRoom.owner_id === authState.user?.id" class="text-button" :disabled="!canChat || busy" @click="inviteUser(user.id)">邀请</button></div>
        <form v-if="canPublish" class="chat-search" @submit.prevent="createGroup"><label for="chat-group-name">创建小群</label><input id="chat-group-name" v-model="groupName" maxlength="40" placeholder="给小群起个名字"><button class="button button-secondary" :disabled="busy || !groupName.trim()">创建并进入</button></form><details class="chat-blocks"><summary>我的拉黑名单（{{ blocks.length }}）</summary><div v-for="user in blocks" :key="user.id" class="chat-person"><span>{{ user.username }}</span><button class="text-button" :disabled="busy" @click="unblockUser(user.id)">解除</button></div></details>
      </aside>
      <section class="panel chat-conversation">
        <template v-if="activeRoom">
          <header class="conversation-heading">
            <div><p class="panel-label">{{ activeRoom.kind === 'direct' ? 'PRIVATE / 1:1' : 'GROUP / SPACE' }}</p><h2>{{ activeRoom.name }}</h2></div>
            <div class="chat-tools">
              <button v-if="activeRoom.kind === 'direct' && activeRoom.other_id" class="text-button" :disabled="busy" @click="blockUser(activeRoom.other_id)">拉黑</button>
              <button v-if="activeRoom.kind !== 'public' && activeRoom.status === 'accepted'" class="text-button" :disabled="busy" @click="leaveRoom">退出会话</button>
            </div>
          </header>
          <div v-if="activeRoom.status === 'invited'" class="chat-invitation">
            <h3>你收到了一个{{ activeRoom.kind === 'direct' ? '私聊' : '群聊' }}邀请。</h3>
            <p>接受后才能查看该会话的消息，包括仍在保留期内的历史。你也可以拒绝。</p>
            <button class="button button-primary" :disabled="!canChat || busy" @click="decideInvitation(true)">接受邀请</button>
            <button class="button button-secondary" :disabled="busy" @click="decideInvitation(false)">拒绝</button>
          </div>
          <template v-else>
            <div v-if="members.length" class="conversation-members"><span v-for="user in members" :key="user.id">{{ user.username }}{{ user.status === 'invited' ? '（待接受）' : '' }}</span></div>
            <div ref="messageArea" class="chat-messages" aria-label="聊天记录" :aria-busy="historyLoading">
              <button v-if="hasMore" class="text-button" :disabled="historyLoading" @click="loadOlder">查看更早消息</button>
              <p v-if="!messages.length" class="chat-empty">{{ historyLoading ? '正在读取消息…' : '还没有消息。可以从一句近况开始。' }}</p>
              <article v-for="item in messages" :key="item.id" :data-message-id="item.id" class="chat-message" :class="{ own: item.sender.id === authState.user?.id }">
                <UserAvatar :user="item.sender" :size="34" />
                <div><div class="chat-message-meta"><strong>{{ item.sender.username }}</strong><time :datetime="item.created_at">{{ formatTime(item.created_at) }}</time><button v-if="item.can_retract" class="human-link-button chat-retract" :disabled="busy" @click="retract(item)">撤回</button></div><p :class="{ retracted: item.is_deleted }">{{ item.is_deleted ? '消息已撤回' : item.content }}</p></div>
              </article>
            </div>
            <div v-if="readingHistory || hasNewMessages" class="chat-history-bar" role="status">
              <span>{{ hasNewMessages ? '有新消息，阅读位置已为你保留。' : '正在浏览历史，每次最多保留200条。' }}</span>
              <button class="text-button" :disabled="historyLoading" @click="syncMessages(true)">回到最新消息 ↓</button>
            </div>
            <p class="chat-sync" role="status">{{ syncError ? `同步暂不可用：${syncError} · 正在降低频率重试` : lastSync ? `最近同步 ${lastSync} · 可见时约每12秒更新` : '准备同步' }}</p>
            <form class="chat-composer" @submit.prevent="send">
              <label class="sr-only" for="chat-content">消息内容</label>
              <textarea id="chat-content" v-model="draft" maxlength="1000" :disabled="!canSend" :placeholder="disabledReason || '写下你想分享的近况… Ctrl / ⌘ + Enter 发送'" @keydown.ctrl.enter.prevent="send" @keydown.meta.enter.prevent="send"></textarea>
              <div><span>{{ draft.length }} / 1000 · {{ disabledReason || '请勿发送密码或敏感信息' }}</span><button class="button button-primary" :disabled="!canSend || !draft.trim()">{{ sending ? '发送中…' : '发送消息' }}</button></div>
              <p class="chat-sync">草稿仅在本次聊天页面暂存；刷新或离开页面后清除。</p>
            </form>
          </template>
        </template>
        <div v-else class="chat-empty"><h2>选择一个会话。</h2><p>可进入大厅，或查找用户名发起私聊。</p></div>
      </section>
    </div>
  </main>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiRequest, postJson, putJson, deleteRequest } from '../api/client.js'
import { authState, canPublish } from '../stores/auth.js'
import { mergeLatest, prependHistory, composerReason } from '../features/chat/history.js'
import UserAvatar from '../components/UserAvatar.vue'

const rooms = ref([]), selectedId = ref('public-lobby'), messages = ref([]), members = ref([]), blocks = ref([]), users = ref([])
const query = ref(''), groupName = ref(''), draft = ref(''), notice = ref(''), syncError = ref(''), lastSync = ref('')
const loading = ref(true), busy = ref(false), sending = ref(false), hasMore = ref(false), historyLoading = ref(false), searched = ref(false)
const readingHistory = ref(false), hasNewMessages = ref(false), messageArea = ref(null)
const activeRoom = computed(() => rooms.value.find(room => room.id === selectedId.value))
const canChat = computed(() => authState.user && !authState.user.is_muted && !authState.user.is_deleted && ['user', 'elevated', 'admin'].includes(authState.user.role))
const disabledReason = computed(() => composerReason(activeRoom.value, authState.user))
const canSend = computed(() => !disabledReason.value && !busy.value && !sending.value)
const drafts = new Map(), retries = new Map() // Memory only: never store private chat text in localStorage.
let timer, controller, listController, disposed = false, revision = 0, failures = 0, latestId = 0

function formatTime(value) { return new Date(value).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }
function roomLabel(room) {
  if (room.status === 'invited') return '邀请待处理'
  if (room.kind !== 'direct') return '群聊'
  return ({ pending: '等待对方接受', closed: '会话已关闭', blocked: '私聊已关闭', ready: '一对一私聊' })[room.send_state] || '确认会话状态中'
}
function schedule() {
  clearTimeout(timer)
  if (!disposed && !document.hidden) timer = setTimeout(refreshAll, Math.min(60000, 12000 * 2 ** Math.min(failures, 3)))
}
async function scrollBottom() { await nextTick(); if (messageArea.value) messageArea.value.scrollTop = messageArea.value.scrollHeight }
function selectRoom(id) { selectedId.value = id }
watch(selectedId, (id, previousId) => {
  if (previousId) drafts.set(previousId, draft.value)
  revision++; controller?.abort()
  messages.value = []; members.value = []; draft.value = drafts.get(id) || ''
  lastSync.value = ''; hasMore.value = false; syncError.value = ''; readingHistory.value = false; hasNewMessages.value = false; latestId = 0
  historyLoading.value = false
  syncMessages(true)
})
async function refreshAll() {
  if (busy.value || disposed || document.hidden) return
  clearTimeout(timer)
  busy.value = true
  const request = new AbortController(); listController?.abort(); listController = request
  try {
    const [list, blocked] = await Promise.all([apiRequest('/api/chat/rooms', { signal: request.signal }), apiRequest('/api/chat/blocks', { signal: request.signal })])
    if (disposed || request.signal.aborted) return
    rooms.value = list; blocks.value = blocked
    if (!activeRoom.value) selectedId.value = 'public-lobby'
    const ok = await syncMessages(!messages.value.length && !historyLoading.value)
    failures = ok === false ? failures + 1 : 0
  } catch (error) {
    if (!disposed && !request.signal.aborted) { syncError.value = error.message; failures++ }
  } finally { busy.value = false; loading.value = false; schedule() }
}
async function syncMessages(force = false) {
  const room = activeRoom.value
  if (!room || room.status === 'invited' || disposed || document.hidden || (historyLoading.value && !force)) return
  controller?.abort(); const request = new AbortController(); controller = request
  const id = selectedId.value, token = revision
  historyLoading.value = true
  const bottom = !messageArea.value || messageArea.value.scrollHeight - messageArea.value.scrollTop - messageArea.value.clientHeight < 80
  try {
    const [history, people] = await Promise.all([apiRequest(`/api/chat/rooms/${id}/messages`, { signal: request.signal }), apiRequest(`/api/chat/rooms/${id}/members`, { signal: request.signal })])
    if (disposed || token !== revision || request !== controller) return
    const reading = !force && (readingHistory.value || !bottom)
    const merged = mergeLatest(messages.value, history.items, reading)
    messages.value = merged.items; members.value = people; readingHistory.value = reading
    hasNewMessages.value = reading && (hasNewMessages.value || merged.hasNew)
    latestId = history.items.at(-1)?.id || 0
    if (!reading) hasMore.value = history.has_more
    lastSync.value = new Date().toLocaleTimeString('zh-CN'); syncError.value = ''
    if (force || (!reading && bottom)) await scrollBottom()
    return true
  } catch (error) {
    if (!disposed && request === controller && !request.signal.aborted) {
      syncError.value = error.message
      if ([401, 403, 404].includes(error.status)) { messages.value = []; members.value = []; hasMore.value = false }
      return false
    }
  } finally { if (request === controller) historyLoading.value = false }
}
function scrollAnchor() {
  if (!messageArea.value) return null
  const top = messageArea.value.getBoundingClientRect().top
  const row = [...messageArea.value.querySelectorAll('[data-message-id]')].find(item => item.getBoundingClientRect().bottom > top)
  return row ? { id: row.dataset.messageId, top: row.getBoundingClientRect().top } : null
}
async function loadOlder() {
  if (historyLoading.value || !messages.value.length) return
  controller?.abort(); const request = new AbortController(); controller = request
  historyLoading.value = true
  const id = selectedId.value, token = revision, anchor = scrollAnchor()
  try {
    const history = await apiRequest(`/api/chat/rooms/${id}/messages?before_id=${messages.value[0].id}`, { signal: request.signal })
    if (disposed || token !== revision || request !== controller) return
    messages.value = prependHistory(messages.value, history.items); hasMore.value = history.has_more; readingHistory.value = true
    hasNewMessages.value ||= latestId > (messages.value.at(-1)?.id || 0)
    await nextTick()
    const row = anchor && messageArea.value?.querySelector(`[data-message-id="${anchor.id}"]`)
    if (row) messageArea.value.scrollTop += row.getBoundingClientRect().top - anchor.top
  } catch (error) { if (!disposed && !request.signal.aborted) notice.value = error.message }
  finally { if (request === controller) historyLoading.value = false }
}
async function operation(task) {
  if (busy.value || disposed) return
  clearTimeout(timer); busy.value = true; notice.value = ''
  try { await task() } catch (error) { if (!disposed) notice.value = error.message }
  finally { busy.value = false; await refreshAll() }
}
async function searchUsers() {
  await operation(async () => {
    if (query.value.trim().length < 2) throw new Error('请输入至少2字用户名。')
    users.value = await apiRequest(`/api/chat/users?q=${encodeURIComponent(query.value.trim())}`); searched.value = true
  })
}
async function startDirect(id) { await operation(async () => { const room = await postJson('/api/chat/direct', { user_id: id }); selectedId.value = room.id; notice.value = '会话已打开；对方接受邀请后，双方才能发送消息。' }) }
async function createGroup() { await operation(async () => { const room = await postJson('/api/chat/groups', { name: groupName.value, user_ids: [] }); selectedId.value = room.id; groupName.value = ''; notice.value = '小群已创建。查找用户后可以邀请加入。' }) }
async function inviteUser(id) { const room = selectedId.value; await operation(async () => { const result = await postJson(`/api/chat/rooms/${room}/invite`, { user_id: id }); notice.value = result.message }) }
async function decideInvitation(accept) { const room = selectedId.value; await operation(async () => { await putJson(`/api/chat/rooms/${room}/invitation`, { accept }); notice.value = accept ? '邀请已接受。' : '邀请已拒绝。'; if (!accept) selectedId.value = 'public-lobby' }) }
async function leaveRoom() { if (!window.confirm('退出后不能再读取此会话，本版本不支持重新加入。确定退出？')) return; const room = selectedId.value; await operation(async () => { await deleteRequest(`/api/chat/rooms/${room}/membership`); drafts.delete(room); retries.delete(room); selectedId.value = 'public-lobby' }) }
async function blockUser(id) { if (!window.confirm('关闭双方私聊和新邀请？公共群消息不会隐藏，可在拉黑名单解除。')) return; await operation(async () => { const result = await putJson(`/api/chat/blocks/${id}`, {}); notice.value = result.message }) }
async function unblockUser(id) { await operation(async () => { await deleteRequest(`/api/chat/blocks/${id}`) }) }
async function retract(item) { if (!window.confirm('撤回后内容不可恢复，确定？')) return; const room = selectedId.value; await operation(async () => { await deleteRequest(`/api/chat/rooms/${room}/messages/${item.id}`); if (selectedId.value === room) messages.value = messages.value.map(row => row.id === item.id ? { ...row, content: '', is_deleted: true, can_retract: false } : row) }) }
async function send() {
  const room = selectedId.value, content = draft.value.trim()
  if (!canSend.value || !content) return
  let pending = retries.get(room)
  if (!pending || pending.content !== content) { pending = { content, client_id: crypto.randomUUID() }; retries.set(room, pending) }
  sending.value = true; notice.value = ''
  try {
    await postJson(`/api/chat/rooms/${room}/messages`, { content, client_id: pending.client_id })
    retries.delete(room); drafts.delete(room)
    if (!disposed && selectedId.value === room) { draft.value = ''; await syncMessages(true) }
  } catch (error) { if (!disposed && selectedId.value === room) notice.value = error.message + '（再次发送相同内容会沿用消息标识，避免重复。）' }
  finally { sending.value = false }
}
function visibility() {
  if (document.hidden) { clearTimeout(timer); controller?.abort(); listController?.abort() }
  else refreshAll()
}
onMounted(() => { refreshAll(); document.addEventListener('visibilitychange', visibility) })
onUnmounted(() => { disposed = true; revision++; clearTimeout(timer); controller?.abort(); listController?.abort(); drafts.clear(); retries.clear(); document.removeEventListener('visibilitychange', visibility) })
</script>
<style scoped>
.chat-messages,.chat-sidebar{scrollbar-width:thin;scrollbar-color:#59708e transparent}
.chat-history-bar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;padding:12px;background: var(--surface);border-radius:9px;color: var(--ink);font-size:12px}.chat-messages{scrollbar-gutter:stable}.chat-composer textarea:disabled{opacity:.7;cursor:not-allowed}
.chat-search>div>button{flex-shrink:0;white-space:nowrap}.chat-search>div>input{flex:1}
.chat-page{padding-top:44px}.chat-rules{padding:18px 22px;margin-bottom:22px;color: var(--muted);font-size:13px;line-height:1.85}.chat-rules summary{cursor:pointer;color: var(--ink)}.chat-layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:20px}.chat-sidebar{padding:22px;align-self:start}.chat-sidebar-heading,.conversation-heading{display:flex;align-items:center;justify-content:space-between;gap:14px}.chat-sidebar h2,.conversation-heading h2{font-size:22px;margin:0}.room-button{display:flex;align-items:center;gap:13px;width:100%;padding:15px 12px;margin-top:12px;text-align:left;background: var(--surface);color: var(--ink);border: 1px solid var(--border);border-radius:12px;cursor:pointer}.room-button.selected{background: var(--surface);border-color: var(--border)}.room-button strong,.room-button small{display:block;overflow-wrap:anywhere}.room-button small{font-size:12px;color: var(--muted);margin-top:6px}.room-symbol{font-size:24px;color: var(--blue)}.chat-search{display:grid;gap:12px;margin:26px 0;color: var(--ink);font-size:13px}.chat-search>div{display:flex;gap:8px}.chat-search input{min-width:0}.chat-person{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:14px 0;font-size:12px;overflow-wrap:anywhere}.chat-person>span:nth-child(2){flex:1}.chat-person button{padding:6px 10px;min-height:32px;font-size:12px}.chat-blocks{margin-top:24px;color: var(--muted);font-size:13px}.chat-blocks summary{cursor:pointer}.chat-conversation{padding:24px;min-height:640px;min-width:0}.conversation-heading{padding-bottom:20px;border-bottom: 1px solid var(--border);flex-wrap:wrap}.chat-tools{display:flex;gap:8px}.conversation-members{display:flex;flex-wrap:wrap;gap:10px;color: var(--muted);font-size:12px;padding:12px 0}.chat-messages{height:430px;overflow-y:auto;overscroll-behavior:contain;padding:18px 4px}.chat-message{display:flex;gap:12px;margin:18px 0}.chat-message>div{min-width:0;max-width:86%}.chat-message-meta{display:flex;align-items:center;flex-wrap:wrap;gap:10px;font-size:12px;color: var(--muted)}.chat-message-meta time{color: var(--blue);font-size:10px}.chat-message p{margin:8px 0 0;padding:12px 15px;background: var(--surface);border: 1px solid var(--border);border-radius:0 12px 12px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;font-size:14px}.chat-message.own p{background: var(--surface);border-color: var(--border)}.chat-message p.retracted{color: var(--muted);background: transparent;border-style:dashed;font-size:12px}.chat-retract{font-size:11px;padding:0;background: none;color: var(--muted);text-decoration:underline;cursor:pointer}.chat-sync{font-size:11px;color: var(--muted)}.chat-composer{margin-top:18px}.chat-composer textarea{min-height:95px}.chat-composer>div{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:12px;font-size:11px;color: var(--muted)}.chat-empty{padding:45px 12px;text-align:center;color: var(--muted);line-height:1.8}.chat-invitation{padding:42px 0;color: var(--muted);line-height:1.8}.chat-invitation button{margin:10px 10px 0 0}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}@media(max-width:900px){.chat-layout{grid-template-columns:1fr}.chat-messages{height:380px}.chat-sidebar{max-height:460px;overflow:auto}.chat-conversation{padding:18px}.chat-message>div{max-width:82%}.chat-composer>div{flex-wrap:wrap}}
</style>
