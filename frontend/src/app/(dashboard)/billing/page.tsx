"use client"

import { useSearchParams } from "next/navigation"
import { useEffect, Suspense } from "react"
import { useSubscription, useUsage, useCheckout, useBillingPortal } from "@/lib/hooks/use-billing"
import { PageHeader } from "@/components/shared/page-header"
import { PLAN_LIMITS } from "@/lib/types/api"
import type { SubscriptionPlan } from "@/lib/types/api"
import {
  AlertTriangle, ArrowRight, CheckCircle2, CreditCard, HardDrive,
  Loader2, TrendingUp, Zap,
} from "lucide-react"
import { toast } from "sonner"
import { formatBytes, formatNumber } from "@/lib/utils"
import { useStaggerReveal } from "@/hooks/use-scroll-reveal"

const STATUS_CONFIG = {
  active:   { label: "Active",   className: "bg-emerald-500/12 text-emerald-400 border-emerald-500/20" },
  trialing: { label: "Trial",    className: "bg-orange-500/12 text-orange-400 border-orange-500/20" },
  past_due: { label: "Past Due", className: "bg-red-500/12 text-red-400 border-red-500/20 animate-pulse" },
  canceled: { label: "Canceled", className: "bg-zinc-800 text-zinc-500 border-zinc-700" },
} as const

const PLAN_FEATURES: Record<SubscriptionPlan, string[]> = {
  trial:        ["3 contract reviews", "All 4 analysis types", "Clause library", "PDF export"],
  starter:      ["25 contract reviews/month", "All analysis types", "Team collaboration (5 seats)", "Priority support"],
  professional: ["100 contract reviews/month", "Unlimited team seats", "Custom checklist rules", "Dedicated account manager"],
  enterprise:   ["Unlimited contracts", "Custom SLAs", "On-premise option", "Custom integrations"],
}

function ProgressBar({ value, max, colorClass }: { value: number; max: number | null; colorClass: string }) {
  const percent = max == null ? 0 : Math.min(100, (value / max) * 100)
  return (
    <div className="h-1.5 rounded-full overflow-hidden bg-white/[0.06]">
      <div className={`h-full rounded-full transition-all duration-1000 ease-out ${colorClass}`} style={{ width: max == null ? "0%" : `${percent}%` }} />
    </div>
  )
}

function BillingContent() {
  const { data: subscription, isLoading: loadingSub } = useSubscription()
  const { data: usage, isLoading: loadingUsage } = useUsage()
  const { mutate: checkout, isPending: checkingOut } = useCheckout()
  const { mutate: openPortal, isPending: openingPortal } = useBillingPortal()
  const searchParams = useSearchParams()
  
  const leftRevealRef = useStaggerReveal(65)
  const rightRevealRef = useStaggerReveal(50)

  useEffect(() => {
    if (searchParams.get("success") === "1") toast.success("Subscription updated successfully!")
    if (searchParams.get("canceled") === "1") toast.info("Checkout canceled — no changes made.")
    if (searchParams.get("demo") === "1") {
      const plan = searchParams.get("plan")
      const isPortal = searchParams.get("portal") === "1"
      if (isPortal) {
        toast.info("Billing portal requires Stripe — will be enabled when keys are configured.")
      } else {
        toast.info(`Stripe checkout for "${plan}" plan will be enabled when Stripe keys are configured.`)
      }
    }
  }, [searchParams])

  const currentPlan = subscription?.plan ?? "trial"
  const currentUsage = usage?.[0]
  const planLimit = PLAN_LIMITS[currentPlan]
  const contractsUsed = currentUsage?.contracts_processed ?? 0
  const contractLimit = planLimit.contracts
  const contractPercent = contractLimit ? Math.round((contractsUsed / contractLimit) * 100) : 0
  const isNearLimit = contractLimit != null && contractPercent >= 80

  const trialDaysLeft = subscription?.trial_end
    ? Math.max(0, Math.ceil((new Date(subscription.trial_end).getTime() - Date.now()) / 86_400_000))
    : null

  const UPGRADE_PLANS: SubscriptionPlan[] = ["starter", "professional", "enterprise"]

  return (
    <div>
      <div className="animate-fade-up">
        <PageHeader
          title="Billing & Usage"
          description="Manage your subscription, usage, and payment details"
          action={
            currentPlan !== "trial" ? (
              <button
                onClick={() => openPortal()}
                disabled={openingPortal}
                className="flex h-10 items-center gap-2 rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 text-sm font-medium text-zinc-300 transition-all hover:border-orange-500/30 hover:text-orange-400 disabled:opacity-50 hover:scale-[1.02] active:scale-[0.98]"
              >
                {openingPortal ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}
                Manage Billing
              </button>
            ) : undefined
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* ── Left: Current plan + usage ── */}
        <div ref={leftRevealRef} className="space-y-5 lg:col-span-2">

          {/* Current plan card */}
          <div className="rounded-2xl border border-white/[0.07] bg-[#111111] p-6 reveal transition-all duration-300 hover:border-white/[0.12]">
            <div className="mb-5 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-zinc-600">Current Plan</p>
                <p className="mt-1 text-sm text-zinc-500">Your organisation&apos;s active subscription</p>
              </div>
              {subscription && (
                <span className={`rounded-full border px-3 py-1 text-xs font-bold transition-all duration-300 hover:scale-105 ${STATUS_CONFIG[subscription.status].className}`}>
                  {STATUS_CONFIG[subscription.status].label}
                </span>
              )}
            </div>

            {loadingSub ? (
              <div className="space-y-3">
                <div className="h-10 w-48 animate-pulse rounded-xl bg-white/[0.04]" />
                <div className="h-4 w-64 animate-pulse rounded-lg bg-white/[0.03]" />
              </div>
            ) : (
              <>
                <div className="flex items-end gap-3 animate-fade-in">
                  <span className="text-4xl font-bold text-white">{planLimit.label}</span>
                  <span className="mb-1 text-lg text-zinc-600">{planLimit.price}</span>
                </div>

                {trialDaysLeft != null && (
                  <div className="mt-4 flex items-center gap-2.5 rounded-xl border border-orange-500/20 bg-orange-500/8 p-4 text-sm text-orange-300 animate-glow-pulse">
                    <AlertTriangle className="h-4 w-4 shrink-0 animate-bounce" />
                    <span>Trial ends in <strong>{trialDaysLeft} day{trialDaysLeft !== 1 ? "s" : ""}</strong> — upgrade to keep your data.</span>
                  </div>
                )}

                {subscription?.current_period_end && (
                  <p className="mt-3 text-xs text-zinc-600 animate-fade-in delay-100">
                    Current period ends{" "}
                    <span className="font-semibold text-zinc-400">
                      {new Date(subscription.current_period_end).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
                    </span>
                  </p>
                )}
              </>
            )}
          </div>

          {/* Usage card */}
          <div className="rounded-2xl border border-white/[0.07] bg-[#111111] p-6 reveal transition-all duration-300 hover:border-white/[0.12]">
            <p className="mb-6 text-xs font-bold uppercase tracking-widest text-zinc-600">Usage This Period</p>

            {loadingUsage ? (
              <div className="space-y-5">
                {[1, 2, 3].map((i) => <div key={i} className="h-12 animate-pulse rounded-xl bg-white/[0.04]" />)}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Contracts */}
                <div className="space-y-2.5 transition-all hover:translate-x-1 duration-200">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-orange-500/12 group-hover:scale-110 transition-all duration-200">
                        <TrendingUp className="h-3.5 w-3.5 text-orange-400" />
                      </div>
                      <span className="font-semibold text-white">Contracts Processed</span>
                    </div>
                    <span className={`font-bold ${isNearLimit ? "text-orange-400 animate-pulse" : "text-white"}`}>
                      {contractsUsed}
                      {contractLimit != null && <span className="font-normal text-zinc-600"> / {contractLimit}</span>}
                      {contractLimit == null && <span className="font-normal text-zinc-600"> (unlimited)</span>}
                    </span>
                  </div>
                  <ProgressBar
                    value={contractsUsed}
                    max={contractLimit}
                    colorClass={contractPercent >= 90 ? "bg-red-500" : contractPercent >= 70 ? "bg-orange-500 animate-pulse" : "bg-orange-400"}
                  />
                  {isNearLimit && contractLimit != null && (
                    <p className="text-xs text-orange-400 animate-pulse">80%+ of limit used — consider upgrading to prevent interruption</p>
                  )}
                </div>

                {/* AI Tokens */}
                <div className="space-y-2.5 transition-all hover:translate-x-1 duration-200">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/12">
                        <Zap className="h-3.5 w-3.5 text-amber-400" />
                      </div>
                      <span className="font-semibold text-white">AI Tokens Used</span>
                    </div>
                    <span className="font-bold text-white">{formatNumber(currentUsage?.ai_tokens_used ?? 0)}</span>
                  </div>
                  <ProgressBar
                    value={1}
                    max={1}
                    colorClass="bg-amber-400"
                  />
                </div>

                {/* Storage */}
                <div className="space-y-2.5 transition-all hover:translate-x-1 duration-200">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-zinc-800">
                        <HardDrive className="h-3.5 w-3.5 text-zinc-500" />
                      </div>
                      <span className="font-semibold text-white">Storage Used</span>
                    </div>
                    <span className="font-bold text-white">{formatBytes(currentUsage?.storage_bytes_used ?? 0)}</span>
                  </div>
                  <ProgressBar
                    value={1}
                    max={1}
                    colorClass="bg-zinc-600"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Plan comparison ── */}
        <div ref={rightRevealRef} className="space-y-4">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-600">Available Plans</p>

          {UPGRADE_PLANS.map((plan) => {
            const config = PLAN_LIMITS[plan]
            const isCurrent = plan === currentPlan
            const features = PLAN_FEATURES[plan]

            return (
              <div
                key={plan}
                className={`relative rounded-2xl border p-5 transition-all duration-300 reveal ${
                  isCurrent
                    ? "border-orange-500/30 bg-orange-500/5 shadow-lg shadow-orange-500/5 hover:border-orange-500/50"
                    : "border-white/[0.07] bg-[#111111] hover:border-white/[0.15] hover:scale-[1.01]"
                }`}
              >
                {isCurrent && (
                  <div className="absolute -top-3 left-4 animate-scale-in">
                    <span className="rounded-full bg-orange-500 px-3 py-0.5 text-xs font-bold text-white shadow-lg shadow-orange-500/25">
                      Current
                    </span>
                  </div>
                )}

                <div className="mb-4 flex items-start justify-between gap-2">
                  <div>
                    <p className="font-bold text-white">{config.label}</p>
                    <p className="text-sm font-semibold text-orange-400">{config.price}</p>
                  </div>
                </div>

                <ul className="mb-4 space-y-2">
                  {features.map((f, idx) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-zinc-500 hover:text-zinc-400 transition-colors duration-200">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-400" />
                      {f}
                    </li>
                  ))}
                </ul>

                {!isCurrent && plan !== "enterprise" && (
                  <button
                    onClick={() => checkout(plan)}
                    disabled={checkingOut}
                    className="flex h-9 w-full items-center justify-center gap-2 rounded-xl bg-orange-500 text-xs font-bold text-white shadow-lg shadow-orange-500/20 transition-all hover:bg-orange-400 active:scale-[0.97] disabled:opacity-50 hover:scale-[1.02] animate-glow-pulse"
                  >
                    {checkingOut ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowRight className="h-3.5 w-3.5 animate-pulse" />}
                    Upgrade to {config.label}
                  </button>
                )}
                {!isCurrent && plan === "enterprise" && (
                  <a
                    href="mailto:sales@contractintel.in"
                    className="flex h-9 w-full items-center justify-center gap-2 rounded-xl border border-white/[0.1] bg-white/[0.04] text-xs font-bold text-zinc-300 transition-all hover:border-orange-500/30 hover:text-orange-400 hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Contact Sales
                  </a>
                )}
                {isCurrent && (
                  <p className="text-center text-xs text-zinc-600 mt-2 font-medium">You&apos;re on this plan</p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default function BillingPage() {
  return (
    <Suspense>
      <BillingContent />
    </Suspense>
  )
}
