import { cn } from "@/lib/utils";
import type {
  AgentRunStatus,
  ConversationStatus,
  TicketPriority,
  TicketStatus,
} from "@/lib/types";

type BadgeVariant =
  | ConversationStatus
  | TicketStatus
  | TicketPriority
  | AgentRunStatus
  | "indexed"
  | "processing"
  | "failed";

const styles: Record<BadgeVariant, string> = {
  resolved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  active: "bg-sky-50 text-sky-700 border-sky-200",
  escalated: "bg-amber-50 text-amber-700 border-amber-200",
  waiting: "bg-accent-soft text-accent border-accent/25",
  closed: "bg-canvas text-muted border-line",
  open: "bg-sky-50 text-sky-700 border-sky-200",
  in_progress: "bg-indigo-50 text-indigo-700 border-indigo-200",
  low: "bg-canvas text-muted border-line",
  medium: "bg-blue-50 text-blue-700 border-blue-200",
  high: "bg-orange-50 text-orange-700 border-orange-200",
  critical: "bg-red-50 text-red-700 border-red-200",
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  failed: "bg-red-50 text-red-700 border-red-200",
  indexed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  processing: "bg-amber-50 text-amber-700 border-amber-200",
};

const labels: Partial<Record<BadgeVariant, string>> = {
  in_progress: "In Progress",
  resolved: "Resolved",
  active: "Active",
  escalated: "Escalated",
  waiting: "Waiting",
  closed: "Closed",
  open: "Open",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
  success: "Success",
  failed: "Failed",
  indexed: "Indexed",
  processing: "Processing",
};

interface StatusBadgeProps {
  status: BadgeVariant;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        styles[status],
        className
      )}
    >
      {labels[status] ?? status}
    </span>
  );
}
