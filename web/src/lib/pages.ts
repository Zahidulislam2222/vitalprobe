import { z } from 'zod'
import data from '../data/pages.json' with { type: 'json' }

const text = z.string().min(1)
const pageId = z.enum(['product', 'explore', 'pricing', 'docs', 'trust'])
const card = z.object({ label: text, title: text, text })
const page = z.object({ path: z.string().regex(/^\/[a-z]+\/$/), label: text, eyebrow: text, heading: text, description: text, title: text, cards: z.array(card) })
const schema = z.object({
  pages: z.object({ product: page, explore: page, pricing: page, docs: page, trust: page }),
  motion: z.object({ pause: text, resume: text, label: text }),
  pricing: z.object({ notice: text, plans: z.array(z.object({ id: z.enum(['engine', 'automated', 'clinician']), name: text, price: z.number().nonnegative(), period: text, status: text, description: text, features: z.array(text).min(1), action: text })).length(3), dialogTitle: text, dialogDescription: text, checks: z.array(text), close: text, link: text }),
  home: z.object({ eyebrow: text, heading: text, description: text, links: z.array(z.object({ page: pageId, number: text, title: text, text })) }),
  docs: z.object({ setup: text, copy: text, copied: text, fallback: text, resources: text, links: z.array(z.object({ key: z.enum(['quickstartUrl', 'docsUrl', 'releaseUrl']), title: text, text })) }),
  trust: z.object({ heading: text, items: z.array(z.object({ title: text, text })) }),
})
export const website = schema.parse(data)
export type PageId = z.infer<typeof pageId>
export function pageFromPath(path: string): PageId | 'home' | 'missing' {
  if (path === '/' || path === '/index.html') return 'home'
  const normalized = path.endsWith('/index.html') ? path.slice(0, -10) : path.replace(/\/?$/, '/')
  return (Object.entries(website.pages).find(([, value]) => value.path === normalized)?.[0] as PageId | undefined) ?? 'missing'
}
