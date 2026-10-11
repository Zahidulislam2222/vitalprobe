import { useRef, useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { ArrowUpRight, Check, Code2, Copy, LockKeyhole, Terminal, X } from 'lucide-react'
import { website as w } from './lib/pages'
import type { PageId } from './lib/pages'
import { animation, parseSiteConfig } from './config'
import { setupCommands } from './lib/setup'
import { content as c } from './lib/content'
import { useMotionPaused, useSettledMotion } from './lib/motion'

const config = parseSiteConfig(import.meta.env)

export function PageHeading({ page }: { page: PageId }) {
  const data = w.pages[page]
  const reduce = useMotionPaused()
  const controls = useSettledMotion(reduce, animation.revealSeconds)
  return <section className="page-heading" id="top"><div className="container"><a className="page-breadcrumb" href="/">{c.brand}<span>/ {data.label}</span></a>
    <p className="eyebrow">{data.eyebrow}</p><motion.h1 initial={reduce ? false : { opacity: 0, y: animation.entranceDistance }} animate={controls} transition={{ duration: reduce ? 0 : animation.revealSeconds }}>{data.heading}</motion.h1><p>{data.description}</p><span className="heading-index" aria-hidden="true">0{Object.keys(w.pages).indexOf(page) + 1}</span></div></section>
}
function FeatureCard({ card, index, page }: { card: { label: string; title: string; text: string }; index: number; page: PageId }) {
  const reduce = useMotionPaused()
  const controls = useSettledMotion(reduce)
  return <motion.article className="feature-card" initial={reduce ? false : { opacity: 0, y: animation.revealDistance }} animate={controls} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: reduce ? 0 : animation.revealSeconds, delay: reduce ? 0 : index * animation.staggerSeconds }} whileHover={reduce ? undefined : { y: animation.cardLift }}><span className="mini-label">{card.label}</span><div className="feature-glyph" aria-hidden="true">{page === 'trust' ? <LockKeyhole /> : <Code2 />}</div><h2>{card.title}</h2><p>{card.text}</p></motion.article>
}
export function FeatureCards({ page }: { page: PageId }) {
  return <section className="feature-section section-pad"><div className="container feature-grid">{w.pages[page].cards.map((card, index) => <FeatureCard key={card.label} card={card} index={index} page={page} />)}</div></section>
}
export function HomeLinks() {
  return <section className="site-directory section-pad"><div className="container"><p className="eyebrow">{w.home.eyebrow}</p><h2>{w.home.heading}</h2><p className="section-description">{w.home.description}</p><div className="directory-grid">{w.home.links.map((item) => <a className="directory-card" key={item.page} href={w.pages[item.page].path}><span className="mini-label">{item.number} / {w.pages[item.page].label}</span><ArrowUpRight aria-hidden="true"/><h3>{item.title}</h3><p>{item.text}</p></a>)}</div></div></section>
}
function Availability({ plan, onClose }: { plan: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { dialog.current?.showModal() }, [])
  return <dialog className="quickstart-dialog" ref={dialog} onClose={onClose} aria-labelledby="availability-title" onClick={(event) => { if (event.target === event.currentTarget) dialog.current?.close() }}><div className="quickstart-inner" data-lenis-prevent><button className="dialog-close" aria-label={w.pricing.close} onClick={() => dialog.current?.close()}><X aria-hidden="true" /></button><div className="quickstart-icon"><LockKeyhole aria-hidden="true" /></div><p className="eyebrow">{plan}</p><h2 id="availability-title">{w.pricing.dialogTitle}</h2><p>{w.pricing.dialogDescription}</p><ul className="availability-list">{w.pricing.checks.map((check) => <li key={check}>{check}</li>)}</ul><a className="arrow-link" href={w.pages.trust.path}>{w.pricing.link}<ArrowUpRight aria-hidden="true" size={16} /></a></div></dialog>
}
export function Pricing({ onSetup, onModal }: { onSetup: () => void; onModal: (open: boolean) => void }) {
  const [plan, setPlan] = useState('')
  function select(value: string) { setPlan(value); onModal(Boolean(value)) }
  return <section className="pricing-section section-pad"><div className="container"><div className="pricing-grid">{w.pricing.plans.map((item) => <article className={`price-card ${item.id === 'automated' ? 'price-featured' : ''}`} key={item.id}><div className="plan-status"><span />{item.status}</div><h2>{item.name}</h2><p>{item.description}</p><div className="plan-price">${item.price}<span>/ {item.period}</span></div><button className={`button ${item.id === 'engine' ? 'button-mint' : 'button-outline'}`} onClick={() => item.id === 'engine' ? onSetup() : select(item.name)}>{item.action}<ArrowUpRight size={17} aria-hidden="true" /></button><ul>{item.features.map((feature) => <li key={feature}><Check size={15} aria-hidden="true" />{feature}</li>)}</ul></article>)}</div><p className="payment-notice"><LockKeyhole size={17} aria-hidden="true" />{w.pricing.notice}</p></div>{plan && <Availability plan={plan} onClose={() => select('')} />}</section>
}
export function DocsSetup() {
  const [method, setMethod] = useState('uv')
  const [status, setStatus] = useState('')
  const commands = setupCommands(method, config.repositoryUrl).join('\n')
  async function copy() { try { await navigator.clipboard.writeText(commands); setStatus(w.docs.copied) } catch { setStatus(w.docs.fallback) } }
  return <section className="docs-section section-pad"><div className="container docs-grid"><div><p className="eyebrow"><Terminal size={16} aria-hidden="true" />{c.ui.onYourMachine}</p><h2>{w.docs.setup}</h2><p className="section-description">{c.quickstart.description}</p><div className="method-tabs" role="group" aria-label="Installation method">{c.quickstart.methods.map((item) => <button key={item.id} aria-pressed={method === item.id} className={method === item.id ? 'active' : ''} onClick={() => { setMethod(item.id); setStatus('') }}>{item.label}</button>)}</div><pre tabIndex={0}><code>{commands}</code></pre><button className="button button-outline" onClick={() => void copy()}><Copy size={16} aria-hidden="true" />{w.docs.copy}</button><p role="status" className="copy-status">{status}</p><p className="section-description">{c.quickstart.methods.find((item) => item.id === method)?.note}</p></div><div className="docs-resources"><h2>{w.docs.resources}</h2>{w.docs.links.map((item) => <a key={item.key} href={config[item.key]} target="_blank" rel="noopener noreferrer"><div><h3>{item.title}</h3><p>{item.text}</p></div><ArrowUpRight size={20} aria-hidden="true" /></a>)}</div></div></section>
}
export function TrustDetails() {
  return <section className="trust-details section-pad"><div className="container"><h2>{w.trust.heading}</h2><div className="trust-rows">{w.trust.items.map((item, index) => <article key={item.title}><span className="mini-label">0{index + 1}</span><h3>{item.title}</h3><p>{item.text}</p></article>)}</div><a className="arrow-link" href={config.releaseUrl} target="_blank" rel="noopener noreferrer">{c.footer.release}<ArrowUpRight size={17} aria-hidden="true" /></a></div></section>
}
