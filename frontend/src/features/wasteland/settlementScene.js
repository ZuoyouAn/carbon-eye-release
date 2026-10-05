import * as THREE from 'three'
import { BUILDINGS,CAMP_ROCKS } from './settlement'
// Original geometry, no external models/textures; game rules remain in settlement.js.
export function createSettlementScene(container,state){
  const canvas=document.createElement('canvas'),context=canvas.getContext('webgl2',{antialias:true,powerPreference:'low-power'})
  if(!context)throw Error('当前设备未启用 WebGL2；可切换三十天剧情。')
  const renderer=new THREE.WebGLRenderer({canvas,context,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;container.appendChild(canvas)
  const scene=new THREE.Scene();scene.background=new THREE.Color('#e6eeea');const camera=new THREE.OrthographicCamera(-14,14,14,-14,.1,100),geometries=new Set(),materials=new Map(),models=new Map(),enemyModels=new Map(),beams=[],bursts=[]
  function material(color){if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.8}));return materials.get(color)}
  function mesh(geometry,color,x,y,z,parent=scene){geometries.add(geometry);const m=new THREE.Mesh(geometry,material(color));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
  const box=(w,h,d,color,x,y,z,parent)=>mesh(new THREE.BoxGeometry(w,h,d),color,x,y,z,parent)
  const cyl=(r,h,color,x,y,z,parent)=>mesh(new THREE.CylinderGeometry(r,r,h,12),color,x,y,z,parent)
  const group=()=>{const g=new THREE.Group();scene.add(g);return g}
  const sun=new THREE.DirectionalLight('#fff1d5',2.6);sun.position.set(-10,24,12);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-22,right:22,top:22,bottom:-22,far:65});sun.shadow.normalBias=.05;scene.add(sun,new THREE.HemisphereLight('#fff','#a5b7a3',2.5))
  box(31,.2,31,'#c5d4bd',0,-.12,0);box(5,.03,30,'#dce3d5',0,0,0);box(30,.03,5,'#dce3d5',0,0,0)
  const grid=new THREE.GridHelper(28,14,'#b2c6b5','#b9cdbd');grid.position.y=.02;scene.add(grid);geometries.add(grid.geometry)
  for(const [x,z] of [[-15,-15],[-15,8],[15,-13],[15,14],[-9,15],[7,15],[-15,-6]]){cyl(.18,1.7,'#987e64',x,.85,z);mesh(new THREE.IcosahedronGeometry(1.3,0),'#85a682',x,2.2,z)}
  CAMP_ROCKS.forEach((r,i)=>{box(2.4,1.2+i*.22,2.4,'#a4ada6',r.x,.6,r.z);box(1.7,.3,2,'#bcc6bd',r.x,1.35,r.z)})
  box(2.2,1.2,2.2,'#94afa6',0,.6,0);box(2.6,.18,2.6,'#f5efe3',0,1.4,0);cyl(.1,3.8,'#6c9291',0,2.2,0);const beacon=mesh(new THREE.OctahedronGeometry(.5),'#69d4d2',0,4.2,0)
  const lightRing=mesh(new THREE.RingGeometry(1.65,1.8,64),'#81c9c1',0,.04,0);lightRing.rotation.x=-Math.PI/2
  for(const [x,z] of [[-2,-2],[2,2]]){box(.7,.9,.7,'#bc9e6a',x,.45,z);box(.18,.94,.73,'#e8d0a7',x,.45,z)}
  const resourceModels=state.nodes.map(node=>{const g=group();g.position.set(node.x,0,node.z)
    if(node.kind==='wood'){cyl(.18,1.8,'#a18b70',0,.9,0,g);mesh(new THREE.IcosahedronGeometry(1.05),'#91ae86',0,2.2,0,g)}
    else if(node.kind==='scrap'){box(1.2,.65,.9,'#9da8ac',0,.35,0,g);box(.4,.4,.4,'#e7b576',.3,.8,0,g);box(.35,.4,.4,'#a8bdc4',-.4,.3,.5,g)}
    else if(node.kind==='food'){box(.7,.55,.7,'#b19c76',0,.28,0,g);for(const x of [-.2,.2])mesh(new THREE.SphereGeometry(.18,8,8),'#d7915d',x,.68,0,g)}
    else {cyl(.38,.95,'#73b6d1',0,.48,0,g);cyl(.32,.08,'#e4f8f8',0,1,0,g)}return g})
  const player=group();box(.55,.7,.4,'#427baf',0,.9,0,player);mesh(new THREE.SphereGeometry(.24,12,8),'#e9c5a1',0,1.5,0,player);cyl(.28,.13,'#eadbc3',0,1.7,0,player);box(.45,.5,.2,'#c1a071',0,1,-.32,player)
  const legs=[-.16,.16].map(x=>box(.19,.55,.22,'#3c637d',x,.3,0,player));box(.12,.2,.65,'#46616e',.34,1,.2,player)
  const ghost=box(1.75,.15,1.75,'#75c7a4',0,.11,0);ghost.material=new THREE.MeshBasicMaterial({color:'#75c7a4',transparent:true,opacity:.55});materials.set('ghost',ghost.material);ghost.visible=false
  const ground=new THREE.Plane(new THREE.Vector3(0,1,0),0),ray=new THREE.Raycaster(),pointer=new THREE.Vector2(),point=new THREE.Vector3();let width=1,height=1,disposed=false,zoom=13
  function buildingModel(b){const g=group();g.position.set(b.x,0,b.z)
    if(b.kind==='wall'){box(1.8,1.6,.65,'#bcab8c',0,.8,0,g);for(const x of [-.65,.65])box(.22,1.95,.9,'#dfceb0',x,.975,0,g)}
    else if(b.kind==='turret'){cyl(.6,.45,'#8ca1a1',0,.22,0,g);cyl(.18,.75,'#708b96',0,.82,0,g);const head=new THREE.Group();g.add(head);box(.9,.38,.65,'#698fab',0,1.27,0,head);box(.14,.14,1.3,'#54778a',0,1.3,.6,head);box(.14,.1,.1,'#8ae4dc',0,1.45,.25,head);g.userData.head=head}
    else if(b.kind==='generator'){box(1.4,.85,1.2,'#d9b66b',0,.45,0,g);box(.8,.18,.9,'#6b8993',0,.96,0,g);cyl(.12,1.3,'#8498a0',.5,.8,-.4,g)}
    else if(b.kind==='garden'){box(1.7,.18,1.7,'#af9270',0,.1,0,g);for(const x of [-.5,0,.5])for(const z of [-.4,.4])mesh(new THREE.ConeGeometry(.2,.4,6),'#74a06a',x,.38,z,g)}
    else{box(1.6,.25,1.5,'#90a3a9',0,.12,0,g);cyl(.46,1.25,'#7cb6d0',0,.82,0,g);cyl(.5,.1,'#e4f1f0',0,1.5,0,g);box(.15,.15,.8,'#7e969d',.5,.55,.2,g)}return g
  }
  function enemyModel(en){const g=group(),big=en.type==='brute',color=big?'#ad7867':en.type==='runner'?'#c19b6c':'#ad9191';g.scale.setScalar(big?1.45:.85);box(.8,.85,.65,color,0,.75,0,g);mesh(new THREE.IcosahedronGeometry(.38,0),'#a4a9a1',0,1.45,0,g);box(.48,.08,.08,'#e58e65',0,1.47,.32,g);for(const x of [-.26,.26])box(.22,.48,.3,'#7d8688',x,.23,0,g);return g}
  function resize(){if(disposed)return;width=Math.max(1,container.clientWidth);height=Math.max(1,container.clientHeight);renderer.setSize(width,height);const aspect=width/height;camera.left=-zoom*aspect;camera.right=zoom*aspect;camera.top=zoom;camera.bottom=-zoom;camera.updateProjectionMatrix();renderer.render(scene,camera)}const observer=new ResizeObserver(resize);observer.observe(container);resize()
  return {canvas,zoom(delta){zoom=Math.max(8,Math.min(22,zoom+delta))},world(clientX,clientY){const r=canvas.getBoundingClientRect();pointer.set((clientX-r.left)/r.width*2-1,-(clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);return ray.ray.intersectPlane(ground,point)?{x:point.x,z:point.z}:null},
    render(s,target,reduced=false){if(disposed)return;const aspect=width/height;camera.left=-zoom*aspect;camera.right=zoom*aspect;camera.top=zoom;camera.bottom=-zoom;camera.updateProjectionMatrix();const cx=s.player.x*.22,cz=s.player.z*.22;camera.position.set(cx+23,26,cz+23);camera.lookAt(cx,0,cz)
      scene.background.set(s.night?'#d9e2f0':'#e6eeea');sun.intensity=s.night?1.4:2.6;sun.color.set(s.night?'#d9e6ff':'#fff1d5');beacon.rotation.y=reduced?0:s.elapsed*.4
      player.position.set(s.player.x,0,s.player.z);player.rotation.y=s.player.facing;legs.forEach((leg,i)=>{leg.rotation.x=reduced||!s.player.moving?0:Math.sin(s.elapsed*12+i*Math.PI)*.22});player.visible=true
      resourceModels.forEach((g,i)=>{g.visible=s.nodes[i].remaining>0});ghost.visible=Boolean(target);if(target){ghost.position.set(target.x,.08,target.z);ghost.material.color.set(target.ok?'#62bd98':'#d77e75')}
      for(const b of s.buildings){let model=models.get(b.id);if(!model){model=buildingModel(b);models.set(b.id,model)}if(model.userData.head){const victim=s.enemies.filter(en=>Math.hypot(en.x-b.x,en.z-b.z)<7).sort((a,c)=>Math.hypot(a.x-b.x,a.z-b.z)-Math.hypot(c.x-b.x,c.z-b.z))[0];if(victim)model.userData.head.rotation.y=Math.atan2(victim.x-b.x,victim.z-b.z);model.userData.head.visible=true}}
      for(const [id,g] of models)if(!s.buildings.some(b=>b.id===id)){scene.remove(g);models.delete(id)}
      for(const en of s.enemies){let g=enemyModels.get(en.id);if(!g){g=enemyModel(en);enemyModels.set(en.id,g)}g.position.set(en.x,0,en.z);g.rotation.y=Math.atan2(-en.x,-en.z)}for(const [id,g] of enemyModels)if(!s.enemies.some(en=>en.id===id)){scene.remove(g);enemyModels.delete(id)}
      s.beams.slice(0,64).forEach((beam,i)=>{if(!beams[i]){const geometry=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);geometries.add(geometry);const m=new THREE.LineBasicMaterial({color:beam.color});materials.set(`beam${i}`,m);beams[i]=new THREE.Line(geometry,m);scene.add(beams[i])}const line=beams[i];line.visible=true;line.material.color.set(beam.color);line.geometry.setFromPoints([new THREE.Vector3(beam.x,1.3,beam.z),new THREE.Vector3(beam.tx,1,beam.tz)])});beams.forEach((line,i)=>{if(i>=s.beams.length)line.visible=false})
      s.particles.slice(0,24).forEach((p,i)=>{if(!bursts[i])bursts[i]=mesh(new THREE.IcosahedronGeometry(.4),'#e6c58c',0,.6,0);bursts[i].visible=!reduced;bursts[i].position.set(p.x,.5,p.z);bursts[i].scale.setScalar(p.life*2)});bursts.forEach((b,i)=>{if(i>=s.particles.length)b.visible=false});renderer.render(scene,camera)
    },dispose(){disposed=true;observer.disconnect();geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());grid.material.dispose();renderer.dispose();renderer.forceContextLoss();canvas.remove()}}
}
