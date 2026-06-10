import test from 'node:test'
import assert from 'node:assert/strict'
import { accountMatches, formatAuthAccount, formatExpectedAccount } from '../src/util.js'

test('accountMatches supports legacy expected account strings', () => {
  assert.equal(accountMatches({ username: '张和All in AI', userId: 'u1' }, '张和'), true)
  assert.equal(accountMatches({ username: '其它账号', userId: 'u1' }, '张和'), false)
})

test('accountMatches prefers stable user id when expected account is structured', () => {
  assert.equal(accountMatches(
    { username: '改名后的账号', userId: '123' },
    { username: '利幼枫0hK', userId: '123' }
  ), true)
  assert.equal(accountMatches(
    { username: '利幼枫0hK', userId: '456' },
    { username: '利幼枫0hK', userId: '123' }
  ), false)
  assert.equal(accountMatches(
    { username: '其它账号', userId: '456' },
    { username: '利幼枫0hK', userId: '123' }
  ), false)
})

test('account formatter includes username and id without exposing credentials', () => {
  assert.equal(formatAuthAccount({ username: '利幼枫0hK', userId: '123' }), '利幼枫0hK / id:123')
  assert.equal(formatExpectedAccount({ username: '利幼枫0hK', userId: '123' }), '利幼枫0hK / id:123')
})
