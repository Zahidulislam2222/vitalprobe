import { z } from 'zod'
import site from '../data/site.json' with { type: 'json' }

const text = z.string().min(1)
const contentSchema = z.object({
  brand: text, tagline: text,
  nav: z.array(z.object({ label: text, href: z.string().startsWith('#') })).min(1),
  hero: z.object({ eyebrow: text, lines: z.array(text).min(1), accent: text, description: text,
    primary: text, secondary: text, note: text, visualCaption: text, visualNote: text }),
  proof: z.array(z.object({ value: text, label: text, detail: text })).min(1),
  evidence: z.object({ eyebrow: text, heading: text, description: text, runLabel: text, targetLabel: text,
    runVerdict: text, disclaimer: text, categories: z.array(z.object({ id: text, label: text })).min(1),
    scenarioLabel: text, responseLabel: text, checkLabel: text, fullReport: text, download: text, empty: text }),
  workflow: z.object({ eyebrow: text, heading: text, description: text,
    steps: z.array(z.object({ number: text, title: text, description: text, command: text, signal: text })).min(1) }),
  approach: z.object({ eyebrow: text, heading: text, intro: text, principles: z.array(z.object({
    icon: z.enum(['synthetic', 'local', 'evidence', 'human']), number: text, title: text, description: text })).min(1) }),
  gettingStarted: z.object({ eyebrow: text, heading: text, description: text, button: text, source: text, note: text }),
  faq: z.object({ eyebrow: text, heading: text, items: z.array(z.object({ question: text, answer: text })).min(1) }),
  quickstart: z.object({ title: text, description: text, bootstrap: z.array(text).min(1), methods: z.array(z.object({ id: text, label: text,
    commands: z.array(text).min(1), note: text })).min(1), copy: text, copied: text, copyFallback: text, docs: text }),
  footer: z.object({ description: text, status: text, disclaimer: text, source: text, release: text, report: text, top: text, copyright: text }),
  ui: z.record(z.string(), text),
  seo: z.object({ title: text, description: text, ogDescription: text, noscriptDescription: text, noscriptReportLink: text }),
})
export const content = contentSchema.parse(site)
