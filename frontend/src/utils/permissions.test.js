import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ROLE_OPTIONS, roleLabel, mayPublish } from './permissions.js'

test('three named roles and deny unknown roles', () => {
  assert.equal(ROLE_OPTIONS.length, 3)
  assert.equal(roleLabel('user'), '低权限')
  assert.equal(roleLabel('elevated'), '高权限')
  assert.equal(roleLabel('admin'), '管理员')
  assert.equal(roleLabel('owner'), '未授权')
})

test('only active high/admin users publish', () => {
  for (const role of ['user', 'elevated', 'admin', 'owner', undefined]) {
    assert.equal(mayPublish({ role }), ['elevated', 'admin'].includes(role))
    assert.equal(mayPublish({ role, is_muted: true }), false)
    assert.equal(mayPublish({ role, is_deleted: true }), false)
  }
  assert.equal(mayPublish(null), false)
})
