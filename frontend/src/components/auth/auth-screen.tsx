"use client"

import { FormEvent, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  ArrowRight,
  Building,
  CheckCircle2,
  Eye,
  EyeOff,
  FileCheck2,
  FileText,
  LockKeyhole,
  Mail,
  Phone,
  Scale,
  ShieldCheck,
  Sparkles,
  User,
  Zap,
} from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type AuthMode = "sign-in" | "sign-up" | "forgot-password"
type LoginMethod = "email" | "phone"

type AuthScreenProps = {
  mode: AuthMode
}

const copy = {
  "sign-in": {
    eyebrow: "Secure workspace access",
    title: "Welcome back",
    description: "Sign in to your Contract Intelligence workspace and continue reviewing.",
    submit: "Sign In",
    alternatePrompt: "New to Contract Intel?",
    alternateAction: "Create an account",
    alternateHref: "/sign-up",
  },
  "sign-up": {
    eyebrow: "Create your workspace",
    title: "Get started today",
    description: "Set up your AI-powered legal review workspace in under 2 minutes.",
    submit: "Create Account",
    alternatePrompt: "Already have an account?",
    alternateAction: "Sign in",
    alternateHref: "/sign-in",
  },
  "forgot-password": {
    eyebrow: "Account recovery",
    title: "Reset your password",
    description: "Enter your email and we'll send you a secure reset link instantly.",
    submit: "Send Reset Link",
    alternatePrompt: "Remembered your password?",
    alternateAction: "Back to sign in",
    alternateHref: "/sign-in",
  },
} satisfies Record<
  AuthMode,
  { eyebrow: string; title: string; description: string; submit: string; alternatePrompt: string; alternateAction: string; alternateHref: string }
>

const leftStats = [
  { value: "5 min", label: "Review cycle" },
  { value: "4 AI", label: "Analysis tracks" },
  { value: "RLS", label: "Tenant security" },
]

export function AuthScreen({ mode }: AuthScreenProps) {
  const router = useRouter()
  const [showPassword, setShowPassword] = useState(false)
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [loginMethod, setLoginMethod] = useState<LoginMethod>("email")
  const [phoneStep, setPhoneStep] = useState<"input" | "otp">("input")
  const [otp, setOtp] = useState(["", "", "", "", "", ""])
  const content = copy[mode]
  const isSignUp = mode === "sign-up"
  const isReset = mode === "forgot-password"

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (loginMethod === "phone" && phoneStep === "input") { setPhoneStep("otp"); return }
    router.push(isReset ? "/sign-in" : "/projects")
  }

  function handleSocialLogin() { router.push("/projects") }

  function handleOtpChange(index: number, value: string) {
    if (value.length > 1) return
    const next = [...otp]; next[index] = value; setOtp(next)
    if (value && index < 5) document.getElementById(`otp-${index + 1}`)?.focus()
  }
  function handleOtpKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && !otp[index] && index > 0) document.getElementById(`otp-${index - 1}`)?.focus()
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-background animate-fade-in">
      {/* Ambient */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 left-1/4 h-[500px] w-[500px] rounded-full bg-orange-600/15 blur-[120px] animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 h-[400px] w-[400px] rounded-full bg-orange-500/10 blur-[100px] animate-pulse-slow delay-300" />
        <div className="absolute inset-0 opacity-[0.02]"
          style={{ backgroundImage: `linear-gradient(rgba(255,69,0,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,69,0,0.3) 1px, transparent 1px)`, backgroundSize: "60px 60px" }} />
      </div>

      <div className="relative z-10 grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">

        {/* ── Left Panel ── */}
        <section className="relative hidden flex-col justify-between overflow-hidden border-r border-white/[0.06] p-10 lg:flex xl:p-14 animate-slide-left">
          <div className="absolute inset-0" style={{ backgroundImage: "url('/auth-bg.png')", backgroundSize: "cover", backgroundPosition: "center", opacity: 0.12 }} />
          <div className="absolute inset-0 bg-gradient-to-br from-background/80 via-[#121417]/70 to-background/90" />

          {/* Logo */}
          <div className="relative z-10 flex items-center gap-2.5 animate-fade-in delay-200">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500 transition-transform duration-300 hover:rotate-12">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <div>
              <span className="block text-sm font-bold text-white">Contract Intel</span>
              <span className="block text-xs text-zinc-500">AI Legal Review Platform</span>
            </div>
          </div>

          {/* Headline */}
          <div className="relative z-10">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-orange-500/25 bg-orange-500/8 px-3 py-1.5 text-xs font-semibold text-orange-400 animate-fade-in delay-300">
              <Sparkles className="h-3.5 w-3.5" />
              AI-Powered Contract Analysis
            </div>
            <h2 className="max-w-lg text-4xl font-bold leading-tight tracking-tight text-white xl:text-5xl animate-fade-up delay-400">
              Review contracts in{" "}
              <span className="bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">
                minutes,
              </span>
              {" "}not hours.
            </h2>
            <p className="mt-5 max-w-md text-base leading-relaxed text-zinc-400 animate-fade-up delay-500">
              Clause-level risk detection, Indian law validation, vendor redline intelligence, and export-ready reports — all in one platform.
            </p>

            {/* Product card */}
            <div className="mt-10 rounded-2xl border border-white/[0.07] bg-white/[0.03] p-5 backdrop-blur-xl animate-scale-in delay-600 animate-float">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-500/15">
                    <FileCheck2 className="h-4 w-4 text-orange-400" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">Vendor MSA Review</p>
                    <p className="text-xs text-zinc-500">Clause-level risk · Indian law</p>
                  </div>
                </div>
                <span className="rounded-full bg-orange-500/15 px-3 py-1 text-xs font-semibold text-orange-400 ring-1 ring-orange-500/25 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-orange-500 animate-pulse" />
                  Live
                </span>
              </div>

              <div className="mt-4 space-y-2">
                {["Template comparison", "Vendor diff analysis", "Indian law validation", "Checklist validation"].map((task) => (
                  <div key={task} className="flex items-center gap-3 rounded-lg bg-white/[0.03] px-3 py-2 transition-all hover:bg-white/[0.06] hover:translate-x-1 duration-200">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-orange-400" />
                    <span className="text-xs text-zinc-400">{task}</span>
                  </div>
                ))}
              </div>

              <div className="mt-4 rounded-xl bg-gradient-to-r from-orange-500/15 to-amber-500/10 p-4 ring-1 ring-orange-500/15 transition-all hover:glow-orange-sm duration-300">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-orange-400 animate-pulse" />
                  <p className="text-sm font-bold text-white">24 findings · 5 critical risks</p>
                </div>
                <p className="mt-1.5 text-xs text-orange-300/70">
                  Risk citations, reviewer notes, and recommended actions exported.
                </p>
              </div>
            </div>

            {/* Stats */}
            <div className="mt-8 grid grid-cols-3 gap-4 animate-fade-up delay-700">
              {leftStats.map((stat) => (
                <div key={stat.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-center transition-all hover:border-orange-500/20 hover:bg-white/[0.04] duration-300">
                  <p className="text-xl font-bold text-white">{stat.value}</p>
                  <p className="mt-1 text-xs text-zinc-600">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Trust badges */}
          <div className="relative z-10 flex flex-wrap gap-3 animate-fade-in delay-800">
            {[
              { icon: ShieldCheck, label: "Bank-grade security" },
              { icon: Scale, label: "Indian law compliant" },
              { icon: FileCheck2, label: "Audit-ready" },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-zinc-500 transition-all hover:text-zinc-300 hover:border-white/[0.12] duration-300 cursor-default">
                <Icon className="h-3.5 w-3.5 text-orange-400" />
                {label}
              </div>
            ))}
          </div>
        </section>

        {/* ── Right Panel ── */}
        <section className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6 lg:px-10 animate-slide-right">
          <div className="w-full max-w-md">
            {/* Mobile logo */}
            <div className="mb-8 flex items-center justify-between lg:hidden animate-fade-in">
              <Link href="/" className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-orange-500">
                  <FileText className="h-4 w-4 text-white" />
                </div>
                <span className="text-sm font-bold text-white">Contract Intel</span>
              </Link>
              <Link href="/" className="text-xs text-zinc-500 hover:text-white transition-colors">Home →</Link>
            </div>

            {/* Form card */}
            <div className="rounded-2xl border border-white/[0.07] bg-[#111111] p-7 shadow-2xl sm:p-8 animate-scale-in delay-100 hover:border-orange-500/10 transition-all duration-300">

              {/* Header */}
              <div className="mb-7 animate-fade-up delay-200">
                <div className="mb-3 flex items-center gap-2">
                  <span className="h-1 w-5 rounded-full bg-orange-500 animate-pulse-slow" />
                  <span className="text-xs font-bold uppercase tracking-widest text-orange-400">{content.eyebrow}</span>
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">{content.title}</h1>
                <p className="mt-2 text-sm leading-relaxed text-zinc-400">{content.description}</p>
              </div>

              {/* Social logins */}
              {!isReset && (
                <>
                  <div className="grid gap-3 sm:grid-cols-2 animate-fade-up delay-300">
                    {/* Google */}
                    <button id="google-login-btn" type="button" onClick={handleSocialLogin}
                      className="flex h-11 items-center justify-center gap-2.5 rounded-xl border border-white/[0.08] bg-white/[0.04] text-sm font-medium text-zinc-300 transition-all hover:border-white/[0.15] hover:bg-white/[0.07] hover:text-white active:scale-[0.98]">
                      <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                      </svg>
                      Google
                    </button>

                    {/* Apple */}
                    <button id="apple-login-btn" type="button" onClick={handleSocialLogin}
                      className="flex h-11 items-center justify-center gap-2.5 rounded-xl border border-white/[0.08] bg-white/[0.04] text-sm font-medium text-zinc-300 transition-all hover:border-white/[0.15] hover:bg-white/[0.07] hover:text-white active:scale-[0.98]">
                      <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11" />
                      </svg>
                      Apple
                    </button>
                  </div>

                  {/* Divider */}
                  <div className="my-5 flex items-center gap-3 animate-fade-in delay-400">
                    <div className="h-px flex-1 bg-white/[0.06]" />
                    <span className="text-xs uppercase tracking-widest text-zinc-600">or</span>
                    <div className="h-px flex-1 bg-white/[0.06]" />
                  </div>

                  {/* Email / Phone toggle */}
                  <div className="mb-5 flex rounded-xl border border-white/[0.07] bg-white/[0.03] p-1 animate-fade-up delay-400">
                    {(["email", "phone"] as LoginMethod[]).map((method) => (
                      <button key={method} type="button" id={`${method}-method-btn`}
                        onClick={() => { setLoginMethod(method); setPhoneStep("input") }}
                        className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition-all ${
                          loginMethod === method
                            ? "bg-orange-500 text-white shadow-lg shadow-orange-500/20"
                            : "text-zinc-500 hover:text-zinc-300"
                        }`}>
                        {method === "email" ? <Mail className="h-4 w-4" /> : <Phone className="h-4 w-4" />}
                        {method === "email" ? "Email" : "Phone"}
                      </button>
                    ))}
                  </div>
                </>
              )}

              {/* Form */}
              <form className="space-y-4 animate-fade-up delay-500" onSubmit={handleSubmit}>

                {/* Phone flow */}
                {loginMethod === "phone" && !isReset ? (
                  phoneStep === "input" ? (
                    <div className="space-y-4">
                      <div className="grid gap-2">
                        <Label className="text-sm font-medium text-zinc-300">Phone number</Label>
                        <div className="flex gap-2">
                          <div className="flex h-11 w-16 items-center justify-center rounded-xl border border-white/[0.08] bg-[#1C1E26] text-sm font-bold text-zinc-300">+91</div>
                          <div className="relative flex-1">
                            <Phone className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                            <input id="phone" name="phone" type="tel" inputMode="numeric" pattern="[0-9]{10}" maxLength={10}
                              placeholder="98XXXXXXXX" required
                              className="h-11 w-full rounded-xl border border-white/[0.08] bg-[#1C1E26] pl-10 pr-4 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-orange-500/60 focus:ring-2 focus:ring-orange-500/15" />
                          </div>
                        </div>
                      </div>
                      <button type="submit" id="send-otp-btn"
                        className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-orange-500 text-sm font-bold text-white transition-all hover:bg-orange-400 active:scale-[0.98] shadow-lg shadow-orange-500/20 animate-glow-pulse">
                        Send OTP <ArrowRight className="h-4 w-4 animate-pulse" />
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="grid gap-3">
                        <Label className="text-sm font-medium text-zinc-300">Enter the 6-digit OTP sent to your phone</Label>
                        <div className="flex justify-between gap-2">
                          {otp.map((digit, i) => (
                            <input key={i} id={`otp-${i}`} type="text" inputMode="numeric" pattern="[0-9]" maxLength={1}
                              value={digit} onChange={(e) => handleOtpChange(i, e.target.value)} onKeyDown={(e) => handleOtpKeyDown(i, e)}
                              className="h-12 w-full rounded-xl border border-white/[0.08] bg-[#1C1E26] text-center text-lg font-bold text-white outline-none transition-all focus:border-orange-500/60 focus:ring-2 focus:ring-orange-500/15" />
                          ))}
                        </div>
                        <button type="button" onClick={() => setPhoneStep("input")} className="text-xs text-orange-400 hover:text-orange-300 transition-colors text-left">← Change number</button>
                      </div>
                      <button type="submit" id="verify-otp-btn"
                        className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-orange-500 text-sm font-bold text-white transition-all hover:bg-orange-400 active:scale-[0.98] shadow-lg shadow-orange-500/20 animate-glow-pulse">
                        Verify & Continue <ArrowRight className="h-4 w-4 animate-pulse" />
                      </button>
                    </div>
                  )
                ) : (
                  /* Email flow */
                  <>
                    {isSignUp && (
                      <div className="grid gap-2 transition-all duration-300">
                        <Label htmlFor="name" className="text-sm font-medium text-zinc-300">Full name</Label>
                        <div className="relative">
                          <User className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                          <Input id="name" name="name" autoComplete="name" placeholder="Aarav Mehta"
                            className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] pl-10 text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-orange-500/15" required />
                        </div>
                      </div>
                    )}
                    {isSignUp && (
                      <div className="grid gap-2 transition-all duration-300">
                        <Label htmlFor="organization" className="text-sm font-medium text-zinc-300">Organisation</Label>
                        <div className="relative">
                          <Building className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                          <Input id="organization" name="organization" autoComplete="organization" placeholder="Acme Legal Ops"
                            className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] pl-10 text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-orange-500/15" required />
                        </div>
                      </div>
                    )}

                    <div className="grid gap-2">
                      <Label htmlFor="email" className="text-sm font-medium text-zinc-300">{isReset ? "Email address" : "Work email"}</Label>
                      <div className="relative">
                        <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                        <Input id="email" name="email" type="email" autoComplete="email" placeholder="you@company.com"
                          className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] pl-10 text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-orange-500/15" required />
                      </div>
                    </div>

                    {!isReset && (
                      <div className="grid gap-2 animate-fade-in duration-200">
                        <div className="flex items-center justify-between">
                          <Label htmlFor="password" className="text-sm font-medium text-zinc-300">Password</Label>
                          {!isSignUp && (
                            <Link href="/forgot-password" className="text-xs font-medium text-orange-400 hover:text-orange-300 transition-colors">
                              Forgot password?
                            </Link>
                          )}
                        </div>
                        <div className="relative">
                          <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                          <Input id="password" name="password"
                            type={showPassword ? "text" : "password"}
                            autoComplete={isSignUp ? "new-password" : "current-password"}
                            placeholder={isSignUp ? "Create a strong password" : "Enter your password"}
                            className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] pl-10 pr-11 text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-orange-500/15"
                            required minLength={8} />
                          <button type="button" onClick={() => setShowPassword((v) => !v)}
                            className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-zinc-600 hover:bg-white/[0.06] hover:text-zinc-300 transition-all"
                            aria-label={showPassword ? "Hide password" : "Show password"}>
                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                      </div>
                    )}

                    {!isReset && (
                      <label className="flex cursor-pointer items-start gap-2.5 text-sm text-zinc-500 select-none">
                        <Checkbox
                          className="mt-0.5 border-white/[0.15] data-[state=checked]:border-orange-500 data-[state=checked]:bg-orange-500 transition-all"
                          checked={isSignUp ? acceptedTerms : rememberMe}
                          onCheckedChange={(c) => isSignUp ? setAcceptedTerms(c === true) : setRememberMe(c === true)}
                        />
                        <span className="transition-colors hover:text-zinc-400">
                          {isSignUp ? <>I agree to the <span className="text-orange-400 font-medium">workspace terms</span> and secure document processing.</> : "Keep me signed in on this device."}
                        </span>
                      </label>
                    )}

                    <button type="submit" id="auth-submit-btn"
                      disabled={isSignUp && !acceptedTerms}
                      className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-orange-500 text-sm font-bold text-white transition-all hover:bg-orange-400 active:scale-[0.98] shadow-lg shadow-orange-500/20 disabled:cursor-not-allowed disabled:opacity-40 animate-glow-pulse">
                      {content.submit}
                      <ArrowRight className="h-4 w-4 animate-pulse" />
                    </button>
                  </>
                )}
              </form>

              {/* Alternate */}
              <p className="mt-6 text-center text-sm text-zinc-500 animate-fade-in delay-600">
                {content.alternatePrompt}{" "}
                <Link href={content.alternateHref} className="font-semibold text-orange-400 hover:text-orange-300 transition-colors">
                  {content.alternateAction}
                </Link>
              </p>

              {/* Security */}
              <div className="mt-5 flex items-center justify-center gap-1.5 text-xs text-zinc-700 animate-fade-in delay-700">
                <ShieldCheck className="h-3.5 w-3.5 text-orange-500/60" />
                256-bit encryption · SOC 2 compliant
              </div>
            </div>

            {/* Back to home */}
            <div className="mt-5 hidden items-center justify-center lg:flex animate-fade-in delay-800">
              <Link href="/" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Back to home</Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}
