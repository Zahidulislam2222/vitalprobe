import { expect, it } from 'vitest'
import envExample from '../../.env.example?raw'

const sources = import.meta.glob('../**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const publishedText = import.meta.glob(['../data/*.json', '../../public/**/*.json', '../../public/**/*.html'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const runtimeSources = Object.entries(sources).filter(([path]) => !path.endsWith('.test.ts'))

it('keeps keys and provider endpoints out of the browser runtime', () => {
  const privateKey = /BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY/
  const apiToken = /\b(?:sk-(?:or-v1-)?[A-Za-z0-9_-]{20,}|(?:sk|rk)_(?:test|live)_[A-Za-z0-9_-]{20,})\b/
  for (const [path, source] of [...runtimeSources, ...Object.entries(publishedText)]) {
    expect(source, path).not.toMatch(privateKey)
    expect(source, path).not.toMatch(apiToken)
  }
  for (const [path, source] of runtimeSources) {
    if (!path.endsWith('/config.ts')) {
      expect(source, path).not.toMatch(/https?:\/\//)
      expect(source, path).not.toContain('import.meta.env.VITE_')
    }
  }
})
it('documents every public environment name and refuses secret-shaped VITE names', () => {
  const source = runtimeSources.find(([path]) => path.endsWith('/config.ts'))![1]
  const names = [...source.matchAll(/env\.(VITE_[A-Z_]+|SITE_[A-Z_]+)/g)].map((match) => match[1])
  expect(names.length).toBeGreaterThan(0)
  for (const name of names) expect(envExample).toContain(`${name}=`)
  expect(envExample).not.toMatch(/VITE_\w*(?:KEY|SECRET|TOKEN|PASSWORD)\s*=/)
})
