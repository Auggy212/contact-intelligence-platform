import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-muted",
        // shimmer sweep — a touch more premium than a flat pulse
        "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.6s_infinite]",
        "before:bg-gradient-to-r before:from-transparent before:via-black/[0.04] before:to-transparent",
        "motion-reduce:before:hidden motion-reduce:animate-pulse",
        className,
      )}
      {...props}
    />
  )
}

export { Skeleton }
