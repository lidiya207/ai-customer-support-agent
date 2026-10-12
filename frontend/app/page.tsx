import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  MessageSquare,
  Ticket,
  Wrench,
  UserRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/ui/brand-mark";

const features = [
  {
    title: "AI Conversations",
    description: "Answer customers instantly with a local or cloud LLM.",
    icon: MessageSquare,
  },
  {
    title: "Knowledge Search",
    description: "Pull accurate answers from your docs and policies.",
    icon: BookOpen,
  },
  {
    title: "Tool Calling",
    description: "Look up orders, tickets, and account data safely.",
    icon: Wrench,
  },
  {
    title: "Human Escalation",
    description: "Hand off complex issues to a real support agent.",
    icon: UserRound,
  },
  {
    title: "Ticket Management",
    description: "Create and track support requests automatically.",
    icon: Ticket,
  },
  {
    title: "AI Analytics",
    description: "See resolution rates, intent, and agent activity.",
    icon: BarChart3,
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-atmosphere">
      <header className="sticky top-0 z-40 border-b border-line/80 bg-surface/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/">
            <BrandMark />
          </Link>

          <nav className="hidden items-center gap-8 text-sm text-muted md:flex">
            <a href="#product" className="hover:text-ink">
              Product
            </a>
            <a href="#features" className="hover:text-ink">
              Features
            </a>
            <Link href="/dashboard" className="hover:text-ink">
              Dashboard
            </Link>
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm" className="hidden sm:inline-flex">
                Sign in
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section id="product" className="relative overflow-hidden">
          <div className="animate-soft-pulse pointer-events-none absolute left-1/2 top-0 h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />

          <div className="relative mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:py-0">
            <div>
              <BrandMark size="lg" className="animate-rise mb-8" />
              <h1 className="animate-rise-delay-1 font-display text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-[3.5rem]">
                Customer support that works while you sleep.
              </h1>
              <p className="animate-rise-delay-2 mt-5 max-w-md text-base leading-relaxed text-muted sm:text-lg">
                AI that searches knowledge, calls tools, opens tickets, and
                escalates to humans when it should.
              </p>
              <div className="animate-rise-delay-2 mt-8 flex flex-col gap-3 sm:flex-row">
                <Link href="/register">
                  <Button size="lg" className="w-full sm:w-auto">
                    Start chatting
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link href="/login">
                  <Button
                    variant="outline"
                    size="lg"
                    className="w-full sm:w-auto"
                  >
                    Sign in
                  </Button>
                </Link>
              </div>
            </div>

            <div className="animate-fade relative hidden lg:block">
              <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-[0_24px_80px_-24px_rgba(17,24,39,0.35)]">
                <div className="flex items-center gap-2 border-b border-line bg-canvas px-4 py-3">
                  <span className="h-2.5 w-2.5 rounded-full bg-line" />
                  <span className="h-2.5 w-2.5 rounded-full bg-line" />
                  <span className="h-2.5 w-2.5 rounded-full bg-line" />
                  <span className="ml-2 text-xs font-medium text-muted">
                    AI Support · live chat
                  </span>
                </div>
                <div className="space-y-4 p-6">
                  <div className="ml-auto max-w-[78%] rounded-2xl rounded-br-md bg-accent px-4 py-3 text-sm text-white">
                    Where is my order #45231?
                  </div>
                  <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-line bg-canvas px-4 py-3 text-sm text-ink">
                    Order <span className="font-medium">#45231</span> shipped
                    yesterday and is out for delivery today.
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-md bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent">
                    Used tool · get_order_status
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="border-t border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <h2 className="font-display text-3xl font-semibold tracking-tight text-ink">
              Built for the full support loop
            </h2>
            <p className="mt-3 max-w-xl text-muted">
              From first message to resolution — AI, knowledge, tools, and
              humans in one flow.
            </p>

            <div className="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div key={feature.title}>
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-accent-soft text-accent">
                      <Icon className="h-4 w-4" />
                    </div>
                    <h3 className="font-display text-lg font-semibold text-ink">
                      {feature.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted">
                      {feature.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-canvas">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-6 text-sm text-muted sm:px-6">
          <BrandMark size="sm" />
          <span>Built for modern support teams</span>
        </div>
      </footer>
    </div>
  );
}
