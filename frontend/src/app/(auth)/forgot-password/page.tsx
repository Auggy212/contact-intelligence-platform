import type { Metadata } from "next"
import { AuthScreen } from "@/components/auth/auth-screen"

export const metadata: Metadata = {
  title: "Reset password | Contract Intelligence Platform",
  description: "Reset access to your Contract Intelligence workspace.",
}

export default function ForgotPasswordPage() {
  return <AuthScreen mode="forgot-password" />
}
