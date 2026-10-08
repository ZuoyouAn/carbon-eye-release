import test from 'node:test'
import assert from 'node:assert/strict'
import { winterTile, pickWinterTile } from './canvas.js'
test('every isometric grid center round-trips on desktop, mobile and expanded aspect ratios',()=>{
  for(const [width,height] of [[850,600],[288,580],[350,580],[1400,900],[900,350]])for(let x=0;x<7;x++)for(let y=0;y<7;y++){
    const p=winterTile(width,height,x,y)
    const picked=pickWinterTile({width,height,x:p.x,y:p.y})
    // IEEE -0 and +0 denote the same grid coordinate, not different cells.
    assert.ok(picked.x===x&&picked.y===y)
    assert.ok(p.x>=0&&p.x<=width);assert.ok(p.y>=0&&p.y<=height)
  }
})
