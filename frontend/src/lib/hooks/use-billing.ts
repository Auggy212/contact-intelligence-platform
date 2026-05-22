import { useQuery, useMutation } from "@tanstack/react-query"
import { billingApi } from "@/lib/api/billing"
import type { SubscriptionPlan } from "@/lib/types/api"
import { toast } from "sonner"

export function useSubscription() {
  return useQuery({ queryKey: ["subscription"], queryFn: () => billingApi.getSubscription() })
}

export function useUsage() {
  return useQuery({ queryKey: ["usage"], queryFn: () => billingApi.getUsage() })
}

export function useCheckout() {
  return useMutation({
    mutationFn: (plan: SubscriptionPlan) => billingApi.createCheckout(plan),
    onSuccess: (data) => { window.location.href = data.checkout_url },
    onError: () => toast.error("Could not open checkout. Please try again."),
  })
}

export function useBillingPortal() {
  return useMutation({
    mutationFn: () => billingApi.createPortal(),
    onSuccess: (data) => { window.location.href = data.portal_url },
    onError: () => toast.error("Could not open billing portal."),
  })
}
