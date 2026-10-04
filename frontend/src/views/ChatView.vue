<template>
  <main class="content-page chat-page">
    <section class="section-heading"><p class="eyebrow">SPACE / CONNECTIONS</p><h1>聊聊正在发生的事。</h1><p>公共大厅、小群与私聊。消息保留30天，连接彼此，也尊重彼此的边界。</p></section>
    <details class="chat-rules panel"><summary>聊天规则与隐私说明</summary><p>所有正常注册用户均可在大厅聊天。高权限及管理员可建小群，每群最多12人；被邀请人接受后才能读消息。私聊须双方接受，拒绝或退出后本版本不重复邀请。拉黑阻止双方私聊与新邀请，不隐藏公共群消息。</p><p>每条最多1000字，至少间隔3秒，每人每日最多200条；全站每日最多1000条。邀请操作每人每天5次。仅文字消息，不上传附件、不渲染HTML；禁言账号只能读。你可以撤回自己的消息，管理员只能治理公共大厅，不能绕过成员校验查看私聊。</p><p>消息通过HTTPS传输并存储在数据库，不是端到端加密。应用内管理员无权查看非成员私聊，但数据库运营者仍有技术访问能力，请勿发送密码或敏感隐私。超过30天的消息不可查看，并在之后发送消息时清理。仅页面可见时每12秒同步，非毫秒级即时通讯。</p></details>
    <p v-if="notice" class="message" role="status">{{ notice }}</p>
    <div class="chat-layout">
      <aside class="panel chat-sidebar"><div class="chat-sidebar-heading"><h2>我的会话</h2><button class="text-button" :disabled="busy" @click="refreshAll">刷新</button></div><p v-if="loading" role="status" class="panel-text">正在连接…免费服务首次唤醒可能稍慢。</p><button v-for="room in rooms" :key="room.id" class="room-button" :class="{ selected: room.id === selectedId }" @click="selectRoom(room.id)"><span class="room-symbol">{{ room.kind === 'direct' ? '↗' : '#' }}</span><span><strong>{{ room.name }}</strong><small>{{ room.status === 'invited' ? '邀请待处理' : room.kind === 'direct' ? (room.blocked ? '私聊已关闭' : '一对一私聊') : '群聊' }}</small></span></button>
        <form class="chat-search" @submit.prevent="searchUsers"><label for="chat-user-search">找一位朋友</label><div><input id="chat-user-search" v-model="query" maxlength="30" placeholder="输入至少2字用户名"><button class="text-button" :disabled="busy">查找</button></div></form><p v-if="searched && !users.length" class="panel-text">没有匹配的用户，或你们之间已关闭邀请。</p><div v-for="user in users" :key="user.id" class="chat-person"><UserAvatar :user="user" :size="32" /><span>{{ user.username }}</span><button class="text-button" :disabled="!canChat || busy" @click="startDirect(user.id)">私聊</button><button v-if="activeRoom?.kind === 'group' && activeRoom.owner_id === authState.user?.id" class="text-button" :disabled="!canChat || busy" @click="inviteUser(user.id)">邀请</button></div>
        <form v-if="canPublish" class="chat-search" @submit.prevent="createGroup"><label for="chat-group-name">创建小群</label><input id="chat-group-name" v-model="groupName" maxlength="40" placeholder="给小群起个名字"><button class="button button-secondary" :disabled="busy || !groupName.trim()">创建并进入</button></form><details class="chat-blocks"><summary>我的拉黑名单（{{ blocks.length }}）</summary><div v-for="user in blocks" :key="user.id" class="chat-person"><span>{{ user.username }}</span><button class="text-button" :disabled="busy" @click="unblockUser(user.id)">解除</button></div></details>
      </aside>
      <section class="panel chat-conversation"><template v-if="activeRoom"><header class="conversation-heading"><div><p class="panel-label">{{ activeRoom.kind === 'direct' ? 'PRIVATE / 1:1' : 'GROUP / SPACE' }}</p><h2>{{ activeRoom.name }}</h2></div><div class="chat-tools"><button v-if="activeRoom.kind === 'direct' && activeRoom.other_id" class="text-button" :disabled="busy" @click="blockUser(activeRoom.other_id)">拉黑</button><button v-if="activeRoom.kind !== 'public' && activeRoom.status === 'accepted'" class="text-button" :disabled="busy" @click="leaveRoom">退出会话</button></div></header><div v-if="activeRoom.status === 'invited'" class="chat-invitation"><h3>你收到了一个{{ activeRoom.kind === 'direct' ? '私聊' : '群聊' }}邀请。</h3><p>接受后才能查看该会话的消息，包括仍在保留期内的历史。你也可以拒绝。</p><button class="button button-primary" :disabled="!canChat || busy" @click="decideInvitation(true)">接受邀请</button><button class="button button-secondary" :disabled="!canChat || busy" @click="decideInvitation(false)">拒绝</button></div><template v-else><div class="conversation-members" v-if="members.length"><span v-for="user in members" :key="user.id">{{ user.username }}{{ user.status === 'invited' ? '（待接受）' : '' }}</span></div><div ref="messageArea" class="chat-messages" aria-label="聊天记录"><button v-if="hasMore" class="text-button" :disabled="historyLoading" @click="loadOlder">查看更早消息</button><p v-if="!messages.length" class="chat-empty">{{ historyLoading ? '正在读取消息…' : '还没有消息。可以从一句近况开始。' }}</p><article v-for="item in messages" :key="item.id" class="chat-message" :class="{ own: item.sender.id === authState.user?.id }"><UserAvatar :user="item.sender" :size="34" /><div><div class="chat-message-meta"><strong>{{ item.sender.username }}</strong><time>{{ formatTime(item.created_at) }}</time><button v-if="item.can_retract" class="human-link-button chat-retract" @click="retract(item)">撤回</button></div><p :class="{ retracted: item.is_deleted }">{{ item.is_deleted ? '消息已撤回' : item.content }}</p></div></article></div><p class="chat-sync" role="status">{{ syncError ? `同步暂停：${syncError}` : lastSync ? `最近同步 ${lastSync} · 可见时每12秒更新` : '准备同步' }}</p><form class="chat-composer" @submit.prevent="send"><label class="sr-only" for="chat-content">消息内容</label><textarea id="chat-content" v-model="draft" maxlength="1000" :disabled="!canChat || activeRoom.blocked || sending" placeholder="写下你想分享的近况… Ctrl / ⌘ + Enter 发送" @keydown.ctrl.enter.prevent="send" @keydown.meta.enter.prevent="send"></textarea><div><span>{{ draft.length }} / 1000 · {{ !canChat ? '账号当前只能阅读' : activeRoom.blocked ? '私聊已关闭' : '请勿发送密码或敏感信息' }}</span><button class="button button-primary" :disabled="!canChat || activeRoom.blocked || sending || !draft.trim()">{{ sending ? '发送中…' : '发送消息' }}</button></div></form></template></template><div v-else class="chat-empty"><h2>选择一个会话。</h2><p>可进入大厅，或查找用户名发起私聊。</p></div></section>
    </div>
  </main>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiRequest, postJson, putJson, deleteRequest } from '../api/client.js'
import { authState, canPublish } from '../stores/auth.js'
import UserAvatar from '../components/UserAvatar.vue'
const rooms = ref([]), selectedId = ref('public-lobby'), messages = ref([]), members = ref([]), blocks = ref([]), users = ref([]), query = ref(''), groupName = ref(''), draft = ref(''), notice = ref(''), syncError = ref(''), lastSync = ref(''), loading = ref(true), busy = ref(false), sending = ref(false), hasMore = ref(false), historyLoading = ref(false), searched = ref(false), messageArea = ref(null)
const activeRoom = computed(() => rooms.value.find(room => room.id === selectedId.value))
const canChat = computed(() => authState.user && !authState.user.is_muted && !authState.user.is_deleted && ['user', 'elevated', 'admin'].includes(authState.user.role))
let timer, controller, disposed = false, pendingSend = null, revision = 0
function formatTime(value) { return new Date(value).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }
async function scrollBottom() { await nextTick(); if (messageArea.value) messageArea.value.scrollTop = messageArea.value.scrollHeight }
function selectRoom(id) { selectedId.value = id }
watch(selectedId, () => { revision++; controller?.abort(); messages.value = []; members.value = []; draft.value = ''; pendingSend = null; lastSync.value = ''; hasMore.value = false; syncError.value = ''; syncMessages(true) })
async function refreshAll() {
  if (busy.value || disposed) return
  busy.value = true
  try {
    const [list, blocked] = await Promise.all([apiRequest('/api/chat/rooms'), apiRequest('/api/chat/blocks')])
    if (disposed) return
    rooms.value = list; blocks.value = blocked
    if (!activeRoom.value) selectedId.value = 'public-lobby'
    await syncMessages(!messages.value.length)
  } catch (error) { if (!disposed) notice.value = error.message }
  finally { busy.value = false; loading.value = false }
}
async function syncMessages(force = false) {
  const room = activeRoom.value
  if (!room || room.status === 'invited' || disposed || document.hidden) return
  controller?.abort(); const request = new AbortController(); controller = request
  const id = selectedId.value, token = revision
  historyLoading.value = true
  const bottom = !messageArea.value || messageArea.value.scrollHeight - messageArea.value.scrollTop - messageArea.value.clientHeight < 80
  try {
    const [history, people] = await Promise.all([apiRequest(`/api/chat/rooms/${id}/messages`, { signal: request.signal }), apiRequest(`/api/chat/rooms/${id}/members`, { signal: request.signal })])
    if (disposed || token !== revision || request !== controller) return
    // Refresh latest window to propagate retractions; preserve explicitly loaded older rows.
    const first = history.items[0]?.id
    const older = force || !first ? [] : messages.value.filter(item => item.id < first)
    messages.value = [...older, ...history.items].slice(-200); members.value = people
    if (!older.length) hasMore.value = history.has_more
    lastSync.value = new Date().toLocaleTimeString('zh-CN'); syncError.value = ''
    if (force || bottom) await scrollBottom()
  } catch (error) { if (!disposed && request === controller && !request.signal.aborted) syncError.value = error.message }
  finally { if (request === controller) historyLoading.value = false }
}
async function loadOlder() {
  if (historyLoading.value || !messages.value.length) return
  historyLoading.value = true
  const id = selectedId.value, token = revision
  try {
    const history = await apiRequest(`/api/chat/rooms/${id}/messages?before_id=${messages.value[0].id}`)
    if (id !== selectedId.value || token !== revision) return
    messages.value = [...history.items, ...messages.value]; hasMore.value = history.has_more
  } catch (error) { notice.value = error.message }
  finally { historyLoading.value = false }
}
async function operation(task) {
  if (busy.value) return
  busy.value = true; notice.value = ''
  try { await task() } catch (error) { notice.value = error.message }
  finally { busy.value = false; await refreshAll() }
}
async function searchUsers() {
  await operation(async () => { if (query.value.trim().length < 2) throw new Error('请输入至少2字用户名。'); users.value = await apiRequest(`/api/chat/users?q=${encodeURIComponent(query.value.trim())}`); searched.value = true })
}
async function startDirect(id) { await operation(async () => { const room = await postJson('/api/chat/direct', { user_id: id }); selectedId.value = room.id; notice.value = '会话已打开；对方接受邀请后，双方才能发送消息。' }) }
async function createGroup() { await operation(async () => { const room = await postJson('/api/chat/groups', { name: groupName.value, user_ids: [] }); selectedId.value = room.id; groupName.value = ''; notice.value = '小群已创建。查找用户后可以邀请加入。' }) }
async function inviteUser(id) { const room = selectedId.value; await operation(async () => { const result = await postJson(`/api/chat/rooms/${room}/invite`, { user_id: id }); notice.value = result.message }) }
async function decideInvitation(accept) { const room = selectedId.value; await operation(async () => { await putJson(`/api/chat/rooms/${room}/invitation`, { accept }); notice.value = accept ? '邀请已接受。' : '邀请已拒绝。'; if (!accept) selectedId.value = 'public-lobby' }) }
async function leaveRoom() { if (!window.confirm('退出后不能再读取此会话，本版本不支持重新加入。确定退出？')) return; const room = selectedId.value; await operation(async () => { await deleteRequest(`/api/chat/rooms/${room}/membership`); selectedId.value = 'public-lobby' }) }
async function blockUser(id) { if (!window.confirm('关闭双方私聊和新邀请？公共群消息不会隐藏，可在拉黑名单解除。')) return; await operation(async () => { const result = await putJson(`/api/chat/blocks/${id}`, {}); notice.value = result.message }) }
async function unblockUser(id) { await operation(async () => { await deleteRequest(`/api/chat/blocks/${id}`) }) }
async function retract(item) { if (!window.confirm('撤回后内容不可恢复，确定？')) return; const room = selectedId.value; await operation(async () => { await deleteRequest(`/api/chat/rooms/${room}/messages/${item.id}`) }) }
async function send() {
  const room = selectedId.value, content = draft.value.trim()
  if (!canChat.value || !content || sending.value || activeRoom.value?.blocked || activeRoom.value?.status !== 'accepted') return
  if (!pendingSend || pendingSend.content !== content || pendingSend.room !== room) pendingSend = { room, content, client_id: crypto.randomUUID() }
  sending.value = true; notice.value = ''
  try { await postJson(`/api/chat/rooms/${room}/messages`, { content, client_id: pendingSend.client_id }); if (selectedId.value === room) { draft.value = ''; pendingSend = null; await syncMessages(true) } }
  catch (error) { notice.value = error.message + '（再次发送相同内容会沿用消息标识，避免重复。）' }
  finally { sending.value = false }
}
function visibility() { if (document.hidden) controller?.abort(); else refreshAll() }
onMounted(() => { refreshAll(); timer = setInterval(() => { if (!document.hidden && !busy.value && !sending.value) refreshAll() }, 12000); document.addEventListener('visibilitychange', visibility) })
onUnmounted(() => { disposed = true; revision++; clearInterval(timer); controller?.abort(); document.removeEventListener('visibilitychange', visibility) })
</script>
<style scoped>
.chat-search>div>button{flex-shrink:0;white-space:nowrap}.chat-search>div>input{flex:1}
.chat-page{padding-top:44px}.chat-rules{padding:18px 22px;margin-bottom:22px;color:var(--muted);font-size:13px;line-height:1.85}.chat-rules summary{cursor:pointer;color:#c7daf4}.chat-layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:20px}.chat-sidebar{padding:22px;align-self:start}.chat-sidebar-heading,.conversation-heading{display:flex;align-items:center;justify-content:space-between;gap:14px}.chat-sidebar h2,.conversation-heading h2{font-size:22px;margin:0}.room-button{display:flex;align-items:center;gap:13px;width:100%;padding:15px 12px;margin-top:12px;text-align:left;background:#172436;color:#c8d7eb;border:1px solid var(--border);border-radius:12px;cursor:pointer}.room-button.selected{background:#273b54;border-color:#83cfe5}.room-button strong,.room-button small{display:block;overflow-wrap:anywhere}.room-button small{font-size:12px;color:#96adc6;margin-top:6px}.room-symbol{font-size:24px;color:#89d6d0}.chat-search{display:grid;gap:12px;margin:26px 0;color:#c6d9e9;font-size:13px}.chat-search>div{display:flex;gap:8px}.chat-search input{min-width:0}.chat-person{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:14px 0;font-size:12px;overflow-wrap:anywhere}.chat-person>span:nth-child(2){flex:1}.chat-person button{padding:6px 10px;min-height:32px;font-size:12px}.chat-blocks{margin-top:24px;color:#bacce1;font-size:13px}.chat-blocks summary{cursor:pointer}.chat-conversation{padding:24px;min-height:640px;min-width:0}.conversation-heading{padding-bottom:20px;border-bottom:1px solid var(--border);flex-wrap:wrap}.chat-tools{display:flex;gap:8px}.conversation-members{display:flex;flex-wrap:wrap;gap:10px;color:#8fa8c4;font-size:12px;padding:12px 0}.chat-messages{height:430px;overflow-y:auto;overscroll-behavior:contain;padding:18px 4px}.chat-message{display:flex;gap:12px;margin:18px 0}.chat-message>div{min-width:0;max-width:86%}.chat-message-meta{display:flex;align-items:center;flex-wrap:wrap;gap:10px;font-size:12px;color:#b7c9e0}.chat-message-meta time{color:#7e97b7;font-size:10px}.chat-message p{margin:8px 0 0;padding:12px 15px;background:#1d2e44;border:1px solid #304760;border-radius:0 12px 12px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;font-size:14px}.chat-message.own p{background:#193c40;border-color:#2b605f}.chat-message p.retracted{color:#8ea0b6;background:transparent;border-style:dashed;font-size:12px}.chat-retract{font-size:11px;padding:0;background:none;color:#a9bfd9;text-decoration:underline;cursor:pointer}.chat-sync{font-size:11px;color:#94aac2}.chat-composer{margin-top:18px}.chat-composer textarea{min-height:95px}.chat-composer>div{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:12px;font-size:11px;color:#97adc4}.chat-empty{padding:45px 12px;text-align:center;color:#8fa5be;line-height:1.8}.chat-invitation{padding:42px 0;color:#b4c7df;line-height:1.8}.chat-invitation button{margin:10px 10px 0 0}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}@media(max-width:900px){.chat-layout{grid-template-columns:1fr}.chat-messages{height:380px}.chat-sidebar{max-height:460px;overflow:auto}.chat-conversation{padding:18px}.chat-message>div{max-width:82%}.chat-composer>div{flex-wrap:wrap}}
</style>
