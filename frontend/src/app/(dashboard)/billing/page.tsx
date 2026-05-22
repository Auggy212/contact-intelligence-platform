"use client"

import { useSearchParams } from "next/navigation"
import { useEffect, Suspense } from "react"
import { useSubscription, useUsage, useCheckout, useBillingPortal } from "@/lib/hooks/use-billing"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { PLAN_LIMITS } from "@/lib/types/api"
import type { SubscriptionPlan } from "@/lib/types/api"
import { CreditCard, Zap, HardDrive, CheckCircle2, ArrowRight, AlertTriangle, Loader2, TrendingUp } from "lucide-react"
import { toast } from "sonner"
import { formatBytes, formatNumber } from "@/lib/utils"

const STATUS_CONFIG = {
  active: { label: "Active", className: "bg-green-100 text-green-700 border-green-200" },
  trialing: { label: "Trial", className: "bg-blue-100 text-blue-700 border-blue-200" },
  past_due: { label: "Past Due", className: "bg-red-100 text-red-700 border-red-200" },
  canceled: { label: "Canceled", className: "bg-slate-100 text-slate-600 border-slate-200" },
} as const

const PLAN_FEATURES: Record<SubscriptionPlan, string[]> = {
  trial: ["3 contract reviews", "All 4 analysis types", "Clause library", "PDF export"],
  starter: ["25 contract reviews/month", "All analysis types", "Team collaboration (5 seats)", "Priority support"],
  professional: ["100 contract reviews/month", "Unlimited team seats", "Custom checklist rules", "Dedicated account manager"],
  enterprise: ["Unlimited contracts", "Custom SLAs", "On-premise option", "Custom integrations"],
}

function ProgressBar({ value, max, colorClass }: { value: number; max: number | null; colorClass: string }) {
  const percent = max == null ? 0 : Math.min(100, (value / max) * 100)
  return (
    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${colorClass}`}
        style={{ width: max == null ? "0%" : `${percent}%` }}
      />
    </div>
  )
}

function BillingContent() {
  const { data: subscription, isLoading: loadingSub } = useSubscription()
  const { data: usage, isLoading: loadingUsage } = useUsage()
  const { mutate: checkout, isPending: checkingOut } = useCheckout()
  const { mutate: openPortal, isPending: openingPortal } = useBillingPortal()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (searchParams.get("success") === "1") toast.success("Subscription updated successfully!")
    if (searchParams.get("canceled") === "1") toast.info("Checkout canceled — no changes made.")
    if (searchParams.get("demo") === "1") {
      const plan = searchParams.get("plan")
      const isPortal = searchParams.get("portal") === "1"
      if (isPortal) {
        toast.info("Billing portal requires Stripe — will be enabled when Stripe keys are configured.")
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
      <PageHeader
        title="Billing & Usage"
        description="Manage your subscription, usage, and payment details"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Current subscription + usage */}
        <div className="lg:col-span-2 space-y-6">
          {/* Current plan card */}
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base">Current Plan</CardTitle>
                  <p className="text-sm text-slate-500 mt-0.5">Your organisation&apos;s active subscription</p>
                </div>
                {subscription && (
                  <Badge className={`text-xs border ${STATUS_CONFIG[subscription.status].className}`}>
                    {STATUS_CONFIG[subscription.status].label}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {loadingSub ? (
                <div className="space-y-3">
                  <Skeleton className="h-8 w-40" />
                  <Skeleton className="h-4 w-56" />
                </div>
              ) : (
                <>
                  <div className="flex items-end gap-3">
                    <span className="text-3xl font-bold text-slate-900">{planLimit.label}</span>
                    <span className="text-lg text-slate-500 mb-0.5">{planLimit.price}</span>
                  </div>

                  {trialDaysLeft != null && (
                    <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>Trial ends in <strong>{trialDaysLeft} day{trialDaysLeft !== 1 ? "s" : ""}</strong> — upgrade to keep your data</span>
                    </div>
                  )}

                  {subscription?.current_period_end && (
                    <p className="text-xs text-slate-500">
                      Current period ends{" "}
                      <span className="font-medium text-slate-700">
                        {new Date(subscription.current_period_end).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
                      </span>
                    </p>
                  )}

                  {currentPlan !== "trial" && (
                    <Button variant="outline" size="sm" onClick={() => openPortal()} disabled={openingPortal}>
                      {openingPortal ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CreditCard className="w-4 h-4 mr-2" />}
                      Manage Billing
                    </Button>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Usage card */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Usage This Period</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {loadingUsage ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 rounded-lg" />)}
                </div>
              ) : (
                <>
                  {/* Contracts */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-blue-500" />
                        <span className="font-medium text-slate-800">Contracts Processed</span>
                      </div>
                      <span className={`font-semibold ${isNearLimit ? "text-amber-600" : "text-slate-700"}`}>
                        {contractsUsed}
                        {contractLimit != null && <span className="text-slate-400 font-normal"> / {contractLimit}</span>}
                        {contractLimit == null && <span className="text-slate-400 font-normal"> (unlimited)</span>}
                      </span>
                    </div>
                    <ProgressBar
                      value={contractsUsed}
                      max={contractLimit}
                      colorClass={contractPercent >= 90 ? "bg-red-500" : contractPercent >= 70 ? "bg-amber-500" : "bg-blue-500"}
                    />
                    {isNearLimit && contractLimit != null && (
                      <p className="text-xs text-amber-600">{contractPercent}% of limit used — consider upgrading</p>
                    )}
                  </div>

                  {/* AI Tokens */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-purple-500" />
                        <span className="font-medium text-slate-800">AI Tokens Used</span>
                      </div>
                      <span className="font-semibold text-slate-700">
                        {formatNumber(currentUsage?.ai_tokens_used ?? 0)}
                      </span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-purple-400 rounded-full w-0" />
                    </div>
                  </div>

                  {/* Storage */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <HardDrive className="w-4 h-4 text-slate-400" />
                        <span className="font-medium text-slate-800">Storage Used</span>
                      </div>
                      <span className="font-semibold text-slate-700">
                        {formatBytes(currentUsage?.storage_bytes_used ?? 0)}
                      </span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-slate-400 rounded-full w-0" />
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Plan comparison */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Available Plans</h3>
          {UPGRADE_PLANS.map((plan) => {
            const config = PLAN_LIMITS[plan]
            const isCurrent = plan === currentPlan
            const features = PLAN_FEATURES[plan]

            return (
              <Card key={plan} className={`relative ${isCurrent ? "ring-2 ring-blue-500" : ""}`}>
                {isCurrent && (
                  <div className="absolute -top-2.5 left-4">
                    <span className="text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full font-medium">Current</span>
                  </div>
                )}
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-slate-900">{config.label}</p>
                      <p className="text-sm font-medium text-blue-600">{config.price}</p>
                    </div>
                  </div>
                  <ul className="space-y-1.5">
                    {features.map((f) => (
                      <li key={f} className="flex items-start gap-1.5 text-xs text-slate-600">
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  {!isCurrent && plan !== "enterprise" && (
                    <Button
                      size="sm"
                      className="w-full"
                      disabled={checkingOut}
                      onClick={() => checkout(plan)}
                    >
                      {checkingOut ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <ArrowRight className="w-4 h-4 mr-2" />
                      )}
                      Upgrade to {config.label}
                    </Button>
                  )}
                  {!isCurrent && plan === "enterprise" && (
                    <Button size="sm" variant="outline" className="w-full" asChild>
                      <a href="mailto:sales@contractintel.in">Contact Sales</a>
                    </Button>
                  )}
                  {isCurrent && (
                    <p className="text-xs text-center text-slate-400">You&apos;re on this plan</p>
                  )}
                </CardContent>
              </Card>
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
