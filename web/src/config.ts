import { z } from 'zod'

export const siteDefaults = {
  repositoryUrl: 'https://github.com/Zahidulislam2222/vitalprobe',
  reportUrl: '/evidence/',
  evidenceUrl: '/evidence/run.json',
  devHost: '127.0.0.1',
  devPort: 18831,
  heroPoster: '/media/signal-instrument.webp',
  heroVideo: '/media/signal-instrument.mp4',
  repositoryPaths: { docs: '/tree/main/docs', quickstart: '/blob/main/docs/quickstart.md', release: '/blob/main/docs/release-status.md' },
} as const

function safeLink(value: string, allowLocal: boolean) {
  if (/[\\\s]/.test(value) || [...value].some((character) => character.charCodeAt(0) < 32) || /%5c/i.test(value)) return false
  const local = value.startsWith('/') && !value.startsWith('//') && !/^\/%2f/i.test(value)
  try {
    const url = new URL(value, 'https://vitalprobe.invalid')
    return !url.username && !url.password && url.protocol === 'https:' &&
      (allowLocal && local || value.startsWith('https://'))
  } catch { return false }
}

const localOrHttps = z.string().refine((value) => safeLink(value, true), 'Expected a same-origin path or HTTPS URL')
const configSchema = z.object({
  repositoryUrl: z.string().refine((value) => safeLink(value, false) && !/[?#]/.test(value),
    'Expected a credential-free HTTPS repository base without a query or fragment'),
  reportUrl: localOrHttps,
  evidenceUrl: localOrHttps,
})

export function parseSiteConfig(env: Record<string, string | undefined>) {
  const parsed = configSchema.parse({
    repositoryUrl: env.VITE_REPOSITORY_URL || siteDefaults.repositoryUrl,
    reportUrl: env.VITE_REPORT_URL || siteDefaults.reportUrl,
    evidenceUrl: env.VITE_EVIDENCE_URL || siteDefaults.evidenceUrl,
  })
  const base = parsed.repositoryUrl.replace(/\/+$/, '').replace(/\.git$/, '')
  return { ...parsed, docsUrl: base + siteDefaults.repositoryPaths.docs,
    quickstartUrl: base + siteDefaults.repositoryPaths.quickstart,
    releaseUrl: base + siteDefaults.repositoryPaths.release }
}

const devSchema = z.object({
  host: z.enum(['127.0.0.1', '::1', 'localhost']),
  port: z.coerce.number().int().min(1024).max(65535),
})
export function parseDevConfig(env: Record<string, string | undefined>) {
  return devSchema.parse({ host: env.SITE_DEV_HOST || siteDefaults.devHost, port: env.SITE_DEV_PORT || siteDefaults.devPort })
}

export const animation = {
  reducedMotionQuery: '(prefers-reduced-motion: reduce)',
  heroScrollRange: [0, 850],
  heroTravelRange: [0, 110],
  cardLift: -6,
  detailDistance: 8,
  terminalDistance: 6,
  entranceDistance: 20,
  revealSeconds: 0.65,
  revealDistance: 24,
  staggerSeconds: 0.08,
  hoverSeconds: 0.2,
  scrollLerp: 0.085,
  anchorSeconds: 1.1,
  spring: { type: 'spring' as const, stiffness: 180, damping: 24 },
}
