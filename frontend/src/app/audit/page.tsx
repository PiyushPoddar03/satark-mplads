"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, AuditLogItem } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import {
  ChevronDown,
  ChevronRight,
  Clock,
  FileCheck,
  Filter,
  History,
  Shield,
  User,
} from "lucide-react";
import { useRouter } from "next/navigation";

export default function AuditLogsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Filters
  const [roleFilter, setRoleFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push("/login");
        return;
      }
      if (user.role !== "admin" && user.role !== "auditor") {
        router.push("/dashboard");
        return;
      }
    }

    loadAuditLogs();
  }, [user, authLoading, router]);

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditLogs();
      setLogs(data);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  // Apply filters
  const filteredLogs = logs.filter((log) => {
    if (roleFilter && log.actor_role !== roleFilter) return false;
    if (entityTypeFilter && log.entity_type !== entityTypeFilter) return false;
    return true;
  });

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
              <History className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
              Immutable Audit Trail
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
              Complete cryptographic log of all platform actions, role assignments, expense bills, and forensic investigations
            </p>
          </div>

          <div className="flex items-center gap-2 bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200 dark:border-emerald-900/60 px-3 py-1.5 rounded-lg text-xs text-emerald-800 dark:text-emerald-300">
            <Shield className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>
              <strong className="font-mono">{logs.length}</strong> audit entries logged
            </span>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-4 mb-6 shadow-xs flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
            <Filter className="w-4 h-4" />
            Filters:
          </div>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="field_inspector">Field Inspector</option>
            <option value="district_officer">District Officer</option>
            <option value="auditor">Auditor</option>
          </select>

          <select
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
            className="px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Entity Types</option>
            <option value="project">Project</option>
            <option value="inspection">Inspection</option>
            <option value="evidence">Evidence</option>
            <option value="expense_bill">Expense Bill</option>
            <option value="risk_score">Risk Score</option>
            <option value="alert">Alert</option>
            <option value="user">User</option>
            <option value="assignment">Assignment</option>
          </select>

          {(roleFilter || entityTypeFilter) && (
            <button
              onClick={() => {
                setRoleFilter("");
                setEntityTypeFilter("");
              }}
              className="px-3 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 cursor-pointer"
            >
              Clear Filters
            </button>
          )}
        </div>

        {/* Audit Logs Table */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-xs overflow-hidden">
          {filteredLogs.length === 0 ? (
            <div className="p-12 text-center text-slate-500 dark:text-slate-400">
              No audit logs found matching the selected filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
                <thead className="bg-slate-50 dark:bg-slate-800 text-[11px] uppercase text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 w-12"></th>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Actor (Role)</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Entity Type</th>
                    <th className="px-4 py-3">Entity ID</th>
                    <th className="px-4 py-3">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {filteredLogs.map((log) => {
                    const isExpanded = expandedRows.has(log.id);
                    const hasChanges = log.previous_value || log.new_value;

                    return (
                      <React.Fragment key={log.id}>
                        <tr
                          className={`hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors ${
                            hasChanges ? "cursor-pointer" : ""
                          }`}
                          onClick={() => hasChanges && toggleRow(log.id)}
                        >
                          <td className="px-4 py-3">
                            {hasChanges &&
                              (isExpanded ? (
                                <ChevronDown className="w-4 h-4 text-slate-400" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-slate-400" />
                              ))}
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                            {new Date(log.created_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <User className="w-3.5 h-3.5 text-slate-400" />
                              <span className="font-medium text-slate-800 dark:text-slate-200">
                                {log.actor_id ? `User ${log.actor_id.slice(0, 8)}` : "System"}
                              </span>
                              {log.actor_role && (
                                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                                  {log.actor_role.replace("_", " ")}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="font-semibold text-slate-900 dark:text-white capitalize">
                              {log.action.replace("_", " ")}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="font-mono text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-[10px] border border-slate-200 dark:border-slate-700">
                              {log.entity_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-[10px] text-slate-500 dark:text-slate-400">
                            {log.entity_id?.slice(0, 12)}...
                          </td>
                          <td className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-md line-clamp-2">
                            {log.description || "—"}
                          </td>
                        </tr>

                        {/* Expanded Row: Before/After JSON Diff */}
                        {isExpanded && hasChanges && (
                          <tr className="bg-slate-50 dark:bg-slate-850">
                            <td colSpan={7} className="px-4 py-4">
                              <div className="grid md:grid-cols-2 gap-4">
                                {log.previous_value && (
                                  <div>
                                    <h4 className="text-[11px] font-bold uppercase text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1.5">
                                      <Clock className="w-3.5 h-3.5" />
                                      Previous State
                                    </h4>
                                    <pre className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded p-3 text-[10px] font-mono text-slate-700 dark:text-slate-300 overflow-auto max-h-48">
                                      {JSON.stringify(log.previous_value, null, 2)}
                                    </pre>
                                  </div>
                                )}

                                {log.new_value && (
                                  <div>
                                    <h4 className="text-[11px] font-bold uppercase text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1.5">
                                      <FileCheck className="w-3.5 h-3.5" />
                                      New State
                                    </h4>
                                    <pre className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded p-3 text-[10px] font-mono text-slate-700 dark:text-slate-300 overflow-auto max-h-48">
                                      {JSON.stringify(log.new_value, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
