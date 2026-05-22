// DEV BYPASS MODE — no Clerk auth, all routes public
// To restore Clerk auth: replace this file with the Clerk middleware version
import { NextResponse } from "next/server"

export function middleware() {
  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
}
