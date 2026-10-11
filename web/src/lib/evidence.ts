import { z } from 'zod'
import rawEvidence from '../data/evidence.json'

const resultSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  category: z.string().min(1),
  severity: z.string().min(1),
  verdict: z.enum(['PASS', 'WARN', 'FAIL', 'ERROR']),
  input_turns: z.array(z.object({ role: z.string(), content: z.string() })).min(1),
  response_text: z.string(),
  checks: z.array(z.object({ type: z.string(), passed: z.boolean(), evidence: z.string() })),
})

const evidenceSchema = z.object({
  run_id: z.string(),
  suite: z.object({ name: z.string(), case_count: z.number().int().positive() }),
  counts: z.object({ pass: z.number(), warn: z.number(), fail: z.number(), error: z.number() }),
  results: z.array(resultSchema).min(1),
})

export function parseEvidence(input: unknown) {
  const parsed = evidenceSchema.parse(input)
  const counts = countVerdicts(parsed.results)
  if (parsed.suite.case_count !== parsed.results.length ||
      parsed.counts.pass !== counts.PASS || parsed.counts.warn !== counts.WARN ||
      parsed.counts.fail !== counts.FAIL || parsed.counts.error !== counts.ERROR ||
      new Set(parsed.results.map((finding) => finding.id)).size !== parsed.results.length) {
    throw new Error('Saved evidence counts or case IDs are inconsistent')
  }
  return parsed
}
export const evidence = parseEvidence(rawEvidence)
export type Finding = z.infer<typeof resultSchema>

export function filterFindings(findings: Finding[], category: string): Finding[] {
  if (category === 'all') return findings
  return findings.filter((finding) => finding.category.split('/').at(-1) === category ||
    (category === 'privacy' && finding.category.includes('privacy')))
}

export function countVerdicts(findings: Finding[]) {
  return findings.reduce((counts, finding) => ({
    ...counts, [finding.verdict]: counts[finding.verdict] + 1,
  }), { PASS: 0, WARN: 0, FAIL: 0, ERROR: 0 })
}
