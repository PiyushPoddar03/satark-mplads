import React from "react";

export function StatusBadge({ status }: { status: string }) {
  const getStyle = (st: string) => {
    switch (st.toLowerCase()) {
      case "approved":
        return "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-900/50";
      case "inspector_assigned":
        return "bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-900/50";
      case "under_inspection":
      case "inspection_pending":
        return "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-900/50";
      case "under_review":
        return "bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-900/50";
      case "completion_requested":
        return "bg-cyan-50 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border-cyan-300 dark:border-cyan-800/60 font-semibold";
      case "high_risk":
      case "escalated":
        return "bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border-red-200 dark:border-red-900/50 font-semibold";
      case "completed":
      case "closed":
        return "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900/50";
      default:
        return "bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700";
    }
  };

  const formatText = (st: string) => {
    return st.replace(/_/g, " ").toUpperCase();
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs border ${getStyle(status)}`}>
      {formatText(status)}
    </span>
  );
}

export function RiskBadge({ score }: { score?: number | null }) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
        N/A
      </span>
    );
  }

  let color = "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900/50";
  let label = "LOW";

  if (score > 80) {
    color = "bg-red-600 dark:bg-red-700 text-white border-red-700 dark:border-red-600 font-bold";
    label = "CRITICAL";
  } else if (score > 60) {
    color = "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-900/50 font-semibold";
    label = "HIGH";
  } else if (score >= 50) {
    color = "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-900/50 font-medium";
    label = "MEDIUM";
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs border ${color}`}>
      <span className="font-mono font-bold">{score.toFixed(0)}%</span>
      <span className="text-[10px] tracking-wider uppercase font-semibold">({label})</span>
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const getStyle = (s: string) => {
    switch (s.toLowerCase()) {
      case "critical":
        return "bg-red-100 dark:bg-red-950/70 text-red-800 dark:text-red-300 border-red-300 dark:border-red-900/60 font-bold";
      case "high":
        return "bg-rose-100 dark:bg-rose-950/70 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-900/60";
      case "medium":
        return "bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-900/60";
      case "low":
        return "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700";
      default:
        return "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300 border-gray-300 dark:border-gray-700";
    }
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border uppercase tracking-wider ${getStyle(severity)}`}>
      {severity}
    </span>
  );
}
