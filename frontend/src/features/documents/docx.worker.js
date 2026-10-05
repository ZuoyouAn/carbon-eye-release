import mammoth from 'mammoth/mammoth.browser.js'
import { unzipSync } from 'fflate'
import { zipPreflight } from './guards'
self.onmessage=async({data})=>{
  try{
    zipPreflight(data)
    const files=unzipSync(new Uint8Array(data));let actual=0
    for(const [name,content] of Object.entries(files)){actual+=content.length;if(actual>40*1024*1024)throw Error('解压尺寸过大。');if(name.endsWith('.xml')&&/<!DOCTYPE|<!ENTITY/i.test(new TextDecoder().decode(content)))throw Error('不支持带 DTD 或实体声明的文档。')}
    const result=await mammoth.convertToHtml({arrayBuffer:data},{externalFileAccess:false,includeEmbeddedStyleMap:false,ignoreEmptyParagraphs:false,convertImage:mammoth.images.imgElement(async image=>{
      if(!['image/png','image/jpeg','image/gif'].includes(image.contentType))return {alt:'不支持的图片格式已省略'}
      const value=await image.readAsBase64String();if(value.length>8*1024*1024)throw Error('文档中单张图片过大。');return {src:`data:${image.contentType};base64,${value}`}
    })})
    if(result.value.length>12*1024*1024)throw Error('转换后内容过大。')
    self.postMessage({html:result.value,warnings:result.messages.map(m=>m.message).slice(0,20)})
  }catch{self.postMessage({error:'无法解析此 DOCX：可能已损坏、加密、含不支持结构，或超出安全尺寸限制。'})}
}
