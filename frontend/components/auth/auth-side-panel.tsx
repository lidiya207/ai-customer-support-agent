import Image from "next/image";
import Link from "next/link";
import { BrandMark } from "@/components/ui/brand-mark";

interface AuthSidePanelProps {
  title: string;
  description: string;
  footer?: string;
}

export function AuthSidePanel({
  title,
  description,
  footer,
}: AuthSidePanelProps) {
  return (
    <div className="relative hidden min-h-screen w-[46%] overflow-hidden bg-brand lg:block">
      <Image
        src="/images/auth-side.jpg"
        alt="Customer support specialist helping customers"
        fill
        priority
        className="object-cover"
        sizes="46vw"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-brand via-brand/60 to-brand/30" />

      <div className="relative z-10 flex min-h-screen flex-col justify-between p-12">
        <Link href="/">
          <BrandMark inverted size="md" />
        </Link>

        <div className="max-w-sm">
          <h1 className="font-display text-4xl font-semibold tracking-tight text-white">
            {title}
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-white/75">
            {description}
          </p>
        </div>

        {footer ? (
          <p className="text-xs text-white/45">{footer}</p>
        ) : (
          <span />
        )}
      </div>
    </div>
  );
}
