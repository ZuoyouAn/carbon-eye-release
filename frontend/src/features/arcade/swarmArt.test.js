import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ART_CELLS, spriteFrame, loadSwarmArt } from './swarmArt.js'

test('eight atlas cells are disjoint, bounded and reject unknown or malformed dimensions',()=>{
  const frames=Object.keys(ART_CELLS).map(id=>spriteFrame(1536,1024,id))
  assert.equal(new Set(frames.map(f=>`${f.x},${f.y}`)).size,8)
  for(const f of frames){assert.ok(f.x>=0&&f.y>=0);assert.ok(f.x+f.width<=1536&&f.y+f.height<=1024)}
  assert.equal(spriteFrame(0,1024,'ranger'),null);assert.equal(spriteFrame(NaN,1024,'mage'),null);assert.equal(spriteFrame(1536,1024,'bad'),null)
})
test('painted atlas is a bounded, alpha-enabled WebP rather than a runtime image service',()=>{
  const bytes=readFileSync(new URL('../../../public/game-art/starfall-units.webp',import.meta.url))
  assert.equal(bytes.subarray(0,4).toString(),'RIFF');assert.equal(bytes.subarray(8,12).toString(),'WEBP')
  assert.equal(bytes.subarray(12,16).toString(),'VP8X');assert.ok(bytes[20]&0x10,'alpha channel must be retained')
  assert.ok(bytes.length<800000,'one lazy image should remain under 800KB')
  const ground=readFileSync(new URL('../../../public/game-art/starfall-ground.webp',import.meta.url))
  assert.equal(ground.subarray(8,12).toString(),'WEBP');assert.ok(bytes.length+ground.length<1200000,'both lazy assets remain below 1.2MB')
})
class FakeImage { naturalWidth=1536; naturalHeight=1024; constructor(){FakeImage.last=this} }
test('view-owned artwork load succeeds, fails safely, and cannot fire after disposal',async()=>{
  const success=loadSwarmArt(FakeImage),image=FakeImage.last;image.onload();assert.equal(await success.ready,image)
  assert.equal(image.onload,null);assert.equal(image.onerror,null)
  const failure=loadSwarmArt(FakeImage);FakeImage.last.onerror();assert.equal(await failure.ready,null)
  const cancelled=loadSwarmArt(FakeImage),pending=FakeImage.last.onload;cancelled.dispose();pending();assert.equal(await cancelled.ready,null)
  assert.equal(FakeImage.last.onload,null)
})
