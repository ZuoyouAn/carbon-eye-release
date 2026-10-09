// Original generated painted units + code-native environment. No runtime AI calls.
import { spriteFrame } from './swarmArt.js'
const TAU = Math.PI * 2
const palette = { ranger: '#328eaa', guardian: '#b98543', mage: '#8870b0' }
function ellipse(c, x, y, rx, ry, fill, stroke) {
  c.beginPath(); c.ellipse(x, y, Math.max(.1, rx), Math.max(.1, ry), 0, 0, TAU)
  if (fill) { c.fillStyle = fill; c.fill() }
  if (stroke) { c.strokeStyle = stroke; c.stroke() }
}
function line(c, x, y, tx, ty, color, width = 2) {
  c.beginPath(); c.moveTo(x, y); c.lineTo(tx, ty); c.strokeStyle = color; c.lineWidth = width; c.stroke()
}
function polygon(c, points, fill, stroke) {
  c.beginPath(); points.forEach(([x,y], i) => i ? c.lineTo(x,y) : c.moveTo(x,y)); c.closePath()
  c.fillStyle = fill; c.fill(); if (stroke) { c.strokeStyle = stroke; c.stroke() }
}
function sprite(c, image, id, x, groundY, height, facing, motion = 0, attack = 0) {
  const frame = image && spriteFrame(image.naturalWidth, image.naturalHeight, id)
  if (!frame) return false
  c.save();c.translate(x,groundY)
  // A small articulated body sway, mirrored direction and recoil preserve the painted silhouette.
  c.scale(Math.cos(facing)<0?-1:1,1);c.rotate(motion*.025-attack*.035)
  const width=height*frame.width/frame.height
  c.drawImage(image,frame.x,frame.y,frame.width,frame.height,-width/2,-height-Math.abs(motion)*2,width,height)
  c.restore();return true
}
function hero(c, s, reduced, image) {
  const p = s.player, a = s.animation, color = palette[s.profession]
  const walk = reduced || !a.moving ? 0 : Math.sin(a.stride), bob = Math.abs(walk) * 1.8
  ellipse(c, p.x, p.y + 19, 22, 8, '#304e6826')
  if (p.invulnerable > 0) { c.lineWidth = 2; ellipse(c, p.x, p.y, 29, 34, '#bce8f333', '#78b9c6') }
  if (a.hurt > 0) { c.lineWidth = 3; ellipse(c, p.x, p.y, 31, 36, null, '#c57263') }
  if (sprite(c,image,s.profession,p.x,p.y+30,124,p.facing,walk,reduced?0:a.attack/.24)) {
    if(s.branch){c.lineWidth=1.5;ellipse(c,p.x,p.y+18,26,9,null,color);for(let i=0;i<4;i++){const t=(reduced?0:s.elapsed*.7)+i*TAU/4;ellipse(c,p.x+Math.cos(t)*27,p.y+18+Math.sin(t)*9,2,2,'#e0ba68')}}
    return
  }
  c.save(); c.translate(p.x, p.y - bob)
  // Feet, coat and face stay upright; arms and weapons follow the aim independently.
  line(c, -7, 7, -8, 22 + walk * 5, '#354a60', 7)
  line(c, 7, 7, 8, 22 - walk * 5, '#354a60', 7)
  polygon(c, [[-13,-9],[-19,16 + walk * 2],[0,12],[17,16 - walk * 2],[12,-9]], s.profession === 'mage' ? '#c5b6de' : '#b7d4d1')
  ellipse(c, 0, 0, 14, 18, color, '#ffffffb0')
  line(c, -10, 7, 10, 7, '#e6cea0', 4)
  ellipse(c, 0, -18, 10, 11, '#efd2b1', '#f9eee0')
  if (s.profession === 'mage') polygon(c, [[-15,-23],[0,-44],[15,-23]], color, '#ede3f4')
  else if (s.profession === 'guardian') {
    ellipse(c, 0, -23, 12, 8, '#adc0ca', '#e9f1f2'); line(c, 0,-31,0,-20,'#f2d09a',3)
    ellipse(c, -14,-5,7,9,'#c6d4d5','#fff'); ellipse(c,14,-5,7,9,'#c6d4d5','#fff')
  } else { ellipse(c, 0,-25,12,6,'#365b70'); polygon(c,[[6,-29],[19,-39],[16,-25]],'#9cc6c2') }
  line(c, -4,-17,-2,-17,'#425363',2); line(c,3,-17,5,-17,'#425363',2)
  c.save(); c.rotate(p.facing)
  const attack = reduced ? 0 : Math.sin(Math.min(1, a.attack / .24) * Math.PI)
  line(c, 6, 0, 22 - attack * 4, 0, '#edd1b0', 6)
  c.translate(-attack * 4, 0)
  if (s.profession === 'ranger') {
    line(c, 16, 0, 37, 0, '#466a7e', 5)
    line(c, 27,-13,31,0,'#acd4d5',4); line(c,31,0,27,13,'#acd4d5',4)
    line(c,27,-13,27,13,'#f6efd9',1); polygon(c,[[36,-3],[42,0],[36,3]],'#82c4d5')
  } else if (s.profession === 'guardian') {
    c.save(); c.rotate(-.7 + attack * 2)
    line(c,16,0,43,0,'#e5be79',5); polygon(c,[[30,-6],[50,-3],[54,0],[50,3],[30,6]],'#e7edf0','#9cb0b7'); c.restore()
    polygon(c,[[-4,-13],[8,-22],[18,-17],[17,-4],[5,3]],'#adc9d1','#f7f9ed')
    line(c,8,-18,8,-5,'#f1d1a0',3)
  } else {
    line(c,16,0,38,0,'#796399',5)
    ellipse(c,39,0,9,9,'#c8b1e5','#f8f0ff'); ellipse(c,39,0,4,4,'#f5ebff')
    if (!reduced) for(let i=0;i<3;i++){ const t=s.elapsed*2+i*TAU/3; ellipse(c,39+Math.cos(t)*14,Math.sin(t)*14,2,2,'#aa92ce') }
  }
  c.restore(); c.restore()
}
function creature(c, en, s, reduced, image) {
  const r = en.radius, boss = en.type === 'boss', tank = en.type === 'tank', runner = en.type === 'runner'
  const color = en.flash > 0 ? '#d2bd98' : boss ? '#ad776c' : tank ? '#8e92a8' : runner ? '#be9973' : '#83a294'
  const angle = Math.atan2(s.player.y - en.y, s.player.x - en.x)
  const gait = reduced || en.charge ? 0 : Math.sin(s.elapsed * (runner ? 15 : 9) + en.id) * 4
  ellipse(c,en.x,en.y+r*.65,r*1.1,r*.42,'#4b5f6b24')
  const painted = sprite(c,image,en.type,en.x,en.y+r*.6,boss?158:tank?87:runner?75:66,angle,gait/4,en.flash>0&&!reduced?.8:0)
  if(!painted){
  c.save(); c.translate(en.x,en.y); c.rotate(angle)
  if (en.flash > 0 && !reduced) c.scale(1.08,.94)
  for(let side=-1;side<=1;side+=2) for(let i=0;i<3;i++) {
    const x=(i-1)*r*.65, offset=gait*(i%2 ? -1 : 1)
    line(c,x,side*r*.5,x+offset-r*.25,side*r*1.3,color,boss?7:tank?5:3)
    line(c,x+offset-r*.25,side*r*1.3,x+offset+r*.1,side*r*1.35,'#516773',2)
  }
  ellipse(c,0,0,r,runner?r*.65:r*.88,color,'#ffffff80')
  if(tank || boss) {
    for(let i=-1;i<=1;i++) polygon(c,[[i*r*.5-r*.25,-r*.4],[i*r*.5,-r*.75],[i*r*.5+r*.25,-r*.4],[i*r*.5,r*.25]],boss?'#825c5b':'#737e96','#c6c8ca')
  } else line(c,-r*.7,0,r*.2,0,'#c5d2b1',3)
  if (runner || boss) {
    polygon(c,[[r*.5,-r*.55],[r*1.4,-r*.8],[r*.8,-r*.18]],'#e4d4b1')
    polygon(c,[[r*.5,r*.55],[r*1.4,r*.8],[r*.8,r*.18]],'#e4d4b1')
  }
  ellipse(c,r*.65,-r*.3,boss?4:2.5,boss?4:2.5,'#f9dda0')
  ellipse(c,r*.65,r*.3,boss?4:2.5,boss?4:2.5,'#f9dda0')
  c.restore()
  }
  if(en.slow>0){c.lineWidth=2;ellipse(c,en.x,en.y,r+5,r+5,null,'#75b6d2')}
  if(en.hp<en.maxHp || boss) {
    c.fillStyle='#d3d7d1';c.fillRect(en.x-r,en.y-r-14,r*2,4)
    c.fillStyle=boss?'#b57569':'#748b8e';c.fillRect(en.x-r,en.y-r-14,r*2*Math.max(0,en.hp/en.maxHp),4)
  }
}
function visual(c, e, reduced, foreground) {
  const t = Math.max(0, Math.min(1, 1-e.life/e.maxLife)), alpha = 1-t
  const above = ['damage','impact','burst','line','pickup'].includes(e.kind)
  if(above!==foreground || (reduced && ['trail','pickup','impact','burst'].includes(e.kind))) return
  c.save(); c.globalAlpha=alpha; c.lineWidth=2; c.lineCap='round'
  if(e.kind==='damage') {
    c.font='600 21px system-ui';c.textAlign='center';c.lineWidth=3;c.strokeStyle='#f6f8f3';c.fillStyle=e.color
    const y=e.y-(reduced?0:t*32);c.strokeText(String(e.radius),e.x,y);c.fillText(String(e.radius),e.x,y)
  } else if(e.kind==='line') {
    const dx=e.tx-e.x,dy=e.ty-e.y
    c.beginPath();c.moveTo(e.x,e.y)
    for(let i=1;i<5;i++){const jitter=reduced?0:(i%2?7:-7);c.lineTo(e.x+dx*i/5-dy/Math.max(1,Math.hypot(dx,dy))*jitter,e.y+dy*i/5+dx/Math.max(1,Math.hypot(dx,dy))*jitter)}
    c.lineTo(e.tx,e.ty);c.strokeStyle=e.color;c.lineWidth=3;c.stroke()
  } else if(e.kind==='impact'||e.kind==='burst') {
    const count=e.kind==='burst'?9:5
    for(let i=0;i<count;i++){const a=i*TAU/count+e.x*.013,r=e.radius*(.4+t*1.5);line(c,e.x+Math.cos(a)*r,e.y+Math.sin(a)*r,e.x+Math.cos(a)*(r+6*(1-t)),e.y+Math.sin(a)*(r+6*(1-t)),e.color,3)}
  } else if(e.kind==='slash') {
    c.translate(e.x,e.y);c.rotate(e.tx+t*TAU)
    c.beginPath();c.arc(0,0,e.radius*(.8+.2*t),-.7,2.8);c.strokeStyle=e.color;c.lineWidth=10*(1-t)+2;c.stroke()
    c.beginPath();c.arc(0,0,e.radius*.75,-.3,2);c.strokeStyle='#f6e8c7';c.lineWidth=2;c.stroke()
  } else if(e.kind==='trail') {
    c.translate(e.x,e.y);c.rotate(e.tx);ellipse(c,0,0,15,20,'#88bbcb55',e.color)
  } else {
    const radius=e.radius*(reduced?1:.25+t*.75)
    ellipse(c,e.x,e.y,radius,radius,null,e.color)
    if(e.kind==='nova'||e.kind==='level') {
      c.globalAlpha=alpha*.1;ellipse(c,e.x,e.y,radius,radius,e.color);c.globalAlpha=alpha
      if(!reduced) for(let i=0;i<8;i++){const a=i*TAU/8+t*.4;polygon(c,[[e.x+Math.cos(a)*radius,e.y+Math.sin(a)*radius],[e.x+Math.cos(a+.03)*(radius+8),e.y+Math.sin(a+.03)*(radius+8)],[e.x+Math.cos(a+.06)*radius,e.y+Math.sin(a+.06)*radius]],e.color)}
    }
  }
  c.restore()
}
export function paintSwarm(c,w,h,s,reduced=false,image=null,ground=null) {
  c.clearRect(0,0,w,h);c.fillStyle='#e5ece1';c.fillRect(0,0,w,h)
  const p=s.player,scale=Math.max(.48,Math.min(.95,w/830)),left=p.x-w/scale/2,top=p.y-h/scale/2
  const visible=(item,margin=170)=>item.x>=left-margin&&item.x<=left+w/scale+margin&&item.y>=top-margin&&item.y<=top+h/scale+margin
  c.save();c.translate(w/2,h/2);c.scale(scale,scale);c.translate(-p.x,-p.y);c.lineCap='round'
  if(ground){
    for(let x=Math.floor(left/640)*640;x<left+w/scale;x+=640)for(let y=Math.floor(top/640)*640;y<top+h/scale;y+=640)c.drawImage(ground,x,y,640,640)
    c.fillStyle='#f7f6e92a';c.fillRect(left,top,w/scale,h/scale)
  }else{
  // Open plaza and moss trails: decorative only, never invisible collision obstacles.
  c.fillStyle='#eee9dd';c.fillRect(-110,top,220,h/scale);c.fillRect(left,-95,w/scale,190)
  for(let x=Math.floor(left/96)*96;x<left+w/scale;x+=96)for(let y=Math.floor(top/72)*72;y<top+h/scale;y+=72){
    const seed=Math.sin(x*.21+y*.71),plaza=Math.abs(x)<160||Math.abs(y)<130
    if(plaza){c.fillStyle=seed>.4?'#e3dece':'#ebe6d8';c.fillRect(x+3,y+3,88,64);line(c,x+5,y+4,x+88,y+4,'#f9f5e9',1);line(c,x+91,y+8,x+91,y+64,'#d3d0c1',1)}
    else{ellipse(c,x+40,y+30,40,20,seed>.2?'#dbe6d3':'#e0e9d6');for(let i=0;i<2;i++){const px=x+15+i*28,py=y+25+Math.sin(i+seed)*16;line(c,px,py,px+3,py-5,'#adbea2',1);if(seed>.5)ellipse(c,px+3,py-5,2,2,'#f6ecb8')}}
  }
  }
  c.lineWidth=2;ellipse(c,0,0,180,135,'#eee8d65c','#c6c8b3');ellipse(c,0,0,153,114,null,'#d2cdb7');ellipse(c,0,0,55,42,null,'#bdc6b3')
  for(let i=0;i<12;i++){const a=i*TAU/12;line(c,Math.cos(a)*162,Math.sin(a)*121,Math.cos(a)*173,Math.sin(a)*129,'#b4bea9',2)}
  // Sparse deterministic landmarks; no unseen collision barriers or random render state.
  if(!ground)for(let x=Math.floor(left/240)*240;x<left+w/scale+240;x+=240) for(let y=Math.floor(top/240)*240;y<top+h/scale+240;y+=240) {
    const n=Math.abs(Math.sin(x*.17+y*.13)),dx=x+45+n*55,dy=y+70
    ellipse(c,dx+19,dy+14,29,9,'#62705d18')
    polygon(c,[[dx,dy],[dx+22,dy-4],[dx+32,dy+10],[dx+4,dy+17]],'#d8e0d9')
    polygon(c,[[dx,dy-6],[dx+22,dy-10],[dx+22,dy-4],[dx,dy]],'#eaf0e8')
    ellipse(c,x+172,y+163,20,9,'#dfe9dc');ellipse(c,x+183,y+157,13,8,'#d5e3d5')
    for(let i=0;i<4;i++)line(c,x+172+i*6,y+155,x+169+i*6,y+147-n*7,'#b8cfbf',1.5)
    if(n>.65){ellipse(c,x+210,y+49,15,5,'#6a78652a');polygon(c,[[x+198,y+45],[x+210,y+50],[x+222,y+45],[x+210,y+40]],'#c4cebc');c.fillStyle='#c2c9b9';c.fillRect(x+204,y+11,12,32);line(c,x+204,y+13,x+204,y+41,'#edf0df',3);ellipse(c,x+210,y+10,9,4,'#e6ebd9');ellipse(c,x+210,y+4,4,7,'#83c4ce','#e1f7ee')}
  }
  for(const en of s.enemies) if(en.charge>0&&visible(en,170)) {
    c.lineWidth=2;ellipse(c,en.x,en.y,150,150,'#cb7a691a','#be7161')
    c.beginPath();c.arc(en.x,en.y,150,-Math.PI/2,-Math.PI/2+TAU*(1-en.charge/1.1));c.strokeStyle='#b86153';c.lineWidth=5;c.stroke()
    c.fillStyle='#995b50';c.font='600 18px system-ui';c.textAlign='center';c.fillText('离开红圈',en.x,en.y-162)
  }
  for(const gem of s.gems) {
    if(!visible(gem,15))continue
    const bob=reduced?0:Math.sin(s.elapsed*3+gem.id)*2
    if(sprite(c,image,'crystal',gem.x,gem.y+10+bob,25,0))continue
    ellipse(c,gem.x,gem.y+8,7,3,'#699b9a20');c.save();c.translate(gem.x,gem.y+bob)
    polygon(c,[[0,-9],[6,-2],[0,8],[-6,-2]],gem.value>1?'#a58aca':'#54b2b2','#e1f5ed')
    polygon(c,[[0,-9],[0,8],[-6,-2]],gem.value>1?'#c5addc':'#86d0c5');c.restore()
  }
  for(const e of s.effects)if(visible(e,e.radius+40))visual(c,e,reduced,false)
  // Depth sorting keeps feet and silhouettes readable as enemies surround the hero.
  const actors=[...s.enemies.filter(en=>visible(en)).map(en=>({y:en.y,en})),{y:p.y,en:null}].sort((a,b)=>a.y-b.y)
  for(const actor of actors) actor.en?creature(c,actor.en,s,reduced,image):hero(c,s,reduced,image)
  for(const b of s.bullets) {
    if(!visible(b,30))continue
    const mage=s.profession==='mage',color=mage?'#a284d0':'#479fba'
    line(c,b.x-b.vx*.025,b.y-b.vy*.025,b.x,b.y,color,mage?6:3)
    ellipse(c,b.x,b.y,mage?10:4,mage?10:4,mage?'#bba1df77':'#7bcbd1')
    ellipse(c,b.x,b.y,mage?5:2,mage?5:2,'#fff6dc')
  }
  for(const e of s.effects)if(visible(e,e.radius+40))visual(c,e,reduced,true)
  c.restore()
  const boss=s.enemies.find(e=>e.type==='boss')
  if(boss) {
    c.fillStyle='#ffffffed';c.fillRect(w*.2,h-38,w*.6,23);c.fillStyle='#bd8071';c.fillRect(w*.2+3,h-35,(w*.6-6)*Math.max(0,boss.hp/boss.maxHp),6)
    c.fillStyle='#694e4b';c.font='14px system-ui';c.textAlign='center';c.fillText(boss.charge?'异兽蓄力 · 离开红圈':'巨型异兽 · 蓄力时停止移动',w/2,h-17)
  }
}
