import { apiClient } from "./client"
import type {
  Subscription, UsageRecord, CreateCheckoutSessionRequest,
  CreateCheckoutSessionResponse, CreatePortalSessionResponse, SubscriptionPlan,
} from "@/lib/types/api"

export const billingApi = {
  getSubscription: (): Promise<Subscription> =>
    apiClient.get("/billing/subscription").then((r) => r.data),

  getUsage: (): Promise<UsageRecord[]> =>
    apiClient.get("/billing/usage").then((r) => r.data),

  createCheckout: (plan: SubscriptionPlan): Promise<CreateCheckoutSessionResponse> => {
    const origin = window.location.origin
    const data: CreateCheckoutSessionRequest = {
      plan,
      success_url: `${origin}/billing?success=1`,
      cancel_url: `${origin}/billing?canceled=1`,
    }
    return apiClient.post("/billing/checkout", data).then((r) => r.data)
  },

  createPortal: (): Promise<CreatePortalSessionResponse> =>
    apiClient.post("/billing/portal").then((r) => r.data),
}
