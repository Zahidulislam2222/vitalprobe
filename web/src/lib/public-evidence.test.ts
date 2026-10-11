import { expect, it } from 'vitest'
import raw from '../data/evidence.json'
import rootJson from '../../public/run.json'
import reportJson from '../../public/evidence/run.json'
import reportHtml from '../../public/evidence/index.html?raw'
import { parseEvidence } from './evidence'
import { setupCommands } from './setup'
import { parseSiteConfig } from '../config'

it('keeps both downloadable JSON copies identical to the explorer evidence', () => {
  expect(rootJson).toEqual(raw)
  expect(reportJson).toEqual(raw)
  expect(parseEvidence(rootJson).results).toHaveLength(25)
})
it('preserves every case and the limitations in the original HTML report', () => {
  for (const finding of raw.results) expect(reportHtml).toContain(finding.id)
  expect(reportHtml.match(/<article class="finding/g)?.length).toBe(raw.results.length)
  expect(reportHtml).toContain('Methodology &amp; limitations')
  expect(reportHtml).toContain('synthetic')
})
it('uses the validated repository override in both copied setup methods', () => {
  const config = parseSiteConfig({ VITE_REPOSITORY_URL: 'https://source.example.test/team/custom-tool' })
  for (const method of ['uv', 'docker']) {
    const commands = setupCommands(method, config.repositoryUrl)
    expect(commands[0]).toBe("git clone 'https://source.example.test/team/custom-tool' vitalprobe")
    expect(commands[1]).toBe('cd vitalprobe')
    expect(commands.join('\n')).not.toContain('github.com')
  }
})
it('quotes shell metacharacters in repository overrides and rejects unknown methods', () => {
  const value = "https://source.example.test/team/it's$(echo-unsafe)"
  const config = parseSiteConfig({ VITE_REPOSITORY_URL: value })
  expect(setupCommands('uv', config.repositoryUrl)[0]).toBe("git clone 'https://source.example.test/team/it'\"'\"'s$(echo-unsafe)' vitalprobe")
  expect(() => setupCommands('unknown', config.repositoryUrl)).toThrow()
})
