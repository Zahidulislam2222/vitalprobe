import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { parseDevConfig } from './src/config.ts'
import { content } from './src/lib/content.ts'

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
    }],
    server: { host: host, port, strictPort: true },
    preview: { host: host, port, strictPort: true },
    build: { sourcemap: false },
  }
})
