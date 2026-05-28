"use client"

import { useEffect, useRef } from "react"

/**
 * Attaches an IntersectionObserver to the returned ref.
 * When the element enters the viewport, the `visible` class is added to all
 * children that have a `reveal`, `reveal-scale`, `reveal-left`, or
 * `reveal-right` class, with an optional stagger delay.
 */
export function useScrollReveal<T extends HTMLElement = HTMLDivElement>(
  options?: IntersectionObserverInit
) {
  const ref = useRef<T>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const targets = el.querySelectorAll<HTMLElement>(
      ".reveal, .reveal-scale, .reveal-left, .reveal-right"
    )

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible")
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px", ...options }
    )

    targets.forEach((t) => observer.observe(t))

    return () => observer.disconnect()
  }, [])

  return ref
}

/**
 * Convenience wrapper: stagger sibling reveal elements.
 * Pass `staggerMs` (default 80ms) per sibling.
 */
export function useStaggerReveal<T extends HTMLElement = HTMLDivElement>(
  staggerMs = 80,
  options?: IntersectionObserverInit
) {
  const ref = useRef<T>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const targets = el.querySelectorAll<HTMLElement>(
      ".reveal, .reveal-scale, .reveal-left, .reveal-right"
    )

    targets.forEach((t, i) => {
      t.style.transitionDelay = `${i * staggerMs}ms`
    })

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible")
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.08, rootMargin: "0px 0px -32px 0px", ...options }
    )

    targets.forEach((t) => observer.observe(t))
    return () => observer.disconnect()
  }, [staggerMs])

  return ref
}
