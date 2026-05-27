"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Scale, Eye, EyeOff, Loader2 } from "lucide-react"
import { saveSession } from "@/lib/auth"

export default function SignInPage() {
  const router = useRouter()
  const [form, setForm] = useState({ email: "", password: "" })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.email.includes("@")) { setError("Please enter a valid email address."); return }
    if (!form.password) { setError("Please enter your password."); return }
    setError("")
    setLoading(true)
    await new Promise((r) => setTimeout(r, 500))
    // In demo mode: any valid-looking email + any password is accepted.
    // Derive a display name from the email local part.
    const localPart = form.email.split("@")[0]
    const displayName = localPart
      .replace(/[._-]/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
    saveSession(displayName, form.email)
    router.replace("/projects")
  }

  return (
    <div className="min-h-screen bg-[#0a0f1e] flex">
      {/* ── Left panel: branding ── */}
      <div className="hidden lg:flex flex-col justify-between w-[480px] shrink-0 p-12 border-r border-white/5 bg-gradient-to-b from-[#0d1428] to-[#0a0f1e]">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
            <Scale className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-lg text-white">ContractIQ</span>
        </Link>

        <div>
          <blockquote className="text-2xl font-medium text-white leading-relaxed mb-6">
            &ldquo;ContractIQ caught a non-compete clause buried in Section 6 that we would have missed entirely.&rdquo;
          </blockquote>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white text-sm font-semibold">
              AK
            </div>
            <div>
              <p className="text-sm font-medium text-white">Agastya Kumar</p>
              <p className="text-xs text-slate-400">Senior Legal Counsel, TechCorp India</p>
            </div>
          </div>
        </div>

        <p className="text-xs text-slate-600">
          Demo mode · No API keys required · © 2025 ContractIQ
        </p>
      </div>

      {/* ── Right panel: form ── */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <Link href="/" className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-white">ContractIQ</span>
          </Link>

          <h1 className="text-2xl font-bold text-white mb-1">Welcome back</h1>
          <p className="text-slate-400 text-sm mb-8">
            Don&apos;t have an account?{" "}
            <Link href="/sign-up" className="text-blue-400 hover:text-blue-300 transition-colors">
              Sign up free
            </Link>
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
              />
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm font-medium text-slate-300">
                  Password
                </label>
                <span className="text-xs text-slate-500">
                  (any password works in demo mode)
                </span>
              </div>
              <div className="relative">
                <input
                  type={showPass ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 pr-11 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            {/* Demo notice */}
            <div className="text-xs text-slate-500 bg-white/3 border border-white/8 rounded-lg px-4 py-3">
              <span className="text-blue-400 font-medium">Demo mode:</span> Enter any email and password to sign in. Your session is stored locally.
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
