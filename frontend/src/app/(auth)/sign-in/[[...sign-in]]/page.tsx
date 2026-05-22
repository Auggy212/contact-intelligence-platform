import { redirect } from "next/navigation"

// DEV BYPASS MODE — skip login, go straight to dashboard
export default function SignInPage() {
  redirect("/projects")
}
