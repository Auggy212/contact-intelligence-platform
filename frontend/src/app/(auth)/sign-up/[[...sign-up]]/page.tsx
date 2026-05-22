import { redirect } from "next/navigation"

// DEV BYPASS MODE — skip signup, go straight to dashboard
export default function SignUpPage() {
  redirect("/projects")
}
