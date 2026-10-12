import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
  inverted?: boolean;
}

const sizes = {
  sm: { box: "h-8 w-8", icon: "h-4 w-4", text: "text-[15px]" },
  md: { box: "h-9 w-9", icon: "h-5 w-5", text: "text-lg" },
  lg: { box: "h-12 w-12", icon: "h-6 w-6", text: "text-3xl" },
};

export function BrandMark({
  className,
  size = "sm",
  showWordmark = true,
  inverted = false,
}: BrandMarkProps) {
  const s = sizes[size];

  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span
        className={cn(
          "flex items-center justify-center rounded-lg",
          s.box,
          inverted
            ? "bg-white/10 text-white ring-1 ring-white/15"
            : "bg-accent text-white"
        )}
      >
        <Bot className={s.icon} />
      </span>
      {showWordmark ? (
        <span
          className={cn(
            "font-display text-ink font-semibold tracking-tight",
            s.text,
            inverted && "text-white"
          )}
        >
          AI Support
        </span>
      ) : null}
    </span>
  );
}
