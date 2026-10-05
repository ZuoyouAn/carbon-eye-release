export const MAX_FILE_BYTES = 10 * 1024 * 1024
export const MAX_PAGES = 12
export function fileKind(name) { const extension = String(name).match(/\.([^.]+)$/)?.[1]?.toLowerCase(); if (!['pdf','docx'].includes(extension)) throw Error('仅支持 .pdf 和 .docx；旧版 .doc、加密文件与宏文档不支持。'); return extension }
export function outputName(name, extension) { const stem = String(name).replace(/\.[^.]*$/,'').replace(/[\\/<>:"|?*\x00-\x1f]/g,'_').slice(0,100) || 'document'; return `${stem}-converted.${extension}` }
export function validateFile(file) { const kind = fileKind(file.name); if (!Number.isFinite(file.size) || file.size < 1 || file.size > MAX_FILE_BYTES) throw Error('单个文件需要在 1 字节至 10 MB 之间。'); return kind }
export function zipPreflight(buffer) {
  const data = new Uint8Array(buffer), v = new DataView(data.buffer,data.byteOffset,data.byteLength); let end = -1
  for (let i=data.length-22;i>=Math.max(0,data.length-65557);i--) if(v.getUint32(i,true)===0x06054b50){end=i;break}
  if(end<0)throw Error('不是有效 DOCX 压缩包。')
  const count=v.getUint16(end+10,true), offset=v.getUint32(end+16,true), centralSize=v.getUint32(end+12,true)
  if(v.getUint16(end+4,true)||v.getUint16(end+6,true)||count===65535||count>2048||offset+centralSize>end)throw Error('不支持多卷、ZIP64 或过多文件条目的文档。')
  let at=offset,total=0, hasDocument=false
  for(let i=0;i<count;i++){
    if(at+46>end||v.getUint32(at,true)!==0x02014b50)throw Error('DOCX 文件目录损坏。')
    const compressed=v.getUint32(at+20,true), expanded=v.getUint32(at+24,true), nameSize=v.getUint16(at+28,true), extra=v.getUint16(at+30,true), comment=v.getUint16(at+32,true)
    if(at+46+nameSize+extra+comment>end)throw Error('DOCX 条目越界。')
    const name=new TextDecoder().decode(data.slice(at+46,at+46+nameSize))
    if(v.getUint16(at+8,true)&1||name.startsWith('/')||name.includes('\\')||name.split('/').includes('..')||['__proto__','constructor','prototype'].includes(name))throw Error('拒绝加密或含异常路径的 DOCX。')
    total+=expanded;if(expanded>16*1024*1024||total>40*1024*1024||expanded>Math.max(65536,compressed*300))throw Error('DOCX 解压尺寸或压缩比超出本地处理限制。')
    if(name==='word/document.xml')hasDocument=true
    at+=46+nameSize+extra+comment
  }
  if(!hasDocument)throw Error('压缩包不包含 Word 正文。');return {count,total}
}
export function textLines(items) {
  // Approximate reading order for simple single-column documents; not a layout recovery engine.
  const rows=[]
  for(const item of items){if(typeof item.str!=='string'||!item.str.trim())continue;const y=item.transform?.[5]??0,x=item.transform?.[4]??0;let row=rows.find(r=>Math.abs(r.y-y)<3);if(!row){row={y,parts:[]};rows.push(row)}row.parts.push({x,text:item.str})}
  return rows.sort((a,b)=>b.y-a.y).map(row=>row.parts.sort((a,b)=>a.x-b.x).map(part=>part.text).join(' ').trim())
}
