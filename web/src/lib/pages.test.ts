import { describe, expect, it } from 'vitest'
import { pageFromPath, website } from './pages'

describe('real page URLs', () => {
  it.each(Object.entries(website.pages))('resolves %s including direct HTML and slashless navigation', (id, page) => {
    expect(pageFromPath(page.path)).toBe(id)
    expect(pageFromPath(page.path.slice(0, -1))).toBe(id)
    expect(pageFromPath(page.path + 'index.html')).toBe(id)
  })
  it('does not treat unknown or encoded paths as a known page', () => {
    expect(pageFromPath('/')).toBe('home')
    expect(pageFromPath('/index.html')).toBe('home')
    expect(pageFromPath('/does-not-exist/')).toBe('missing')
    expect(pageFromPath('/%64ocs/')).toBe('missing')
  })
  it('keeps paid tiers explicitly unavailable without a checkout destination', () => {
    expect(website.pricing.notice).toContain('not available')
    expect(website.pricing.plans.map((plan) => plan.id)).toEqual(['engine', 'automated', 'clinician'])
    expect(website.pricing.plans.find((plan) => plan.id === 'automated')?.status).toContain('Not on sale')
    expect(website.pricing.plans.find((plan) => plan.id === 'clinician')?.status).toContain('gates open')
    expect(JSON.stringify(website)).not.toMatch(/buy\.stripe\.com|checkout\.stripe\.com/)
  })
})
