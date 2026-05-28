"use client"

import Link from "next/link"
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  FileCheck2,
  FileText,
  FolderOpen,
  Gavel,
  Library,
  LucideIcon,
  Play,
  Scale,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Users,
  Zap,
} from "lucide-react"
import { useScrollReveal, useStaggerReveal } from "@/hooks/use-scroll-reveal"

// ─── Data ────────────────────────────────────────────────────────────────────

const navigation = [
  { label: "Features", href: "#features" },
  { label: "Technology", href: "#platform" },
  { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
]

const trustedBy = [
  "Legalify", "LexCorp", "IndiaJuris", "ContractFlow",
  "LawSync", "VendorShield", "LexHub", "ClauseAI",
]

const features = [
  {
    title: "Supports Any Contract Format",
    description: "Upload DOCX or PDF — our parser handles templates, vendor drafts, and executed contracts without manual formatting.",
    icon: UploadCloud, color: "text-orange-400", bg: "bg-orange-500/10",
  },
  {
    title: "Automated Analysis Pipeline",
    description: "Trigger all four AI analysis tracks in parallel: template compare, vendor diff, law validation, and checklist — in one click.",
    icon: Zap, color: "text-amber-400", bg: "bg-amber-500/10",
  },
  {
    title: "Clause-Level Risk Findings",
    description: "Every risk is pinned to a specific clause with severity rating, law citation, and a recommended action — not just a summary.",
    icon: FileCheck2, color: "text-orange-400", bg: "bg-orange-500/10",
  },
  {
    title: "Real-Time Team Collaboration",
    description: "Reviewer, admin, and viewer roles work together in a shared project with a live audit trail of every action taken.",
    icon: Users, color: "text-amber-400", bg: "bg-amber-500/10",
  },
  {
    title: "Indian Law Validation",
    description: "Flags clauses that are unenforceable or non-compliant with Indian business statutes automatically.",
    icon: Gavel, color: "text-orange-400", bg: "bg-orange-500/10",
  },
  {
    title: "Semantic Clause Search",
    description: "Legal-domain embeddings find equivalent language without exact keywords — across your entire clause library.",
    icon: Library, color: "text-amber-400", bg: "bg-amber-500/10",
  },
]

const capabilities = [
  { title: "Template comparison", description: "Detects additions, deletions, and modified clauses against your standard.", icon: FolderOpen },
  { title: "Indian law validation", description: "Flags non-compliant language across core Indian business statutes.", icon: Gavel },
  { title: "Vendor redline intelligence", description: "Explains business impact of edits — payment terms, liability caps, jurisdiction.", icon: FileCheck2 },
  { title: "Clause library search", description: "Semantic search using legal-domain embeddings, no exact keywords needed.", icon: Library },
]

const plans = [
  {
    name: "Starter", price: "$49", per: "/month", tagline: "For first legal ops teams",
    features: ["25 contract reviews/month", "All 4 analysis types", "Team collaboration (5 seats)", "PDF export", "Email support"],
    cta: "Start a Project", highlighted: false,
  },
  {
    name: "Professional", price: "$120", per: "/month", tagline: "For growing review volume",
    features: ["100 contract reviews/month", "Unlimited team seats", "Custom checklist rules", "Dedicated account manager", "In-depth reporting", "Expedited support"],
    cta: "Start a Project", highlighted: true,
  },
  {
    name: "Enterprise", price: "$450", per: "/month", tagline: "For controlled legal operations",
    features: ["Custom pricing", "Everything in Pro", "Dedicated account manager", "Full API access", "Custom security & compliance"],
    cta: "Start a Project", highlighted: false,
  },
]

const faqs = [
  { q: "What is this platform used for?", a: "Contract Intelligence Platform helps legal and operations teams review, compare, and validate contracts using AI — cutting turnaround from days to minutes." },
  { q: "Is my contract data secure?", a: "Yes. Every organisation is isolated at the database level using PostgreSQL Row-Level Security. Clerk JWT auth enforces role and tenant context on every API request." },
  { q: "Can I review multiple contract types?", a: "Absolutely. The platform handles vendor MSAs, NDAs, employment agreements, and any DOCX or PDF contract format." },
  { q: "Does it work for Indian law compliance?", a: "Yes — Indian law validation is one of the four built-in AI tracks. It flags clauses that are unenforceable under Indian statutes automatically." },
  { q: "How quickly can I get started?", a: "Create an account, set up your workspace, and run your first contract review within 5 minutes — no integration or setup required." },
]

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const featuresRef = useStaggerReveal<HTMLDivElement>(90)
  const capabilitiesRef = useStaggerReveal<HTMLDivElement>(70)
  const pricingRef = useStaggerReveal<HTMLDivElement>(110)
  const faqRef = useStaggerReveal<HTMLDivElement>(60)
  const heroRef = useScrollReveal<HTMLDivElement>()

  return (
    <main className="min-h-screen bg-background text-white">

      {/* ── Ambient animated glows ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[600px] rounded-full bg-orange-600/15 blur-[160px] animate-float-slow" />
        <div className="absolute top-1/2 right-[-10%] w-[500px] h-[500px] rounded-full bg-orange-500/10 blur-[120px] animate-float" style={{ animationDelay: "-3s" }} />
        <div className="absolute bottom-0 left-[-5%] w-[400px] h-[400px] rounded-full bg-orange-700/8 blur-[100px] animate-float" style={{ animationDelay: "-5s" }} />
        {/* Subtle rotating ring */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full border border-orange-500/[0.06] animate-spin-slow" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full border border-orange-500/[0.04] animate-spin-slow" style={{ animationDirection: "reverse", animationDuration: "30s" }} />
      </div>

      {/* ── Header ── */}
      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-background/90 backdrop-blur-xl animate-fade-in">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-500 transition-transform group-hover:scale-110 group-hover:rotate-3">
              <FileText className="h-4 w-4 text-white" />
            </span>
            <span className="text-sm font-bold text-white tracking-tight">Contract Intel</span>
          </Link>

          <nav className="hidden items-center gap-7 md:flex">
            {navigation.map((item, i) => (
              <a key={item.href} href={item.href}
                className="text-sm font-medium text-zinc-400 transition-colors hover:text-white relative after:absolute after:bottom-0 after:left-0 after:h-px after:w-0 after:bg-orange-400 after:transition-all after:duration-300 hover:after:w-full"
                style={{ animationDelay: `${i * 50}ms` }}>
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/sign-in" className="hidden text-sm font-medium text-zinc-400 hover:text-white transition-colors sm:block px-3 py-2">
              Log In
            </Link>
            <Link href="/sign-up" className="btn-orange !py-2 !px-4 text-xs animate-glow-pulse">
              Sign Up
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative pt-20 pb-16 sm:pt-28 sm:pb-24" ref={heroRef}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-orange-500/20 bg-orange-500/8 px-4 py-1.5 text-xs font-semibold text-orange-400 tracking-wide animate-fade-up delay-100">
            <Sparkles className="h-3.5 w-3.5 animate-pulse-slow" />
            ✦ AI-Powered Legal Review Platform
          </div>

          <h1 className="mx-auto max-w-4xl text-5xl font-bold leading-tight tracking-tight text-white sm:text-6xl lg:text-7xl animate-fade-up delay-200">
            Contract Review That{" "}
            <span className="shimmer-text">Grows with</span>
            <br />
            Your Team
          </h1>

          <p className="mx-auto mt-7 max-w-2xl text-base leading-relaxed text-zinc-400 sm:text-lg animate-fade-up delay-300">
            Unlock AI-powered clause analysis, Indian law validation, and vendor redline intelligence — designed to support your legal ops team at every stage of review.
          </p>

          <div className="mt-9 flex flex-col items-center justify-center gap-4 sm:flex-row animate-fade-up delay-400">
            <Link href="/sign-up"
              className="btn-orange h-12 px-8 text-sm animate-glow-pulse hover:scale-105 active:scale-95 transition-transform">
              Get Started Free
            </Link>
            <Link href="/projects" className="btn-ghost h-12 px-8 text-sm group hover:scale-[1.02] active:scale-[0.98] transition-transform">
              <Play className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              Watch Demo
            </Link>
          </div>

          {/* Stats row */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-8 animate-fade-up delay-500">
            {[
              { value: "5 min", label: "Review cycle" },
              { value: "4 AI", label: "Analysis tracks" },
              { value: "RLS", label: "Tenant security" },
              { value: "99.9%", label: "Uptime SLA" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <p className="text-2xl font-bold text-white">{s.value}</p>
                <p className="text-xs text-zinc-600">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Dashboard mockup - floating */}
          <div className="relative mx-auto mt-14 max-w-5xl animate-fade-up delay-600">
            <div className="absolute inset-x-0 -top-6 h-24 bg-gradient-to-b from-orange-500/5 to-transparent blur-2xl" />
            {/* Floating glow rings behind mockup */}
            <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 mx-auto h-[120%] w-[70%] rounded-full bg-orange-500/5 blur-[80px] -z-10" />
            <div className="animate-float" style={{ animationDuration: "7s" }}>
              <DashboardMockup />
            </div>
          </div>
        </div>
      </section>

      {/* ── Trusted by – Marquee ── */}
      <section className="border-y border-white/[0.06] bg-background py-10 overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center mb-7">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-600">
            Trusted by 4,000+ Growing Companies
          </p>
        </div>
        <div className="marquee-track relative flex overflow-hidden">
          {/* duplicate for infinite scroll */}
          <div className="animate-marquee flex shrink-0 gap-14 items-center">
            {[...trustedBy, ...trustedBy].map((name, i) => (
              <span key={i} className="whitespace-nowrap text-base font-bold text-zinc-700 hover:text-zinc-400 transition-colors tracking-tight cursor-default">
                {name}
              </span>
            ))}
          </div>
          <div className="animate-marquee flex shrink-0 gap-14 items-center" aria-hidden="true">
            {[...trustedBy, ...trustedBy].map((name, i) => (
              <span key={i} className="whitespace-nowrap text-base font-bold text-zinc-700 tracking-tight">
                {name}
              </span>
            ))}
          </div>
          {/* Fade edges */}
          <div className="pointer-events-none absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-[#0d0d0d] to-transparent z-10" />
          <div className="pointer-events-none absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-[#0d0d0d] to-transparent z-10" />
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="py-24 overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            eyebrow="Platform"
            title={<>Contract Review for the<br />Modern Legal Team</>}
            description="Tailored AI tools to simplify review management, boost efficiency, and support your organisation's growth."
          />

          <div ref={featuresRef} className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <div key={f.title} className="reveal card-lift gradient-border">
                <FeatureCard {...f} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Capabilities ── */}
      <section id="platform" className="border-y border-white/[0.06] bg-background py-24 overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            eyebrow="Technology"
            title="Reimagined for the Future of Law"
            description="Trust us to deliver cutting-edge AI innovation, transparency, and personalised analysis, all designed to help you achieve operational legal freedom."
          />

          <div ref={capabilitiesRef} className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {capabilities.map((c) => (
              <div key={c.title} className="reveal card-lift group rounded-xl border border-white/[0.07] bg-[#14151A] p-6 transition-all hover:border-orange-500/30 hover:bg-[#14151A]">
                <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-orange-500/10 ring-1 ring-orange-500/20 group-hover:bg-orange-500/20 transition-all">
                  <c.icon className="h-5 w-5 text-orange-400" />
                </div>
                <h3 className="mb-2 text-sm font-bold text-white">{c.title}</h3>
                <p className="text-xs leading-relaxed text-zinc-500">{c.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="py-24 overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            eyebrow="Pricing"
            title={<>Flexible Plans for Every<br />Need and Budget</>}
            description="Choose the perfect plan to scale, save, and maximise value."
          />

          <div ref={pricingRef} className="grid gap-6 sm:grid-cols-3">
            {plans.map((plan) => (
              <div key={plan.name} className="reveal-scale card-lift">
                <PricingCard plan={plan} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="border-t border-white/[0.06] bg-background py-24 overflow-hidden">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <SectionHeader
            eyebrow="FAQ"
            title="Everything You Need to Know"
          />

          <div ref={faqRef} className="space-y-3">
            {faqs.map((faq, i) => (
              <div key={i} className="reveal">
                <FAQItem q={faq.q} a={faq.a} defaultOpen={i === 0} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Newsletter ── */}
      <section className="border-t border-white/[0.06] py-20 overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <NewsletterSection />
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-white/[0.06] bg-background py-14">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <Link href="/" className="mb-4 flex items-center gap-2 group w-fit">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-500 transition-transform group-hover:scale-110">
                  <FileText className="h-4 w-4 text-white" />
                </span>
                <span className="text-sm font-bold text-white">Contract Intel</span>
              </Link>
              <p className="max-w-xs text-sm leading-relaxed text-zinc-500">
                AI-powered contract review platform built for Indian legal ops teams.
              </p>
            </div>

            {[
              { label: "About", links: ["Premium Features", "Benefits", "How To Use", "Key Features", "Privacy Policy"] },
              { label: "Mobile App", links: ["How To Use", "Use App", "Blogs", "Submission", "Contact"] },
              { label: "All Pages", links: ["Home", "App", "Blog", "Key Store", "Contact"] },
            ].map((col) => (
              <div key={col.label}>
                <p className="mb-4 text-xs font-bold uppercase tracking-widest text-white">{col.label}</p>
                <ul className="space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l}>
                      <a href="#" className="text-sm text-zinc-500 hover:text-orange-400 transition-colors">{l}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-white/[0.06] pt-8 sm:flex-row">
            <p className="text-xs text-zinc-600">© 2026 Contract Intelligence Platform. All rights reserved.</p>
            <p className="text-xs text-zinc-600">Terms of Service</p>
          </div>
        </div>
      </footer>
    </main>
  )
}

// ─── Section Header ────────────────────────────────────────────────────────────

function SectionHeader({ eyebrow, title, description }: {
  eyebrow: string
  title: React.ReactNode
  description?: string
}) {
  const ref = useScrollReveal<HTMLDivElement>()
  return (
    <div ref={ref} className="mb-14 text-center">
      <div className="reveal">
        <p className="mb-3 text-xs font-bold uppercase tracking-widest text-orange-400">{eyebrow}</p>
      </div>
      <div className="reveal delay-100">
        <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">{title}</h2>
      </div>
      {description && (
        <div className="reveal delay-200">
          <p className="mx-auto mt-5 max-w-2xl text-base text-zinc-400">{description}</p>
        </div>
      )}
    </div>
  )
}

// ─── Feature Card ──────────────────────────────────────────────────────────────

function FeatureCard({ title, description, icon: Icon, color, bg }: {
  title: string; description: string; icon: LucideIcon; color: string; bg: string
}) {
  return (
    <div className="group card-dark-hover p-7 h-full">
      <div className={`mb-5 flex h-12 w-12 items-center justify-center rounded-2xl ${bg} ring-1 ring-white/[0.06] group-hover:ring-orange-500/20 group-hover:scale-110 transition-all duration-300`}>
        <Icon className={`h-6 w-6 ${color} group-hover:rotate-6 transition-transform duration-300`} />
      </div>
      <h3 className="mb-2 text-base font-bold text-white">{title}</h3>
      <p className="text-sm leading-relaxed text-zinc-500">{description}</p>
    </div>
  )
}

// ─── Pricing Card ──────────────────────────────────────────────────────────────

function PricingCard({ plan }: { plan: typeof plans[0] }) {
  return (
    <div className={`relative flex flex-col rounded-2xl border p-7 transition-all h-full ${
      plan.highlighted
        ? "border-orange-500/50 bg-[#14151A] animate-border-glow"
        : "border-white/[0.07] bg-[#111111] hover:border-white/[0.12]"
    }`}>
      {plan.highlighted && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="rounded-full bg-orange-500 px-4 py-1 text-xs font-bold text-white animate-glow-pulse">
            Most Popular
          </span>
        </div>
      )}

      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-1">{plan.tagline}</p>
        <h3 className="text-xl font-bold text-white mb-4">{plan.name}</h3>
        <div className="flex items-end gap-1">
          <span className="text-4xl font-bold text-white">{plan.price}</span>
          <span className="mb-1 text-sm text-zinc-500">{plan.per}</span>
        </div>
      </div>

      <Link href="/sign-up"
        className={`mb-7 flex h-11 items-center justify-center rounded-xl text-sm font-bold transition-all hover:scale-[1.02] active:scale-[0.98] ${
          plan.highlighted
            ? "bg-orange-500 text-white hover:bg-orange-400 animate-glow-pulse"
            : "border border-white/[0.1] bg-white/[0.04] text-white hover:border-orange-500/40 hover:bg-orange-500/8"
        }`}>
        {plan.cta}
      </Link>

      <ul className="flex-1 space-y-3">
        {plan.features.map((f, i) => (
          <li key={f} className="flex items-start gap-2.5 text-sm text-zinc-400"
            style={{ animationDelay: `${i * 60}ms` }}>
            <CheckCircle2 className="h-4 w-4 shrink-0 text-orange-400 mt-0.5" />
            {f}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── FAQ ──────────────────────────────────────────────────────────────────────

function FAQItem({ q, a, defaultOpen }: { q: string; a: string; defaultOpen?: boolean }) {
  return (
    <details className="group rounded-xl border border-white/[0.07] bg-[#111111] overflow-hidden transition-all hover:border-orange-500/20" open={defaultOpen}>
      <summary className="flex cursor-pointer items-center justify-between gap-4 p-5 text-sm font-semibold text-white list-none select-none">
        {q}
        <ChevronDown className="h-4 w-4 shrink-0 text-zinc-500 transition-transform duration-300 group-open:rotate-180 group-open:text-orange-400" />
      </summary>
      <div className="border-t border-white/[0.06] px-5 py-4">
        <p className="text-sm leading-relaxed text-zinc-400">{a}</p>
      </div>
    </details>
  )
}

// ─── Newsletter ───────────────────────────────────────────────────────────────

function NewsletterSection() {
  const ref = useScrollReveal<HTMLDivElement>()
  return (
    <div ref={ref}>
      <div className="reveal rounded-2xl border border-orange-500/15 bg-gradient-to-br from-orange-500/8 to-amber-500/5 p-10 text-center animate-border-glow">
        <p className="mb-1 text-xs font-bold uppercase tracking-widest text-orange-400">Stay Updated</p>
        <h2 className="mb-3 text-3xl font-bold text-white">Get Our News And Updates</h2>
        <p className="mx-auto mb-8 max-w-md text-sm text-zinc-400">
          By subscribing you agree to our <span className="text-orange-400 cursor-pointer hover:underline">Privacy Policy</span>
        </p>
        <form className="mx-auto flex max-w-md gap-2" onSubmit={(e) => e.preventDefault()}>
          <input type="email" placeholder="Enter your email" className="input-dark flex-1 rounded-lg" />
          <button type="submit" className="btn-orange shrink-0 rounded-lg px-5 py-2.5 text-sm hover:scale-[1.03] active:scale-[0.97]">
            Subscribe
          </button>
        </form>
      </div>
    </div>
  )
}

// ─── Dashboard Mockup ─────────────────────────────────────────────────────────

function DashboardMockup() {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl overflow-hidden ring-1 ring-white/[0.04]" style={{ boxShadow: "0 40px 100px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04)" }}>
      {/* Window bar */}
      <div className="flex h-10 items-center justify-between border-b border-white/[0.06] bg-background px-4">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500/60 hover:bg-red-500 transition-colors cursor-pointer" />
          <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/60 hover:bg-yellow-500 transition-colors cursor-pointer" />
          <span className="h-2.5 w-2.5 rounded-full bg-green-500/60 hover:bg-green-500 transition-colors cursor-pointer" />
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1 text-[10px] text-zinc-600">
          Contract Intel · Dashboard
        </div>
        <div className="flex items-center gap-2 text-[10px] text-zinc-500">
          <span className="h-2 w-2 rounded-full bg-orange-400 animate-pulse" />
          Live
        </div>
      </div>

      {/* Body */}
      <div className="flex h-[420px]">
        {/* Sidebar */}
        <div className="w-44 border-r border-white/[0.06] bg-background p-3 shrink-0">
          <div className="mb-5 flex items-center gap-2 px-1">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-orange-500">
              <FileText className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="text-xs font-bold text-white">Contract Intel</span>
          </div>
          {["Overview", "Activity", "Manage", "Program", "Account", "Reports"].map((item, i) => (
            <div key={item} className={`mb-1 rounded-md px-3 py-2 text-[11px] font-medium transition-all hover:scale-[1.02] ${
              i === 0 ? "bg-orange-500/15 text-orange-400 border border-orange-500/20" : "text-zinc-600 hover:text-zinc-400"
            }`}>
              {item}
            </div>
          ))}
        </div>

        {/* Main */}
        <div className="flex-1 p-5 overflow-hidden">
          <div className="mb-5 flex items-start justify-between">
            <div>
              <p className="text-xs text-zinc-500">Good morning,</p>
              <p className="text-sm font-bold text-white">Legal Ops Team</p>
              <p className="mt-1 text-[10px] text-zinc-600">Stay on top of your tasks, monitor progress, and track results.</p>
            </div>
            <div className="flex gap-2">
              <button className="rounded-lg bg-orange-500 px-3 py-1.5 text-[10px] font-bold text-white hover:bg-orange-400 transition-colors">⟳ Transfer</button>
              <button className="rounded-lg border border-white/[0.08] px-3 py-1.5 text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors">↗ Request</button>
            </div>
          </div>

          {/* Stats row */}
          <div className="mb-5 grid grid-cols-4 gap-3">
            {[
              { label: "Total Balance", value: "$689,372", change: "+12.5%" },
              { label: "Total Savings", value: "$950", change: "+3.2%" },
              { label: "Total Spending", value: "$700", change: "-1.8%" },
              { label: "Total Income", value: "$1,050", change: "+7.1%" },
            ].map((stat) => (
              <div key={stat.label} className="rounded-xl border border-white/[0.06] bg-[#14151A] p-3 hover:border-orange-500/15 transition-colors">
                <p className="mb-1 text-[9px] text-zinc-600">{stat.label}</p>
                <p className="text-sm font-bold text-white leading-tight">{stat.value}</p>
                <p className={`mt-0.5 text-[9px] font-semibold ${stat.change.startsWith("+") ? "text-emerald-400" : "text-red-400"}`}>{stat.change}</p>
              </div>
            ))}
          </div>

          {/* Chart + tasks */}
          <div className="flex gap-3">
            <div className="flex-1 rounded-xl border border-white/[0.06] bg-[#14151A] p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-[10px] font-semibold text-white">Risk Findings</p>
                <span className="text-[9px] text-zinc-600">24 clauses</span>
              </div>
              <div className="flex items-end gap-1 h-14">
                {[30, 55, 40, 75, 90, 60, 45, 80, 65, 50, 70, 85].map((h, i) => (
                  <div key={i} className="flex-1 rounded-sm transition-all hover:opacity-80"
                    style={{
                      height: `${h}%`,
                      backgroundColor: i % 3 === 0 ? "#f97316" : i % 3 === 1 ? "#2a2a2a" : "#1e1e1e",
                      animationDelay: `${i * 80}ms`,
                    }} />
                ))}
              </div>
            </div>
            <div className="w-36 rounded-xl border border-white/[0.06] bg-[#14151A] p-4">
              <p className="mb-3 text-[10px] font-semibold text-white">Analysis Tasks</p>
              <div className="space-y-2">
                {["Template compare", "Vendor diff", "Law validation", "Checklist"].map((t, i) => (
                  <div key={t} className="flex items-center gap-1.5 text-[9px] text-zinc-500" style={{ animationDelay: `${i * 100}ms` }}>
                    <CheckCircle2 className="h-3 w-3 text-orange-400 shrink-0" />
                    {t}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
