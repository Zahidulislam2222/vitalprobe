import { describe, expect, it } from 'vitest'
import { countVerdicts, evidence, filterFindings, parseEvidence } from './evidence'
import { content } from './content'
import { parseDevConfig, parseSiteConfig, siteDefaults } from '../config'

describe('the real saved synthetic evidence', () => {
  it('agrees with every displayed summary', () => {
    expect(countVerdicts(evidence.results)).toEqual({ PASS: 3, WARN: 0, FAIL: 22, ERROR: 0 })
    expect(evidence.results).toHaveLength(25)
    expect(content.proof[0].value).toBe(String(evidence.results.length))
    expect(content.evidence.runVerdict).toContain(String(evidence.counts.fail))
  })
  it.each(content.evidence.categories)('makes the $label filter reachable and accurate', ({ id }) => {
    const found = filterFindings(evidence.results, id)
    expect(found.length).toBeGreaterThan(0)
    if (id !== 'all') expect(found.every((row) => row.category.includes(id))).toBe(true)
  })
  it('rejects stale summaries, duplicate identifiers and malformed evidence', () => {
    expect(() => parseEvidence({ ...evidence, counts: { ...evidence.counts, fail: 0 } })).toThrow()
    expect(() => parseEvidence({ ...evidence, results: [evidence.results[0], ...evidence.results.slice(0, -1)] })).toThrow()
    expect(() => parseEvidence({ ...evidence, results: [] })).toThrow()
  })
  it('keeps human gates and target limitations visible in maintained copy', () => {
    expect(content.footer.status).toContain('GATES OPEN')
    expect(content.approach.principles.find((item) => item.icon === 'human')?.description).toContain('still open')
    expect(content.evidence.disclaimer).toContain('scripted target only')
    expect(content.footer.disclaimer).toContain('No clinical validation')
  })
})

describe('the public configuration boundary', () => {
  it('owns defaults and supports public overrides without business-code changes', () => {
    expect(parseSiteConfig({}).repositoryUrl).toBe(siteDefaults.repositoryUrl)
    expect(parseSiteConfig({}).quickstartUrl).toBe(siteDefaults.repositoryUrl + siteDefaults.repositoryPaths.quickstart)
    expect(parseSiteConfig({ VITE_REPORT_URL: '/different-report/' }).reportUrl).toBe('/different-report/')
    expect(parseDevConfig({ SITE_DEV_PORT: '18832' }).port).toBe(18832)
  })
  it.each(['javascript:alert(1)', '//evil.test', '/\\evil.test', '/%5cevil.test', '/%2fevil.test',
    'https://user:pass@example.test', 'http://example.test', 'https://example.test/\n'])('rejects unsafe report links: %s', (value) => {
    expect(() => parseSiteConfig({ VITE_REPORT_URL: value })).toThrow()
  })
  it.each(['?ref=main', '#readme', '?', '#'])('rejects repository queries/fragments: %s', (suffix) => {
    expect(() => parseSiteConfig({ VITE_REPOSITORY_URL: 'https://source.example.test/team/tool' + suffix })).toThrow()
  })
  it('derives documentation paths from a normalized Git repository base', () => {
    const config = parseSiteConfig({ VITE_REPOSITORY_URL: 'https://source.example.test/team/tool.git/' })
    expect(config.quickstartUrl).toBe('https://source.example.test/team/tool/blob/main/docs/quickstart.md')
  })
  it.each(['0','65536','not-a-port'])('rejects invalid development ports: %s', (value) => {
    expect(() => parseDevConfig({ SITE_DEV_PORT: value })).toThrow()
  })
  it('keeps the preview loopback-only', () => {
    expect(() => parseDevConfig({ SITE_DEV_HOST: '0.0.0.0' })).toThrow()
  })
})
