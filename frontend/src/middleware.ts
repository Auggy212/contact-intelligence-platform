import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// Routes that are always public (landing + auth pages)
const PUBLIC_PATHS = ["/", "/sign-in", "/sign-up"]

// Routes that are always allowed regardless (Next.js internals, fonts, favicons)
function isStaticAsset(pathname: string) {
  return (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/fonts") ||
    pathname.match(/\.(ico|png|jpg|jpeg|svg|webp|woff|woff2)$/) !== null
  )
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (isStaticAsset(pathname)) return NextResponse.next()

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  )

  // Read mock session from cookie (set by the client after localStorage save)
  const sessionCookie = request.cookies.get("cip_session")
  const isLoggedIn = sessionCookie?.value === "1"

  // Logged-in user hitting landing/auth → send to dashboard
  if (isLoggedIn && (pathname === "/" || pathname.startsWith("/sign-in") || pathname.startsWith("/sign-up"))) {
    return NextResponse.redirect(new URL("/projects", request.url))
  }

  // Unauthenticated user hitting dashboard → send to landing
  if (!isLoggedIn && !isPublic) {
    return NextResponse.redirect(new URL("/", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
}
