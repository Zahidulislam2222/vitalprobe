import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion, useScroll, useSpring } from 'motion/react'
import { ReactLenis, useLenis } from 'lenis/react'
import {
  ArrowDown, ArrowRight, ArrowUpRight, Check, CheckCircle2, ChevronDown,
  ChevronRight, Code2, Copy, FileJson2, Fingerprint, FlaskConical,
  LockKeyhole, Menu, Pause, Play, ScanLine, ShieldCheck, Terminal, X, XCircle,
} from 'lucide-react'
import { animation, parseSiteConfig, siteDefaults } from './config'
import { content as c } from './lib/content'
import { countVerdicts, evidence, filterFindings } from './lib/evidence'
import type { Finding } from './lib/evidence'
import { setupCommands } from './lib/setup'

const config = parseSiteConfig(import.meta.env)

function Brand({ compact = false }: { compact?: boolean }) {
  return <a className="brand" href="#top" aria-label={`${c.brand} home`}>
    <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M2 17h8l4-9 5 17 4-8h7" /></svg></span>
    {!compact && <span>{c.brand}<span className="brand-dot">.</span></span>}
  </a>
}

function Reveal({ children, className = '', delay = 0 }: {
  children: ReactNode; className?: string; delay?: number
}) {
  const reduce = useReducedMotion()
  return <motion.div className={className}
    initial={reduce ? false : { opacity: 0, y: animation.revealDistance }}
    whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.12 }}
    transition={{ duration: reduce ? 0 : animation.revealSeconds, delay, ease: [0.22, 1, 0.36, 1] }}>
    {children}
  </motion.div>
}

function ArrowLink({ href, children, className = '', external = false }: {
  href: string; children: ReactNode; className?: string; external?: boolean
}) {
  return <a className={`arrow-link ${className}`} href={href}
    {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}>
    {children}<ArrowUpRight size={17} aria-hidden="true" />
  </a>
}

function HeroMedia() {
  const video = useRef<HTMLVideoElement>(null)
  const reduce = useReducedMotion()
  const [playing, setPlaying] = useState(false)
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    const current = video.current
    if (!current) return
    // The detailed still remains the primary artwork. Playback is a deliberate choice.
    if (reduce) current.pause()
  }, [reduce])

  function toggleVideo() {
    const current = video.current
    if (!current) return
    if (current.paused) void current.play().catch(() => setUnavailable(true))
    else current.pause()
  }

  return <div className="hero-media">
    <video ref={video} muted loop playsInline preload="none" poster={siteDefaults.heroPoster}
      src={siteDefaults.heroVideo} aria-hidden="true" tabIndex={-1}
      onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
      onError={() => setUnavailable(true)} />
    <div className="hero-media-shade" />
    <div className="signal-label"><span className="signal-dot" />{c.hero.visualCaption}</div>
    {!unavailable && <button className="media-control" onClick={toggleVideo}
      aria-label={playing ? c.ui.pauseAnimation : c.ui.playAnimation}>
      {playing ? <Pause size={14} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
      <span>{playing ? c.ui.pauseMotion : c.ui.playMotion}</span>
    </button>}
    <p className="visual-note">{c.hero.visualNote}</p>
  </div>
}

function FindingDetail({ finding }: { finding: Finding }) {
  const reduce = useReducedMotion()
  return <motion.div className="finding-detail" key={finding.id}
    initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0 }} transition={{ duration: reduce ? 0 : animation.hoverSeconds }}>
    <div className="finding-topline"><span className={`verdict verdict-${finding.verdict.toLowerCase()}`}>
      {finding.verdict === 'PASS' ? <Check size={12} aria-hidden="true" /> : <X size={12} aria-hidden="true" />}
      {finding.verdict}
    </span><span className="severity">{finding.severity} {c.ui.severity}</span></div>
    <h3>{finding.title}</h3>
    <div className="conversation">
      <div className="conversation-block"><div className="mini-label"><span className="conversation-dot" />{c.evidence.scenarioLabel}</div>
        <p>{finding.input_turns.filter((turn) => turn.role === 'user').at(-1)?.content}</p></div>
      <div className="conversation-block bot-response"><div className="mini-label"><span className="conversation-dot amber" />{c.evidence.responseLabel}</div>
        <p>{finding.response_text}</p></div>
    </div>
    <div className="check-list"><div className="mini-label">{c.evidence.checkLabel}</div>
      {finding.checks.map((check, index) => <div className={`check-row ${check.passed ? 'is-pass' : 'is-fail'}`} key={`${check.type}-${index}`}>
        {check.passed ? <CheckCircle2 size={16} aria-label="Passed" /> : <XCircle size={16} aria-label="Failed" />}
        <div><span className="check-type">{check.type.replaceAll('_', ' ')}</span><p>{check.evidence}</p></div>
      </div>)}
    </div>
    <div className="finding-id"><Fingerprint size={13} aria-hidden="true" />{finding.id}</div>
  </motion.div>
}

function EvidenceExplorer() {
  const [category, setCategory] = useState('all')
  const [selectedId, setSelectedId] = useState(evidence.results.find((finding) => finding.verdict === 'FAIL')?.id || evidence.results[0].id)
  const filtered = filterFindings(evidence.results, category)
  const selected = filtered.find((finding) => finding.id === selectedId) || filtered[0]
  const counts = countVerdicts(evidence.results)

  function chooseCategory(next: string) {
    setCategory(next)
    setSelectedId(filterFindings(evidence.results, next)[0]?.id || '')
  }

  return <section className="evidence-section section-pad" id="evidence" aria-labelledby="evidence-title">
    <div className="container">
      <Reveal className="section-intro split-intro"><div><p className="eyebrow">{c.evidence.eyebrow}</p>
        <h2 id="evidence-title">{c.evidence.heading}</h2></div><p className="section-description">{c.evidence.description}</p></Reveal>
      <Reveal className="evidence-console">
        <div className="console-topbar"><div className="window-dots" aria-hidden="true"><i /><i /><i /></div>
          <span>vitalprobe / {evidence.suite.name}</span><span className="saved-indicator"><span />{c.ui.savedRun}</span></div>
        <div className="run-summary"><div><p className="mini-label">{c.evidence.targetLabel}</p><h3>{c.evidence.runVerdict}</h3></div>
          <div className="run-counts"><div><strong>{evidence.results.length}</strong><span>{c.ui.scenarios}</span></div>
            <div className="count-pass"><strong>{counts.PASS.toString().padStart(2, '0')}</strong><span>{c.ui.pass}</span></div>
            <div className="count-fail"><strong>{counts.FAIL}</strong><span>{c.ui.fail}</span></div>
            <div><strong>{counts.ERROR.toString().padStart(2, '0')}</strong><span>{c.ui.errors}</span></div></div></div>
        <div className="filter-bar" role="group" aria-label="Filter fictional scenarios">
          {c.evidence.categories.map((filter) => <button key={filter.id} className={category === filter.id ? 'active' : ''}
            aria-pressed={category === filter.id} onClick={() => chooseCategory(filter.id)}>{filter.label}
            {category === filter.id && <span>{filtered.length}</span>}</button>)}
        </div>
        <div className="explorer-body"><div className="scenario-list" data-lenis-prevent aria-label="Fictional scenario results">
          {filtered.map((finding) => <button key={finding.id} className={`scenario-item ${finding.id === selected?.id ? 'selected' : ''}`}
            aria-pressed={finding.id === selected?.id} onClick={() => setSelectedId(finding.id)}>
            <span className={`scenario-status ${finding.verdict.toLowerCase()}`} aria-label={finding.verdict}>
              {finding.verdict === 'PASS' ? <Check size={13} aria-hidden="true" /> : <X size={13} aria-hidden="true" />}</span>
            <span>{finding.title}<small>{finding.category.split('/').at(-1)}</small></span>
            <ChevronRight size={15} aria-hidden="true" />
          </button>)}
          {filtered.length === 0 && <p className="empty-state">{c.evidence.empty}</p>}
        </div><div className="detail-wrapper" data-lenis-prevent>
          <span className="sr-only" role="status" aria-live="polite">{selected?.title}</span>
          <AnimatePresence mode="wait" initial={false}>{selected && <FindingDetail finding={selected} key={selected.id} />}</AnimatePresence>
        </div></div>
        <div className="console-footer"><ArrowLink href={config.reportUrl}>{c.evidence.fullReport}</ArrowLink>
          <a href={config.evidenceUrl} download className="json-download"><FileJson2 size={15} aria-hidden="true" />{c.evidence.download}</a></div>
      </Reveal>
      <p className="evidence-disclaimer">{c.evidence.disclaimer}</p>
    </div>
  </section>
}

function Workflow() {
  const [step, setStep] = useState(0)
  const reduce = useReducedMotion()
  return <section className="workflow-section section-pad" id="workflow" aria-labelledby="workflow-title"><div className="container workflow-layout">
    <div><Reveal><p className="eyebrow">{c.workflow.eyebrow}</p><h2 id="workflow-title">{c.workflow.heading}</h2>
      <p className="section-description">{c.workflow.description}</p></Reveal>
      <div className="workflow-steps">{c.workflow.steps.map((item, index) => <button className={`workflow-step ${step === index ? 'active' : ''}`}
        key={item.number} aria-pressed={step === index} onClick={() => setStep(index)}>
        <span className="step-number">{item.number}</span><span><strong>{item.title}</strong><span className="step-description">{item.description}</span></span>
        <ArrowUpRight size={20} aria-hidden="true" /></button>)}</div>
    </div><Reveal className="workflow-visual">
      <div className="orbital-diagram" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" />
        <div className="orbit-node node-one"><Code2 size={21} /></div><div className="orbit-node node-two"><FlaskConical size={21} /></div>
        <div className="orbit-node node-three"><ShieldCheck size={21} /></div><div className="orbit-core"><ScanLine size={44} strokeWidth={1.1} /></div>
        <span className="orbit-cross cross-one">+</span><span className="orbit-cross cross-two">+</span></div>
      <div className="workflow-terminal"><div className="terminal-label"><Terminal size={14} aria-hidden="true" />{c.ui.localWorkspace}<span className="terminal-led" /></div>
        <AnimatePresence mode="wait"><motion.div key={step} initial={reduce ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: reduce ? 0 : animation.hoverSeconds }}>
          <code><span>$ </span>{c.workflow.steps[step].command}</code><p><Check size={13} aria-hidden="true" />{c.workflow.steps[step].signal}</p>
        </motion.div></AnimatePresence></div>
      <div className="workflow-footnote"><span className="signal-dot" />{c.ui.workflowFootnote}</div>
    </Reveal>
  </div></section>
}

const principleIcons = { synthetic: FlaskConical, local: LockKeyhole, evidence: ScanLine, human: Fingerprint }

function Approach() {
  return <section className="approach-section section-pad" id="approach" aria-labelledby="approach-title"><div className="container">
    <Reveal className="section-intro"><p className="eyebrow">{c.approach.eyebrow}</p><h2 id="approach-title">{c.approach.heading}</h2>
      <p className="section-description">{c.approach.intro}</p></Reveal>
    <div className="principles">{c.approach.principles.map((principle, index) => {
      const Icon = principleIcons[principle.icon as keyof typeof principleIcons]
      return <Reveal className="principle" key={principle.number} delay={animation.staggerSeconds * index}>
        <div className="principle-topline"><span>{principle.number}</span><Icon size={25} strokeWidth={1.4} aria-hidden="true" /></div>
        <h3>{principle.title}</h3><p>{principle.description}</p>
      </Reveal>
    })}</div>
    <Reveal className="boundary-note"><span className="boundary-cross" aria-hidden="true">+</span>
      <p>{c.footer.status}</p><ArrowLink href={config.releaseUrl} external>{c.footer.release}</ArrowLink></Reveal>
  </div></section>
}

function Quickstart({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [method, setMethod] = useState('uv')
  const [copyStatus, setCopyStatus] = useState('')
  const selected = c.quickstart.methods.find((item) => item.id === method)!
  const commands = setupCommands(method, config.repositoryUrl)

  useEffect(() => {
    dialog.current?.showModal()
  }, [])

  async function copyCommands() {
    try {
      await navigator.clipboard.writeText(commands.join('\n'))
      setCopyStatus(c.quickstart.copied)
    } catch {
      setCopyStatus(c.quickstart.copyFallback)
    }
  }

  return <dialog ref={dialog} className="quickstart-dialog" aria-labelledby="quickstart-title" onClose={onClose}
    onClick={(event) => { if (event.target === event.currentTarget) dialog.current?.close() }}>
    <div className="quickstart-inner" data-lenis-prevent><button className="dialog-close" onClick={() => dialog.current?.close()} aria-label="Close setup"><X size={23} aria-hidden="true" /></button>
      <div className="quickstart-icon"><Terminal size={28} aria-hidden="true" /></div><p className="eyebrow">{c.ui.onYourMachine}</p>
      <h2 id="quickstart-title">{c.quickstart.title}</h2><p>{c.quickstart.description}</p>
      <div className="method-tabs" role="group" aria-label="Installation method">{c.quickstart.methods.map((item) => <button key={item.id} aria-pressed={method === item.id} className={method === item.id ? 'active' : ''}
        onClick={() => { setMethod(item.id); setCopyStatus('') }}>{item.label}</button>)}</div>
      <pre tabIndex={0}><code>{commands.join('\n')}</code></pre>
      <button className="button button-dark copy-button" onClick={() => void copyCommands()}><Copy size={16} aria-hidden="true" />{copyStatus === c.quickstart.copied ? c.quickstart.copied : c.quickstart.copy}</button>
      <span className="copy-status" role="status" aria-live="polite">{copyStatus}</span><p className="setup-note">{selected.note}</p>
      <ArrowLink href={config.quickstartUrl} external>{c.quickstart.docs}</ArrowLink>
    </div>
  </dialog>
}

function Experience() {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuToggle = useRef<HTMLButtonElement>(null)
  const [setupOpen, setSetupOpen] = useState(false)
  const { scrollYProgress } = useScroll()
  const progress = useSpring(scrollYProgress, animation.spring)
  const lenis = useLenis()

  useEffect(() => {
    if (!menuOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setMenuOpen(false); menuToggle.current?.focus() }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [menuOpen])

  useEffect(() => {
    if (setupOpen) lenis?.stop()
    else lenis?.start()
    return () => { lenis?.start() }
  }, [setupOpen, lenis])

  return <>
    <a href="#main" className="skip-link">Skip to content</a>
    <motion.div className="reading-progress" style={{ scaleX: progress }} aria-hidden="true" />
    <header className="site-header"><div className="container nav-container"><Brand />
      <nav className={`main-nav ${menuOpen ? 'mobile-open' : ''}`} id="main-navigation" aria-label="Main navigation"
        onKeyDown={(event) => { if (event.key === 'Escape') setMenuOpen(false) }}>
        {c.nav.map((item) => <a href={item.href} key={item.href} onClick={() => setMenuOpen(false)}>{item.label}</a>)}
        <a href={config.docsUrl} target="_blank" rel="noopener noreferrer">{c.ui.docs}<ArrowUpRight size={13} aria-hidden="true" /></a>
      </nav>
      <div className="nav-actions"><button className="button button-nav" onClick={() => setSetupOpen(true)}>{c.hero.secondary}<ArrowUpRight size={16} aria-hidden="true" /></button>
        <button ref={menuToggle} className="menu-toggle" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="main-navigation" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}</button></div>
    </div></header>
    <main id="main"><section className="hero" id="top" aria-labelledby="hero-title"><div className="hero-grid" aria-hidden="true" /><HeroMedia />
      <div className="container hero-content"><Reveal><p className="eyebrow"><span className="live-dot" />{c.hero.eyebrow}</p>
        <h1 id="hero-title">{c.hero.lines.map((line) => <span key={line}>{line}</span>)}<em>{c.hero.accent}</em></h1>
        <p className="hero-description">{c.hero.description}</p><div className="hero-actions"><a className="button button-mint" href="#evidence">{c.hero.primary}<ArrowDown size={17} aria-hidden="true" /></a>
          <button className="hero-secondary" onClick={() => setSetupOpen(true)}><Terminal size={17} aria-hidden="true" />{c.hero.secondary}<ArrowUpRight size={15} aria-hidden="true" /></button></div>
        <div className="hero-note"><ShieldCheck size={14} aria-hidden="true" />{c.hero.note}</div>
      </Reveal></div><div className="hero-bottom"><div className="container"><span>{c.ui.heroBottom}</span><a href="#evidence" aria-label="Scroll to synthetic evidence"><ArrowDown size={16} aria-hidden="true" /></a><span>{c.ui.scrollToInspect}</span></div></div>
    </section>
    <section className="proof-strip" aria-label="Verified project facts"><div className="container proof-grid">{c.proof.map((fact, index) => <Reveal className="proof-item" key={fact.label} delay={index * animation.staggerSeconds}>
      <strong>{fact.value}</strong><div><span>{fact.label}</span><p>{fact.detail}</p></div>
    </Reveal>)}</div></section>
    <EvidenceExplorer /><Workflow /><Approach />
    <section className="start-section section-pad" id="start" aria-labelledby="start-title"><div className="container start-layout"><Reveal><p className="eyebrow">{c.gettingStarted.eyebrow}</p><h2 id="start-title">{c.gettingStarted.heading}</h2>
      <p className="section-description">{c.gettingStarted.description}</p><div className="start-actions"><button className="button button-mint" onClick={() => setSetupOpen(true)}>{c.gettingStarted.button}<ArrowUpRight size={18} aria-hidden="true" /></button>
        <ArrowLink href={config.repositoryUrl} external>{c.gettingStarted.source}</ArrowLink></div><p className="start-note">{c.gettingStarted.note}</p></Reveal>
      <Reveal className="source-card"><div className="source-card-top"><Code2 size={27} aria-hidden="true" /><span>{c.ui.openSourceEngine}</span><ArrowUpRight size={22} aria-hidden="true" /></div>
        <div className="source-card-brand">{c.brand}<span>.</span></div><p>{c.tagline}</p><div className="source-card-bottom"><span className="language-dot" />{c.ui.sourceLanguage}<span>{c.ui.sourceLicense}</span><a href={config.repositoryUrl} target="_blank" rel="noopener noreferrer" aria-label="View VitalProbe source on GitHub"><ArrowRight size={22} aria-hidden="true" /></a></div></Reveal>
    </div></section>
    <section className="faq-section section-pad" aria-labelledby="faq-title"><div className="container faq-layout"><Reveal><p className="eyebrow">{c.faq.eyebrow}</p><h2 id="faq-title">{c.faq.heading}</h2></Reveal>
      <div className="faq-list">{c.faq.items.map((item) => <details className="faq-item" key={item.question}><summary>{item.question}<ChevronDown size={19} aria-hidden="true" /></summary><p>{item.answer}</p></details>)}</div>
    </div></section>
    </main>
    <footer className="site-footer"><div className="container"><div className="footer-top"><Brand /><p>{c.footer.description}</p><a href="#top" className="back-to-top">{c.footer.top}<ArrowUpRight size={17} aria-hidden="true" /></a></div>
      <div className="footer-statement" aria-hidden="true">{c.tagline}</div><div className="footer-bottom"><div><p className="footer-status"><span />{c.footer.status}</p><p className="footer-disclaimer">{c.footer.disclaimer}</p></div>
        <nav aria-label="Footer navigation"><ArrowLink href={config.repositoryUrl} external>{c.footer.source}</ArrowLink><ArrowLink href={config.releaseUrl} external>{c.footer.release}</ArrowLink><ArrowLink href={config.reportUrl}>{c.footer.report}</ArrowLink></nav></div>
      <div className="copyright">{c.footer.copyright}<span>{c.ui.footerMotto}</span></div>
    </div></footer>
    {setupOpen && <Quickstart onClose={() => setSetupOpen(false)} />}
  </>
}

export default function App() {
  const reduce = useReducedMotion()
  return <ReactLenis root options={{ autoRaf: true, lerp: animation.scrollLerp, smoothWheel: !reduce,
    anchors: { duration: reduce ? 0 : animation.anchorSeconds } }}><Experience /></ReactLenis>
}
