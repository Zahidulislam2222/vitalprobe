import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { parseDevConfig } from './src/config.ts'
import { content } from './src/lib/content.ts'
import { website } from './src/lib/pages.ts'

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!)
}
const pageData: Record<string, string> = {
  TITLE: content.seo.title, DESCRIPTION: content.seo.description,
  OG_DESCRIPTION: content.seo.ogDescription, BRAND: content.brand,
  NOSCRIPT_DESCRIPTION: content.seo.noscriptDescription,
  NOSCRIPT_REPORT_LINK: content.seo.noscriptReportLink,
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const { host, port } = parseDevConfig(env)
  return {
    plugins: [react(), {
      name: 'maintained-page-copy',
      transformIndexHtml(html: string) {
        return html.replace(/__SITE_([A-Z_]+)__/g, (_, key: string) => escapeHtml(pageData[key]))
      },
    }, {
      name: 'static-page-routes', enforce: 'post',
      generateBundle(_, bundle) {
        const index = bundle['index.html']
        if (!index || index.type !== 'asset') throw new Error('Missing built HTML entry')
        const html = String(index.source)
        for (const page of Object.values(website.pages)) {
          const links = Object.values(website.pages).map((item) => `<a href="${item.path}">${escapeHtml(item.label)}</a>`).join(' · ')
          const output = html.replace(/<title>.*?<\/title>/, `<title>${escapeHtml(page.title)}</title>`)
            .replace(/(<meta property="og:title" content=")[^"]*/, `$1${escapeHtml(page.title)}`)
            .replace(/(<meta name="description" content=")[^"]*/, `$1${escapeHtml(page.description)}`)
            .replace(/<noscript>[\s\S]*?<\/noscript>/, `<noscript><main><h1>${escapeHtml(page.heading)}</h1><p>${escapeHtml(page.description)}</p><nav>${links}</nav><a href="/evidence/">${escapeHtml(content.seo.noscriptReportLink)}</a></main></noscript>`)
          this.emitFile({ type: 'asset', fileName: page.path.slice(1) + 'index.html', source: output })
        }
      },
    }],
    server: { host: host, port, strictPort: true },
    preview: { host: host, port, strictPort: true },
    build: { sourcemap: false },
  }
})
