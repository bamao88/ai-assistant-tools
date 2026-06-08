import path from 'node:path'
import { fileURLToPath } from 'node:url'

const srcDir = path.dirname(fileURLToPath(import.meta.url))

export const ENGINE_DIR = path.resolve(srcDir, '..')
export const TOOLS_ROOT = path.resolve(ENGINE_DIR, '..', '..')

export function credentialsDir() {
  return process.env.DRAFT_DIRECT_CREDENTIAL_DIR
    ? path.resolve(process.env.DRAFT_DIRECT_CREDENTIAL_DIR)
    : path.join(TOOLS_ROOT, 'var', 'credentials', 'platform-draft-direct')
}

export function platformCookiePath(platform) {
  return path.join(credentialsDir(), `${platform}.json`)
}

export function expectedAccountsPath() {
  return path.join(TOOLS_ROOT, 'vendor', 'wechatsync', 'config', 'project-platforms.json')
}
