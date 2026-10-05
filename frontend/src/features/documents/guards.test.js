import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileKind,outputName,validateFile,zipPreflight,textLines } from './guards.js'
test('only supported files under resource limits are accepted',()=>{assert.equal(validateFile({name:'中.DOCX',size:42}),'docx');for(const f of [{name:'a.doc',size:1},{name:'a.docm',size:1},{name:'a.pdf',size:0},{name:'a.pdf',size:11*1024*1024}])assert.throws(()=>validateFile(f));assert.throws(()=>fileKind('pdf'))})
test('download names cannot contain path components',()=>{assert.equal(outputName('../test.pdf','docx'),'.._test-converted.docx');assert.equal(outputName('报告.docx','pdf'),'报告-converted.pdf')})
test('ZIP preflight accepts real Word fixture and rejects truncation/expanded size claims',()=>{const b=readFileSync('node_modules/mammoth/test/test-data/single-paragraph.docx');assert.ok(zipPreflight(b).count>1);assert.throws(()=>zipPreflight(b.slice(0,100)));const malicious=Buffer.from(b);let at=malicious.indexOf(Buffer.from([0x50,0x4b,0x01,0x02]));malicious.writeUInt32LE(0xffffffff,at+24);assert.throws(()=>zipPreflight(malicious));assert.throws(()=>zipPreflight(new Uint8Array(0)))})
test('single column line extraction groups by baseline and ignores empty items',()=>{assert.deepEqual(textLines([{str:'right',transform:[0,0,0,0,20,100]},{str:'bottom',transform:[0,0,0,0,0,20]},{str:'left',transform:[0,0,0,0,0,101]},{str:''}]),['left right','bottom'])})
