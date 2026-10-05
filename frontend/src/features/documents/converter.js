import DOMPurify from 'dompurify'
import { MAX_PAGES, textLines, zipPreflight } from './guards'
export function cleanDocumentHtml(html){
  const clean=DOMPurify.sanitize(html,{ALLOWED_TAGS:['p','br','h1','h2','h3','h4','strong','em','u','s','sup','sub','ul','ol','li','table','thead','tbody','tr','td','th','img'],ALLOWED_ATTR:['src','alt','colspan','rowspan'],ALLOW_DATA_ATTR:false})
  const root=document.createElement('div');root.innerHTML=clean
  root.querySelectorAll('img').forEach(img=>{if(!/^data:image\/(png|jpeg|gif);base64,[a-z0-9+/=]+$/i.test(img.getAttribute('src')||''))img.remove()})
  return root.innerHTML
}
export function openDocx(buffer,signal){
  zipPreflight(buffer)
  return new Promise((resolve,reject)=>{const worker=new Worker(new URL('./docx.worker.js',import.meta.url),{type:'module'});let done=false
    const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);worker.terminate();error?reject(error):resolve(value)}
    const abort=()=>finish(new DOMException('转换已取消。','AbortError')),timer=setTimeout(()=>finish(Error('解析超过 30 秒，请使用更小或更简单的文档。')),30000)
    if(signal?.aborted){abort();return}signal?.addEventListener('abort',abort,{once:true})
    worker.onmessage=event=>event.data.error?finish(Error(event.data.error)):finish(null,{html:cleanDocumentHtml(event.data.html),warnings:event.data.warnings})
    worker.onerror=()=>finish(Error('文档解析器未能启动，请刷新或重试。'));worker.postMessage(buffer,[buffer])
  })
}
const check=signal=>{if(signal?.aborted)throw new DOMException('转换已取消。','AbortError')}
export async function openPdf(buffer,mode,signal,progress){
  const pdfjs=await import('pdfjs-dist/build/pdf.mjs'),worker=await import('pdfjs-dist/build/pdf.worker.mjs?url');check(signal)
  pdfjs.GlobalWorkerOptions.workerSrc=worker.default
  const task=pdfjs.getDocument({data:new Uint8Array(buffer),useWasm:false,isEvalSupported:false,cMapUrl:'/document-assets/cmaps/',cMapPacked:true,standardFontDataUrl:'/document-assets/standard_fonts/'})
  const cancel=()=>task.destroy();signal?.addEventListener('abort',cancel,{once:true})
  try{const pdf=await task.promise;check(signal);if(pdf.numPages>MAX_PAGES)throw Error(`首版最多处理 ${MAX_PAGES} 页 PDF，请先拆分文件。`)
    const pages=[];for(let i=1;i<=pdf.numPages;i++){check(signal);progress(i,pdf.numPages);const page=await pdf.getPage(i),viewport=page.getViewport({scale:1}),text=await page.getTextContent();check(signal)
      if(!Number.isFinite(viewport.width)||!Number.isFinite(viewport.height)||viewport.width<72||viewport.height<72||viewport.width>1584||viewport.height>1584)throw Error('PDF 页面尺寸超出支持范围，请使用常规页面大小的副本。')
      let image='';if(mode==='appearance'){const scale=Math.min(1.5,Math.sqrt(3000000/(viewport.width*viewport.height))),view=page.getViewport({scale}),canvas=document.createElement('canvas');canvas.width=Math.ceil(view.width);canvas.height=Math.ceil(view.height);await page.render({canvasContext:canvas.getContext('2d'),viewport:view}).promise;check(signal);image=canvas.toDataURL('image/png');canvas.width=canvas.height=1}
      pages.push({width:viewport.width,height:viewport.height,lines:textLines(text.items),image});page.cleanup()
    }return {pages,emptyPages:pages.filter(page=>!page.lines.length).length}
  }catch(error){if(error.name==='PasswordException')throw Error('首版不支持密码保护的 PDF，请使用已解密的副本。');if(signal?.aborted)throw new DOMException('转换已取消。','AbortError');throw error}finally{signal?.removeEventListener('abort',cancel);await task.destroy()}
}
export async function pagesToWord(pages,mode,signal){
  check(signal);const {Document,Paragraph,TextRun,ImageRun,Packer}=await import('docx');check(signal)
  const sections=pages.map(page=>{const width=Math.round(page.width*20),height=Math.round(page.height*20),margin=360
    if(width<1440||height<1440||width>31680||height>31680)throw Error('PDF 页面尺寸超出 Word 支持范围。')
    const imageWidth=Math.min((width-margin*2)/15,((height-margin*2)/15-24)*page.width/page.height)
    const children=mode==='appearance'?[new Paragraph({alignment:'center',spacing:{before:0,after:0,line:240},children:[new ImageRun({type:'png',data:Uint8Array.from(atob(page.image.split(',')[1]),c=>c.charCodeAt(0)),transformation:{width:imageWidth,height:imageWidth*page.height/page.width}})]})]:page.lines.map(line=>new Paragraph({spacing:{after:120},children:[new TextRun({text:line,font:'Arial',size:24})]}))
    return {properties:{page:{size:{width,height},margin:{top:margin,right:margin,bottom:margin,left:margin}}},children:children.length?children:[new Paragraph('（此页未检测到可提取文字；未进行 OCR。）')]}
  });const blob=await Packer.toBlob(new Document({creator:'',lastModifiedBy:'',title:'',description:'',sections}));check(signal);return blob
}
export async function previewToPdf(element,signal,progress){
  const [{default:html2canvas},{jsPDF}]=await Promise.all([import('html2canvas'),import('jspdf')]);check(signal)
  // Raster PDF deliberately preserves Chinese glyphs without downloading/uploading fonts.
  const width=794,pageHeight=1123,padding=48,innerHeight=pageHeight-padding*2
  const host=document.createElement('div');host.className='document-render-host';host.style.cssText=`position:fixed;left:-10000px;top:0;width:${width}px;background:white;padding:${padding}px;box-sizing:border-box;color:#111;font-size:16px;line-height:1.7;font-family:Arial,"Microsoft YaHei",sans-serif;`;host.innerHTML=element.innerHTML;document.body.appendChild(host)
  try{host.querySelectorAll('img').forEach(img=>{img.style.maxWidth='100%';img.style.height='auto'});host.querySelectorAll('table').forEach(table=>{table.style.width='100%';table.style.borderCollapse='collapse'});host.querySelectorAll('td,th').forEach(cell=>{cell.style.border='1px solid #ccc';cell.style.padding='8px'})
    await Promise.all([...host.querySelectorAll('img')].map(img=>img.decode().catch(()=>{})));await document.fonts.ready;check(signal)
    // Slice rendered blocks at safe line/element boundaries; no single giant canvas.
    const contentHeight=host.scrollHeight-padding*2;if(contentHeight>innerHeight*MAX_PAGES)throw Error('重排后超过 12 页，暂不支持此大小。')
    const breaks=[0];let start=0;const base=host.getBoundingClientRect().top+padding
    const candidates=[...host.querySelectorAll('p,h1,h2,h3,h4,li,tr,img')].flatMap(node=>{const rect=node.getBoundingClientRect();return [rect.top-base,rect.bottom-base]}).filter(n=>n>0).sort((a,b)=>a-b)
    while(start+innerHeight<contentHeight){check(signal);const ideal=start+innerHeight;let cut=candidates.filter(n=>n>start+innerHeight*.65&&n<=ideal).pop()||ideal;if(cut<=start)cut=ideal;breaks.push(cut);start=cut}
    breaks.push(Math.max(contentHeight,1));if(breaks.length-1>MAX_PAGES)throw Error('分页后超过 12 页，暂不支持此大小。')
    const pdf=new jsPDF({unit:'px',format:[width,pageHeight],hotfixes:['px_scaling']})
    for(let i=0;i<breaks.length-1;i++){check(signal);progress(i+1,breaks.length-1);const height=Math.ceil(breaks[i+1]-breaks[i]);const canvas=await html2canvas(host,{backgroundColor:'#fff',scale:1.5,width,height,y:padding+breaks[i],useCORS:false,allowTaint:false,logging:false});check(signal);if(i)pdf.addPage([width,pageHeight]);pdf.addImage(canvas.toDataURL('image/png'),'PNG',0,padding,width,height);canvas.width=canvas.height=1}
    return pdf.output('blob')
  }finally{host.remove()}
}
