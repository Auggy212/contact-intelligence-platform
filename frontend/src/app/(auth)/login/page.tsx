import type { Metadata } from "next"
import { AuthScreen } from "@/components/auth/auth-screen"

export const metadata: Metadata = {
  title: "Login | Contract Intelligence Platform",
  description: "Log in to your Contract Intelligence workspace.",
}

export default function LoginPage() {
  return <AuthScreen mode="sign-in" />
}
