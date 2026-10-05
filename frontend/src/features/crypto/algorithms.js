// Transparent educational implementations. No network, storage, or production key use.
const bytes = text => [...new TextEncoder().encode(text)]
const hex = (n, size = 2) => (n >>> 0).toString(16).padStart(size, '0')
export const hexBytes = values => values.map(n => hex(n)).join('')
const stage = (title, note, values, extra = {}) => ({ title, note, values: values.map(String), ...extra })
const limited = (text, n = 256) => { if (typeof text !== 'string' || bytes(text).length > n) throw Error(`输入最多 ${n} 个 UTF-8 字节。`); return text }
const integer = (value, min, max) => { const n = Number(value); if (!Number.isSafeInteger(n) || n < min || n > max || String(value).trim() === '') throw Error(`请输入 ${min}–${max} 的整数。`); return n }
export function parseHex(text, count) { const v = String(text).replace(/\s/g, ''); if (!new RegExp(`^[0-9a-fA-F]{${count * 2}}$`).test(v)) throw Error(`需要 ${count * 2} 位十六进制字符（${count} 字节），不自动填充。`); return v.match(/../g).map(s => parseInt(s, 16)) }
export function caesar(text, shift = 3, reverse = false) {
  limited(text, 128); const k = integer(shift, 0, 25), steps = [], result = [...text].map((ch, i) => {
    const code = ch.charCodeAt(0), base = /^[A-Z]$/.test(ch) ? 65 : /^[a-z]$/.test(ch) ? 97 : null
    const out = base === null ? ch : String.fromCharCode(base + (code - base + (reverse ? -k : k) + 26) % 26)
    steps.push(stage(`字符 ${i + 1}`, base === null ? '非英文字母保持原样。' : `字母编号 ${code - base} ${reverse ? '−' : '+'} ${k}，对 26 取模。`, [ch, base === null ? '不参与移位' : code - base, k, out], { labels: ['输入', '编号', '偏移', '输出'], phase: 1 })); return out
  }).join('')
  return { steps, result }
}
export function vigenere(text, key = 'SPACE', reverse = false) {
  limited(text, 128); if (!/^[a-zA-Z]{1,32}$/.test(key)) throw Error('维吉尼亚密钥需要 1–32 个英文字母。')
  let j = 0; const steps = [], result = [...text].map((ch, i) => {
    const base = /^[A-Z]$/.test(ch) ? 65 : /^[a-z]$/.test(ch) ? 97 : null, letter = key[j % key.length].toUpperCase(), k = letter.charCodeAt(0) - 65
    const out = base === null ? ch : String.fromCharCode(base + (ch.charCodeAt(0) - base + (reverse ? -k : k) + 26) % 26)
    steps.push(stage(`字符 ${i + 1}`, base === null ? '非英文字母不推进密钥。' : `密钥字母 ${letter} 对应偏移 ${k}；逐字母计算后对 26 取模。`, [ch, letter, k, out], { labels: ['输入', '循环密钥', '偏移', '输出'], phase: 1 })); if (base !== null) j++; return out
  }).join('')
  return { steps, result }
}
export function xorTrace(text, key = 'Space') {
  const input = bytes(limited(text, 128)), secret = bytes(limited(key, 32)); if (!secret.length) throw Error('异或密钥不能为空。')
  const out = input.map((n, i) => n ^ secret[i % secret.length])
  return { steps: input.map((n, i) => stage(`UTF-8 字节 ${i + 1}`, '相同位为 0，不同位为 1。对结果再异或同一个密钥字节即可恢复原字节。重复短密钥不安全。', [n.toString(2).padStart(8, '0'), secret[i % secret.length].toString(2).padStart(8, '0'), out[i].toString(2).padStart(8, '0')], { labels: ['明文字节', '密钥字节', '密文字节'], phase: 1 })), result: hexBytes(out) }
}
const K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
const rotr = (n, r) => (n >>> r) | (n << (32 - r))
export function sha256Trace(text) {
  const input = bytes(limited(text)), padded = [...input, 128]; while (padded.length % 64 !== 56) padded.push(0)
  padded.push(0, 0, 0, 0, ...[24,16,8,0].map(n => (input.length * 8 >>> n) & 255))
  const H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
  const steps = [stage('编码与填充', `UTF-8 ${input.length} 字节，追加 80、零字节及 64 位大端长度；共 ${padded.length / 64} 块。`, padded.map(n => hex(n)), { phase: 0 })]
  for (let block = 0; block < padded.length / 64; block++) {
    const W = []; for (let i = 0; i < 16; i++) W[i] = padded.slice(block * 64 + i * 4, block * 64 + i * 4 + 4).reduce((a, b) => (a << 8) | b, 0) >>> 0
    for (let i = 16; i < 64; i++) { const x = W[i - 15], y = W[i - 2]; W[i] = (W[i - 16] + (rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3)) + W[i - 7] + (rotr(y, 17) ^ rotr(y, 19) ^ (y >>> 10))) >>> 0 }
    steps.push(stage(`块 ${block + 1} · 消息扩展`, '16 个原始 32 位字扩展为 W[0..63]。所有加法对 2³² 取模。', W.map(n => hex(n, 8)), { phase: 1 }))
    let [a,b,c,d,e,f,g,h] = H
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (rotr(e,6) ^ rotr(e,11) ^ rotr(e,25)) + ((e & f) ^ (~e & g)) + K[i] + W[i]) >>> 0
      const t2 = ((rotr(a,2) ^ rotr(a,13) ^ rotr(a,22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0
      ;[a,b,c,d,e,f,g,h] = [(t1 + t2) >>> 0,a,b,c,(d + t1) >>> 0,e,f,g]
      steps.push(stage(`块 ${block + 1} · 压缩轮 ${i + 1} / 64`, 'T1 = h + Σ₁(e) + Ch(e,f,g) + K[t] + W[t]；T2 = Σ₀(a) + Maj(a,b,c)。显示本轮更新后的八个寄存器。', [a,b,c,d,e,f,g,h].map(n => hex(n,8)), { labels: ['a','b','c','d','e','f','g','h'], details: [`W[${i}] = ${hex(W[i],8)}`, `K[${i}] = ${hex(K[i],8)}`, `T1 = ${hex(t1,8)}`, `T2 = ${hex(t2,8)}`], phase: 2 }))
    }
    ;[a,b,c,d,e,f,g,h].forEach((v, i) => { H[i] = (H[i] + v) >>> 0 })
    steps.push(stage(`块 ${block + 1} · 链值累加`, '本块的寄存器与原链值相加，传给下一块；最后拼接为 256 位摘要。散列不是可逆加密。', H.map(n => hex(n,8)), { phase: 3 }))
  }
  return { steps, result: H.map(n => hex(n,8)).join('') }
}
const mul = (a, b) => { let n = 0; for (let i = 0; i < 8; i++) { if (b & 1) n ^= a; a = ((a << 1) ^ (a & 128 ? 0x11b : 0)) & 255; b >>>= 1 } return n }
const powGF = (a, n) => { let v = 1; while (n) { if (n & 1) v = mul(v, a); a = mul(a,a); n >>>= 1 } return v }
const rot8 = (a, n) => ((a << n) | (a >>> (8 - n))) & 255
const S = Array.from({ length:256 }, (_, n) => { const v = n ? powGF(n,254) : 0; return v ^ rot8(v,1) ^ rot8(v,2) ^ rot8(v,3) ^ rot8(v,4) ^ 0x63 })
export function aes128Trace(inputHex, keyHex) {
  let state = parseHex(inputHex,16); const key = parseHex(keyHex,16), expanded = [...key], steps = []
  let rcon = 1
  while (expanded.length < 176) { let t = expanded.slice(-4); if (expanded.length % 16 === 0) { t = [S[t[1]] ^ rcon,S[t[2]],S[t[3]],S[t[0]]]; rcon = mul(rcon,2) } for (let i = 0; i < 4; i++) expanded.push(expanded[expanded.length - 16] ^ t[i]) }
  const matrix = values => Array.from({ length:16 }, (_, i) => hex(values[(i % 4) * 4 + Math.floor(i / 4)]))
  const record = (title,note,phase,round) => steps.push(stage(title,note,matrix(state), { matrix:true, phase, round, details:[`轮密钥 ${round}：${hexBytes(expanded.slice(round * 16, round * 16 + 16))}`] }))
  record('输入状态矩阵','16 字节按列填入 4×4 矩阵。下面按行显示，每格一个字节。',0,0)
  const addKey = round => { state = state.map((v,i) => v ^ expanded[round * 16 + i]); record(`轮 ${round} · AddRoundKey`,'状态逐字节异或本轮密钥。密钥扩展生成 11 组轮密钥。',4,round) }
  addKey(0)
  for (let round = 1; round <= 10; round++) {
    state = state.map(n => S[n]); record(`轮 ${round} · SubBytes`,'逐字节 S-box 非线性替换：GF(2⁸) 乘法逆元加仿射变换。',1,round)
    const before = [...state]; for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) state[c * 4 + r] = before[((c + r) % 4) * 4 + r]
    record(`轮 ${round} · ShiftRows`,'第 0–3 行分别向左循环移位 0–3 格。',2,round)
    if (round !== 10) { const next = []; for (let c = 0; c < 4; c++) { const a = state.slice(c * 4,c * 4 + 4); next.push(mul(a[0],2)^mul(a[1],3)^a[2]^a[3],a[0]^mul(a[1],2)^mul(a[2],3)^a[3],a[0]^a[1]^mul(a[2],2)^mul(a[3],3),mul(a[0],3)^a[1]^a[2]^mul(a[3],2)) } state = next; record(`轮 ${round} · MixColumns`,'每列乘固定矩阵 [02 03 01 01; 01 02 03 01; 01 01 02 03; 03 01 01 02]，使用 GF(2⁸) 运算。第 10 轮省略此步。',3,round) }
    addKey(round)
  }
  return { steps, result: hexBytes(state) }
}
export function prime(n) { if (!Number.isInteger(n) || n < 2) return false; for (let d = 2; d * d <= n; d++) if (n % d === 0) return false; return true }
export function modPow(base, exponent, modulus, steps = [], label = '模幂') {
  let a = BigInt(base), b = BigInt(exponent), n = BigInt(modulus), v = 1n; if (b < 0n || n < 2n || b > 1000000n) throw Error('模幂参数超出演示范围。'); a %= n
  while (b) { const bit = Number(b & 1n); if (bit) v = v * a % n; steps.push(stage(`${label} · 位 ${steps.length + 1}`, `指数最低位为 ${bit}；${bit ? '累积值乘当前底数后取模；' : '累积值保持；'}底数平方、指数右移。`, [b,a,v,n], { labels: ['剩余指数','当前底数','累积结果','模数'], phase:2 })); a = a * a % n; b >>= 1n } return Number(v)
}
export function rsaTrace(pInput,qInput,eInput,mInput) {
  const p = integer(pInput,3,997), q = integer(qInput,3,997), e = integer(eInput,3,999983); if (!prime(p) || !prime(q) || p === q) throw Error('p、q 需要是两个不同的 3–997 素数。')
  const n = p * q, phi = (p - 1) * (q - 1), m = integer(mInput,0,n - 1); if (e >= phi) throw Error('e 必须小于 φ(n)。')
  let [oldR,r,oldT,t] = [phi,e,0,1]; const steps = [stage('计算公钥参数','n = p×q；φ(n) = (p−1)(q−1)。公钥是 (n,e)，p、q 和 d 应保密。此处小整数及裸 RSA 仅作教学。',[p,q,n,phi,e],{labels:['p','q','n','φ(n)','e'],phase:0})]
  while (r) { const quotient = Math.floor(oldR / r); [oldR,r] = [r,oldR - quotient * r]; [oldT,t] = [t,oldT - quotient * t]; steps.push(stage('扩展欧几里得','寻找 e 的模 φ(n) 逆元 d。余数最终为 1 才存在逆元。',[oldR,r,oldT,t],{labels:['旧余数','新余数','旧系数','新系数'],phase:1})) }
  if (oldR !== 1) throw Error('e 与 φ(n) 必须互素。'); const d = ((oldT % phi) + phi) % phi
  steps.push(stage('私钥指数','d = e⁻¹ mod φ(n)，满足 e×d mod φ(n) = 1。',[e,d,phi,e*d%phi],{labels:['e','d','φ(n)','校验'],phase:1}))
  const encrypted = modPow(m,e,n,steps,'加密 mᵉ mod n'), decrypted = modPow(encrypted,d,n,steps,'解密 cᵈ mod n')
  steps.push(stage('恢复输入','加密与解密是两次模幂。实际 RSA 加密需要合适的密钥长度和 OAEP 等编码，本页未实现，不能保护真实秘密。',[m,encrypted,decrypted],{labels:['输入整数','密文整数','恢复整数'],phase:3}))
  return {steps,result:`密文 ${encrypted}；恢复 ${decrypted}；n=${n}，d=${d}`}
}
export function dhTrace(pInput,gInput,aInput,bInput) {
  const p = integer(pInput,5,997); if (!prime(p)) throw Error('p 需要是 5–997 的素数。'); const g = integer(gInput,2,p - 2), a = integer(aInput,1,p - 2), b = integer(bInput,1,p - 2), steps = [stage('公共参数与双方秘密','p、g 公开；a、b 分别属于双方。这里是小整数代数教学，未验证安全子群，也没有身份认证。',[p,g,a,b],{labels:['公开 p','公开 g','Alice 私有 a','Bob 私有 b'],phase:0})]
  const A = modPow(g,a,p,steps,'Alice 公钥'), B = modPow(g,b,p,steps,'Bob 公钥')
  steps.push(stage('只交换公钥','A = gᵃ mod p；B = gᵇ mod p。交换 A、B，不交换 a、b。',[A,B],{labels:['Alice → Bob','Bob → Alice'],phase:1}))
  const ka = modPow(B,a,p,steps,'Alice 共享值'), kb = modPow(A,b,p,steps,'Bob 共享值')
  steps.push(stage('共享值一致','Bᵃ mod p = Aᵇ mod p。实际协议还需验证参数、身份认证和 KDF；不能直接把本页数值作为密钥。',[ka,kb],{labels:['Alice 的共享值','Bob 的共享值'],phase:3}))
  return { steps, result:`Alice = ${ka}；Bob = ${kb}` }
}
