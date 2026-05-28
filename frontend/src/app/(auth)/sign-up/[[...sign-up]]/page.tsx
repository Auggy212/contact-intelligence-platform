import type { Metadata } from "next"
import { AuthScreen } from "@/components/auth/auth-screen"

export const metadata: Metadata = {
  title: "Create account | Contract Intelligence Platform",
  description: "Create your Contract Intelligence workspace.",
}

export default function SignUpPage() {
  return <AuthScreen mode="sign-up" />
}
