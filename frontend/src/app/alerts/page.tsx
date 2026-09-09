"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, AlertItem } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { SeverityBadge } from "@/components/StatusBadge";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  ExternalLink,
  Filter,
  FolderKanban,
  Search,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function AlertsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Resolution Modal
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [resolutionStatus, setResolutionStatus] = useState<
    "open" | "under_review" | "escalated" | "resolved" | "dismissed"
  >("under_review");
  const [notes, setNotes] = useState("");
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push("/login");
        return;
      }
      if (user.role !== "admin" && user.role !== "district_officer") {
        router.push("/dashboard");
        return;
      }
    }

    loadAlerts();
  }, [user, authLoading, severityFilter, statusFilter, router]);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await api.getAlerts(severityFilter || undefined, statusFilter || undefined);
      setAlerts(data);
    } catch (err) {
      console.error("Failed to load alerts:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAlert) return;

    try {
      setUpdating(true);
      await api.updateAlert(selectedAlert.id, {
        status: resolutionStatus,
        resolution_notes: notes || undefined,
      });
      setSelectedAlert(null);
      setNotes("");
      loadAlerts();
    } catch (err: any) {
      alert(`Failed to update alert: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors pb-12">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldAlert className="w-6 h-6 text-amber-500" />
              Forensic Anomalies & Alerts Center
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
              Automated anomaly flags detected via SATARK neural engine, material price benchmarks, and geospatial rules
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-4 mb-6 shadow-xs flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
            <Filter className="w-4 h-4" />
            Filters:
          </div>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="under_review">Under Review</option>
            <option value="escalated">Escalated</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </div>

        {/* Alerts Grid / Table */}
        {alerts.length === 0 ? (
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-12 text-center shadow-xs">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">No Anomalies Found</h3>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
              All projects are currently compliant with physical progress, geofence, and financial benchmarks.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-5 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700">
                        {alert.alert_code}
                      </span>
                      <SeverityBadge severity={alert.severity} />
                      <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                        {alert.status.replace("_", " ")}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1">{alert.title}</h3>

                    {alert.description && (
                      <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed max-w-3xl">{alert.description}</p>
                    )}

                    <div className="flex items-center gap-4 text-[11px] text-slate-400 dark:text-slate-500 pt-2 font-mono">
                      <span>Detected: {new Date(alert.created_at).toLocaleString()}</span>
                      {alert.assigned_to && <span>Assigned to: {alert.assigned_to}</span>}
                    </div>
                  </div>

                  <div className="flex flex-row md:flex-col items-center md:items-end justify-between gap-2">
                    <Link
                      href={`/projects/${alert.project_id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/70 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 px-3 py-1.5 rounded transition-colors"
                    >
                      Inspect Dossier <ArrowRight className="w-3.5 h-3.5" />
                    </Link>

                    <button
                      onClick={() => {
                        setSelectedAlert(alert);
                        setResolutionStatus(alert.status as any);
                        setNotes(alert.resolution_notes || "");
                      }}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 px-3 py-1.5 rounded transition-colors cursor-pointer"
                    >
                      Update Status
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Alert Status Resolution Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-xl max-w-lg w-full p-6 text-slate-900 dark:text-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-slate-900 dark:text-white text-base">Update Anomaly Status</h3>
              <button
                onClick={() => setSelectedAlert(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateAlert} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                  Investigation Status
                </label>
                <select
                  value={resolutionStatus}
                  onChange={(e: any) => setResolutionStatus(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="open">Open (Unreviewed)</option>
                  <option value="under_review">Under Review (Assigned to Officer)</option>
                  <option value="escalated">Escalated (Sent to Ministry)</option>
                  <option value="resolved">Resolved (Remediated)</option>
                  <option value="dismissed">Dismissed (False Positive)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                  Resolution / Forensic Remarks
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Provide audit notes on actions taken, physical verification, or contractor explanation..."
                  rows={4}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-slate-400"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedAlert(null)}
                  className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updating}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-semibold disabled:opacity-50 cursor-pointer"
                >
                  {updating ? "Saving..." : "Save Status & Log"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
