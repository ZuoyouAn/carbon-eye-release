'use strict';
const $ = id => document.getElementById(id);
// Embedded myATS pages receive the existing public API base, never auth tokens.
const configured = new URLSearchParams(location.search).get('api');
let apiBase = '';
if (configured) {
  const parsed = new URL(configured, location.origin);
  const trustedOrigins = new Set([location.origin, 'https://personal-website-carbon-eye-api.onrender.com']);
  const localDevelopment = ['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname) && ['127.0.0.1', 'localhost', '[::1]'].includes(parsed.hostname);
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password || (!trustedOrigins.has(parsed.origin) && !localDevelopment)) throw new Error('无效的 API 地址：只允许当前站点、已配置后端或本机开发地址');
  apiBase = parsed.href.replace(/\/$/, '');
}
const modes = {
  ip: { label: '公网 IP 地址', placeholder: '例如 1.1.1.1', hint: '查看公网地址的地区、网络组织和估计坐标。', privacy: '查询会把此 IP 发送给 ipwho.is。获取我的出口 IP 时，浏览器会直接访问 api.ipify.org。' },
  phone: { label: '电话号码', placeholder: '例如 +1 202 555 0123', hint: '带 + 国家码可跨地区解析；本地号码使用下方选择的地区。', privacy: '号码在运行后端的机器离线解析，不发送给外部号码查询服务。号码规则校验不确认开通状态。' },
  username: { label: '公开用户名', placeholder: '例如 octocat', hint: '在 19 个平台核对公开页面响应；查询可能需要约 20–30 秒。', privacy: '用户名会发送给所列公开平台。页面可访问不等于账号存在，也不能认定账号属于同一人。' },
};
let kind = 'ip', lastResult = null, busy = false;
function element(tag, text, cls) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; }
function resetResult() {
  lastResult = null; $('export').hidden = true; $('result-title').textContent = '等待一条线索';
  const box = element('div', undefined, 'empty'); box.append(element('span', '◎', 'orbit'), element('p', '结果会出现在这里。'), element('small', '先选择类型，再输入需要查询的内容。')); $('result').replaceChildren(box);
}
function setMode(next) {
  kind = next; $('value-label').textContent = modes[next].label; $('value').placeholder = modes[next].placeholder; $('value').value = ''; $('hint').textContent = modes[next].hint; $('privacy').textContent = modes[next].privacy;
  $('region-row').hidden = next !== 'phone'; $('my-ip').hidden = next !== 'ip'; $('error').hidden = true;
  document.querySelectorAll('[data-kind]').forEach(btn => btn.setAttribute('aria-pressed', String(btn.dataset.kind === next))); resetResult();
}
function setBusy(value) { busy = value; document.querySelectorAll('#query-form button,[data-kind],#clear').forEach(btn => { btn.disabled = value; }); document.querySelector('.result-panel').setAttribute('aria-busy', String(value)); $('submit').textContent = value ? '正在读取公开数据…' : '查询公开信息 ↗'; }
function fail(message) { $('error').textContent = message; $('error').hidden = false; }
async function fetchJson(url, options = {}, timeout = 30000) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal, cache: 'no-store', credentials: 'omit' });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '输入不符合要求或查询服务不可用。');
    return data;
  } catch (e) { if (e.name === 'AbortError') throw new Error('查询超时，请稍后重试。'); if (e instanceof TypeError) throw new Error('无法连接查询服务，请先启动后端并检查网络。'); throw e; }
  finally { clearTimeout(timer); }
}
const statusLabels = { reachable: '页面可访问 · 待人工核对', not_found: '服务器返回未找到', restricted: '受限 / 登录 / 频率限制', redirect: '页面跳转 · 待人工核对', network_error: '网络失败或超时', unknown: '无法判断' };
function format(value) { if (value === null || value === undefined || value === '') return '未提供'; if (typeof value === 'boolean') return value ? '是' : '否'; return Array.isArray(value) ? value.join(' / ') || '未提供' : String(value); }
function link(url, text) { const a = element('a', text); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; }
function renderResult(response) {
  lastResult = response; const d = response.data; const content = $('result'); content.replaceChildren(); $('result-title').textContent = { ip: 'IP 归属信息', phone: '号码规则解析', username: '公开页面线索' }[response.kind];
  const notes = { ip: '地图为网络地理估计，不是个人实时位置。', phone: '地区与运营商来自号段元数据；不包含机主或实时位置。', username: '状态只反映 HTTP 响应。同名、登录页与软 404 均可能造成误判。' };
  content.append(element('p', notes[response.kind], 'result-note'));
  if (response.kind === 'username') {
    content.append(element('p', `用户名：${d.username} · ${d.profiles.length} 个平台`, 'source'));
    const list = element('div', undefined, 'profiles');
    for (const item of d.profiles) { const card = element('article', undefined, 'profile'); card.append(link(item.url, `${item.name} ↗`), element('span', `${statusLabels[item.status]}${item.http_status ? ` · ${item.http_status}` : ''}`, `status ${item.status}`)); list.append(card); }
    content.append(list);
  } else {
    const rows = response.kind === 'ip' ? [['IP',d.ip],['地址类型',d.type],['国家 / 地区',d.country],['省 / 区域',d.region],['城市',d.city],['纬度',d.latitude],['经度',d.longitude],['ASN',d.connection?.asn],['网络组织',d.connection?.org],['ISP',d.connection?.isp],['域名',d.connection?.domain],['时区',d.timezone?.id]] : [['国际格式',d.international],['E.164',d.e164],['本地格式',d.national],['地区代码',d.region_code],['国家码',d.country_code],['号段所属地区',d.description],['原始运营商',d.carrier],['可能时区',d.timezones],['号码类型',d.type],['长度可能',d.possible],['规则有效',d.valid]];
    const dl = element('dl'); for (const [key,value] of rows) { const row = element('div'); row.append(element('dt',key),element('dd',format(value))); dl.append(row); } content.append(dl);
    if (d.maps_url) content.append(link(d.maps_url,'在地图查看估计区域 ↗'));
  }
  content.append(element('p', `来源：${response.source} · ${new Date(response.queried_at).toLocaleString()}`, 'source')); $('export').hidden = false;
  $('health').textContent = '查询服务已连接'; $('health').classList.remove('offline');
}
document.querySelectorAll('[data-kind]').forEach(btn => btn.addEventListener('click', () => { if (!busy) setMode(btn.dataset.kind); }));
$('query-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return; $('error').hidden = true; resetResult(); setBusy(true);
  try { renderResult(await fetchJson(`${apiBase}/api/ghosttrack/${kind}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value: $('value').value.trim(), region: $('region').value }) }, 60000)); }
  catch (e) { fail(e.message); } finally { setBusy(false); }
});
$('my-ip').addEventListener('click', async () => {
  if (busy) return; $('error').hidden = true; setBusy(true);
  try { const data = await fetchJson('https://api.ipify.org?format=json', {}, 10000); $('value').value = data.ip; }
  catch (e) { fail(e.message); } finally { setBusy(false); }
});
$('clear').addEventListener('click', () => { $('value').value = ''; $('error').hidden = true; resetResult(); });
$('export').addEventListener('click', () => {
  if (!lastResult) return; const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = element('a'); a.href = url; a.download = `ghosttrack-${lastResult.kind}-${Date.now()}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
setMode('ip');
async function checkHealth() {
  $('retry-health').disabled = true; $('health').textContent = '正在连接查询服务（免费后端首次唤醒可能较慢）…';
  try {
    const data = await fetchJson(`${apiBase}/api/ghosttrack/health`, {}, 60000);
    if (data.status !== 'ok') throw new Error('invalid health response');
    $('health').textContent = '查询服务已连接'; $('health').classList.remove('offline');
  } catch (error) {
    $('health').textContent = '服务暂未连接 · 可重试；本机使用请启动后端'; $('health').classList.add('offline');
  } finally { $('retry-health').disabled = false; }
}
$('retry-health').addEventListener('click', checkHealth);
checkHealth();
if (window.parent !== window) new ResizeObserver(() => window.parent.postMessage({ type: 'ghosttrack-height', height: Math.ceil(document.querySelector('main').getBoundingClientRect().height) + 8 }, location.origin)).observe(document.querySelector('main'));
