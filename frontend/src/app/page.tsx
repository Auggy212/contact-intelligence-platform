"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import {
  FileText, Shield, Zap, Scale, CheckCircle2,
  ArrowRight, ChevronRight, Brain, Users,
  FileSearch, AlertTriangle, Star,
} from "lucide-react"
import { isAuthenticated } from "@/lib/auth"

export default function LandingPage() {
  const router = useRouter()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/projects")
    } else {
      setChecked(true)
    }
  }, [router])

  if (!checked) return null

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-white overflow-x-hidden">

      {/* ── Navbar ──────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-white/5 bg-[#0a0f1e]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-lg tracking-tight">ContractIQ</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
            <a href="#use-cases" className="hover:text-white transition-colors">Use cases</a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/sign-in"
              className="text-sm text-slate-300 hover:text-white transition-colors px-4 py-2"
            >
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-24 px-6">
        {/* Glow orbs */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-40 left-1/4 w-[300px] h-[300px] bg-indigo-600/10 rounded-full blur-[80px] pointer-events-none" />
        <div className="absolute top-40 right-1/4 w-[300px] h-[300px] bg-violet-600/10 rounded-full blur-[80px] pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-medium mb-8">
            <Zap className="w-3 h-3" />
            AI-Powered Legal Contract Intelligence for India
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.08] mb-6">
            Review contracts{" "}
            <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-violet-400 bg-clip-text text-transparent">
              10× faster
            </span>
            <br />with AI precision
          </h1>

          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Upload your contracts, templates, and vendor drafts. ContractIQ
            automatically detects deviations, flags Indian law violations, and
            surfaces high-risk clauses — so your legal team can focus on what matters.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/sign-up"
              className="group inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-xl font-semibold text-base transition-all shadow-lg shadow-blue-600/25 hover:shadow-blue-500/40"
            >
              Start free trial
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 text-slate-300 hover:text-white px-8 py-3.5 rounded-xl font-medium text-base border border-white/10 hover:border-white/20 transition-all"
            >
              See how it works
              <ChevronRight className="w-4 h-4" />
            </a>
          </div>

          {/* Social proof */}
          <div className="mt-12 flex items-center justify-center gap-6 text-sm text-slate-500">
            <div className="flex items-center gap-1.5">
              <div className="flex">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                ))}
              </div>
              <span>Trusted by legal teams</span>
            </div>
            <div className="w-px h-4 bg-white/10" />
            <span>Indian Contract Act 1872 compliant checks</span>
            <div className="hidden sm:block w-px h-4 bg-white/10" />
            <span className="hidden sm:block">No API keys required for demo</span>
          </div>
        </div>

        {/* Hero Dashboard Preview */}
        <div className="relative max-w-5xl mx-auto mt-16">
          <div className="rounded-2xl border border-white/10 bg-slate-900/80 overflow-hidden shadow-2xl shadow-black/60 backdrop-blur">
            {/* Fake browser chrome */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5 bg-slate-950/50">
              <div className="w-3 h-3 rounded-full bg-red-500/70" />
              <div className="w-3 h-3 rounded-full bg-amber-500/70" />
              <div className="w-3 h-3 rounded-full bg-green-500/70" />
              <div className="flex-1 ml-2 h-5 bg-white/5 rounded-md max-w-xs text-[11px] text-slate-500 flex items-center px-3">
                contractiq.ai/projects
              </div>
            </div>
            {/* Fake dashboard content */}
            <div className="p-6 grid grid-cols-3 gap-4">
              {[
                { label: "Critical Issues", value: "3", color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
                { label: "High Risk Clauses", value: "7", color: "text-orange-400", bg: "bg-orange-500/10 border-orange-500/20" },
                { label: "Law Violations", value: "5", color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
              ].map((stat) => (
                <div key={stat.label} className={`rounded-xl border p-4 ${stat.bg}`}>
                  <p className="text-xs text-slate-400 mb-1">{stat.label}</p>
                  <p className={`text-3xl font-bold ${stat.color}`}>{stat.value}</p>
                </div>
              ))}
            </div>
            <div className="px-6 pb-6 space-y-2">
              {[
                { title: "Non-compete clause detected", sev: "HIGH", law: "ICA §27", color: "border-l-orange-500" },
                { title: "Payment terms exceed MSME 45-day limit", sev: "HIGH", law: "MSME §15", color: "border-l-orange-500" },
                { title: "No governing law clause detected", sev: "HIGH", law: "CPC 1908", color: "border-l-orange-500" },
                { title: "Liquidated damages clause present", sev: "MEDIUM", law: "ICA §74", color: "border-l-amber-500" },
                { title: "Arbitration statute name incorrect", sev: "LOW", law: "ACA 1996", color: "border-l-blue-500" },
              ].map((f, i) => (
                <div key={i} className={`flex items-center gap-3 p-3 rounded-lg bg-white/3 border-l-2 ${f.color} border border-white/5`}>
                  <AlertTriangle className="w-4 h-4 text-slate-400 shrink-0" />
                  <span className="text-sm text-slate-300 flex-1">{f.title}</span>
                  <span className="text-[10px] font-mono text-slate-500 bg-white/5 px-2 py-0.5 rounded">{f.law}</span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    f.sev === "HIGH" ? "bg-orange-500/20 text-orange-400" :
                    f.sev === "MEDIUM" ? "bg-amber-500/20 text-amber-400" :
                    "bg-blue-500/20 text-blue-400"
                  }`}>{f.sev}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Subtle gradient fade at bottom */}
          <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[#0a0f1e] to-transparent" />
        </div>
      </section>

      {/* ── Features ────────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything your legal team needs
            </h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              From first draft to final sign-off — ContractIQ covers every stage
              of your contract review workflow.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: FileSearch,
                title: "Template Comparison",
                description: "Instantly compare vendor drafts against your master template. Every deviation highlighted, every missing clause flagged.",
                color: "text-blue-400",
                bg: "bg-blue-500/10 border-blue-500/20",
              },
              {
                icon: Scale,
                title: "Indian Law Validation",
                description: "22 bundled rules covering ICA 1872, IT Act, MSME Act, CPA 2019, and Maharashtra Stamp Act. No legal database subscription needed.",
                color: "text-violet-400",
                bg: "bg-violet-500/10 border-violet-500/20",
              },
              {
                icon: Shield,
                title: "Vendor Redline Analysis",
                description: "Track every change the vendor made to your proposed draft. OOXML tracked-change detection plus AI-powered risk scoring.",
                color: "text-emerald-400",
                bg: "bg-emerald-500/10 border-emerald-500/20",
              },
              {
                icon: CheckCircle2,
                title: "Custom Checklist Rules",
                description: "Define your organisation's own playbook rules — payment caps, mandatory clauses, jurisdiction requirements — and run them automatically.",
                color: "text-amber-400",
                bg: "bg-amber-500/10 border-amber-500/20",
              },
              {
                icon: Brain,
                title: "Clause Library",
                description: "Approved clauses saved automatically. Build your organisation's knowledge base over time — searchable by category and content.",
                color: "text-pink-400",
                bg: "bg-pink-500/10 border-pink-500/20",
              },
              {
                icon: Users,
                title: "Team Collaboration",
                description: "Invite reviewers, assign roles (Admin / Reviewer / Viewer), and track every action with a full audit log.",
                color: "text-orange-400",
                bg: "bg-orange-500/10 border-orange-500/20",
              },
            ].map((f) => (
              <div
                key={f.title}
                className="group p-6 rounded-2xl border border-white/8 bg-white/3 hover:bg-white/5 hover:border-white/12 transition-all duration-300"
              >
                <div className={`inline-flex items-center justify-center w-10 h-10 rounded-xl border mb-4 ${f.bg}`}>
                  <f.icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-6 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-950/10 to-transparent pointer-events-none" />
        <div className="relative max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              From upload to insight in minutes
            </h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">
              Three files in, full legal analysis out — no manual review required.
            </p>
          </div>

          <div className="relative">
            {/* Connector line */}
            <div className="absolute left-[28px] top-12 bottom-12 w-px bg-gradient-to-b from-blue-600 via-indigo-600 to-violet-600 hidden md:block" />

            <div className="space-y-10">
              {[
                {
                  step: "01",
                  icon: FileText,
                  title: "Upload your documents",
                  description: "Upload up to three files: your master Template (A), the Proposed Draft (B), and the Vendor's Reply (C). Supports .docx and .pdf formats. Any filename, any structure.",
                  color: "bg-blue-600",
                },
                {
                  step: "02",
                  icon: Brain,
                  title: "Run AI analysis",
                  description: "Choose which analyses to run — Template Comparison, Vendor Diff, Indian Law Validation, Custom Checklist. Results are ready in seconds.",
                  color: "bg-indigo-600",
                },
                {
                  step: "03",
                  icon: AlertTriangle,
                  title: "Review findings",
                  description: "Every finding lists the exact clause, risk level (Critical / High / Medium / Low), the applicable Indian law section, and a clear recommendation.",
                  color: "bg-violet-600",
                },
                {
                  step: "04",
                  icon: CheckCircle2,
                  title: "Approve & export",
                  description: "Accept or reject each finding. Approved clauses go to your Clause Library. Export the full review as a PDF report for clients or management.",
                  color: "bg-purple-600",
                },
              ].map((s, i) => (
                <div key={i} className="flex gap-6 md:gap-8">
                  <div className={`flex-shrink-0 w-14 h-14 rounded-xl ${s.color} flex items-center justify-center shadow-lg z-10`}>
                    <s.icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="pt-1">
                    <div className="text-xs font-mono text-slate-500 mb-1">Step {s.step}</div>
                    <h3 className="text-xl font-semibold mb-2">{s.title}</h3>
                    <p className="text-slate-400 leading-relaxed max-w-lg">{s.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Use Cases ───────────────────────────────────────────────────── */}
      <section id="use-cases" className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Built for Indian legal practice</h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">
              Covering the statutes that matter most to commercial contracts in India.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              {
                title: "Corporate Legal Teams",
                points: [
                  "Review vendor MSAs against your standard template",
                  "Catch non-compete and IP assignment clauses early",
                  "Enforce payment terms compliant with MSME Act",
                ],
              },
              {
                title: "Law Firms & Consultants",
                points: [
                  "Deliver faster, more thorough reviews to clients",
                  "Build a reusable clause library across matters",
                  "Audit trail for every decision and approval",
                ],
              },
              {
                title: "Procurement & Finance",
                points: [
                  "Flag 90-day payment terms before signing",
                  "Detect liquidated damages and penalty clauses",
                  "Ensure stamp duty references for Maharashtra contracts",
                ],
              },
              {
                title: "Startups & SMEs",
                points: [
                  "Affordable alternative to expensive legal retainers",
                  "Plain-language recommendations on every risk",
                  "No legal expertise required to get started",
                ],
              },
            ].map((uc) => (
              <div key={uc.title} className="p-6 rounded-2xl border border-white/8 bg-white/3">
                <h3 className="font-semibold text-lg mb-4">{uc.title}</h3>
                <ul className="space-y-3">
                  {uc.points.map((p) => (
                    <li key={p} className="flex items-start gap-3 text-slate-400 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats bar ───────────────────────────────────────────────────── */}
      <section className="py-16 px-6 border-y border-white/5 bg-white/2">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { value: "22+", label: "Indian law rules" },
            { value: "4", label: "Analysis types" },
            { value: "< 30s", label: "Analysis time" },
            { value: "100%", label: "No API keys needed" },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                {s.value}
              </div>
              <div className="text-sm text-slate-400 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────────── */}
      <section className="py-28 px-6 relative">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[600px] h-[400px] bg-blue-600/8 rounded-full blur-[100px]" />
        </div>
        <div className="relative max-w-2xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Ready to review smarter?
          </h2>
          <p className="text-slate-400 text-lg mb-10">
            Create your account in seconds. No credit card, no API keys, no setup.
            Just upload a contract and see what the platform can do.
          </p>
          <Link
            href="/sign-up"
            className="group inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-10 py-4 rounded-xl font-semibold text-lg transition-all shadow-xl shadow-blue-600/30 hover:shadow-blue-500/40"
          >
            Create free account
            <ArrowRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <p className="mt-4 text-sm text-slate-500">
            Already have an account?{" "}
            <Link href="/sign-in" className="text-blue-400 hover:text-blue-300 transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-10 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-blue-600 flex items-center justify-center">
              <Scale className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold text-sm">ContractIQ</span>
          </div>
          <p className="text-xs text-slate-500">
            AI-powered contract intelligence for Indian law. Demo mode — no external API keys required.
          </p>
          <div className="flex items-center gap-6 text-xs text-slate-500">
            <span>© 2025 ContractIQ</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
