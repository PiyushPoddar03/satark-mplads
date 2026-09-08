"use client";

import { useEffect, useState } from "react";
import {
  api,
  InspectorRequestItem,
  UserProfile,
} from "@/lib/api";
import {
  AlertCircle,
  AlertTriangle,
  Building,
  Check,
  CheckCircle2,
  Clock,
  FileText,
  Mail,
  Phone,
  Plus,
  RefreshCw,
  Search,
  Send,
  Shield,
  Trash2,
  UserCheck,
  UserMinus,
  UserPlus,
  Users,
  X,
  XCircle,
} from "lucide-react";

interface InspectorManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile;
  onSuccess?: () => void;
}

export function InspectorManagementModal({
  isOpen,
  onClose,
  currentUser,
  onSuccess,
}: InspectorManagementModalProps) {
  const isAdmin = currentUser.role === "admin";
  const isOfficer = currentUser.role === "district_officer";

  // Active tab state
  const [activeTab, setActiveTab] = useState<"add" | "remove" | "requests">("add");

  // Inspectors list
  const [inspectors, setInspectors] = useState<any[]>([]);
  const [loadingInspectors, setLoadingInspectors] = useState(false);
  const [searchInspector, setSearchInspector] = useState("");

  // Requests list
  const [requests, setRequests] = useState<InspectorRequestItem[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);
  const [requestFilter, setRequestFilter] = useState<"all" | "pending" | "approved" | "rejected">("all");

  // Add Form state
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "Password@123",
    inspector_id: `INS-KA-00${Math.floor(10 + Math.random() * 90)}`,
    phone: "",
    district: currentUser.district || "Bengaluru Urban",
    state: currentUser.state || "Karnataka",
    reason: "",
  });
  const [submittingAdd, setSubmittingAdd] = useState(false);

  // Remove Form / Action state
  const [selectedInspectorForRemoval, setSelectedInspectorForRemoval] = useState<string>("");
  const [removalReason, setRemovalReason] = useState("");
  const [submittingRemove, setSubmittingRemove] = useState(false);

  // Review modal / action state
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [adminReviewNotes, setAdminReviewNotes] = useState("");
  const [reviewingAction, setReviewingAction] = useState<"approve" | "reject" | null>(null);
  const [submittingReview, setSubmittingReview] = useState(false);

  // Feedback message
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Load Inspectors
  const loadInspectors = async () => {
    try {
      setLoadingInspectors(true);
      const data = await api.getUsers("field_inspector");
      setInspectors(data);
    } catch (err) {
      console.error("Failed to load inspectors:", err);
    } finally {
      setLoadingInspectors(false);
    }
  };

  // Load Requests
  const loadRequests = async () => {
    try {
      setLoadingRequests(true);
      const data = await api.getInspectorRequests();
      setRequests(data);
    } catch (err) {
      console.error("Failed to load inspector requests:", err);
    } finally {
      setLoadingRequests(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadInspectors();
      loadRequests();
      setMessage(null);
      setFormData({
        full_name: "",
        email: "",
        password: "Password@123",
        inspector_id: `INS-KA-00${Math.floor(10 + Math.random() * 90)}`,
        phone: "",
        district: currentUser.district || "Bengaluru Urban",
        state: currentUser.state || "Karnataka",
        reason: "",
      });
      setSelectedInspectorForRemoval("");
      setRemovalReason("");
      setReviewingId(null);
    }
  }, [isOpen, currentUser]);

  if (!isOpen) return null;

  const pendingRequestsCount = requests.filter((r) => r.status === "pending").length;

  // Filter inspectors by search
  const filteredInspectors = inspectors.filter((insp) => {
    const q = searchInspector.toLowerCase();
    return (
      insp.full_name?.toLowerCase().includes(q) ||
      insp.email?.toLowerCase().includes(q) ||
      insp.inspector_id?.toLowerCase().includes(q) ||
      insp.district?.toLowerCase().includes(q)
    );
  });

  // Filter requests
  const filteredRequests = requests.filter((req) => {
    if (requestFilter === "all") return true;
    return req.status === requestFilter;
  });

  // Handle Add (Direct for Admin, Request for District Officer)
  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingAdd(true);
    setMessage(null);

    try {
      if (isAdmin) {
        // Direct admin creation
        await api.createInspector({
          full_name: formData.full_name,
          email: formData.email,
          password: formData.password,
          inspector_id: formData.inspector_id,
          phone: formData.phone,
          district: formData.district,
          state: formData.state,
        });

        setMessage({
          type: "success",
          text: `Inspector ${formData.full_name} (${formData.inspector_id}) has been successfully created and activated!`,
        });
        loadInspectors();
        onSuccess?.();
      } else {
        // District Officer request submission
        if (!formData.reason.trim()) {
          setMessage({
            type: "error",
            text: "Please provide a justification reason for requesting this field inspector.",
          });
          setSubmittingAdd(false);
          return;
        }

        await api.createInspectorRequest({
          request_type: "add",
          inspector_data: {
            full_name: formData.full_name,
            email: formData.email,
            password: formData.password,
            inspector_id: formData.inspector_id,
            phone: formData.phone,
            district: formData.district,
            state: formData.state,
          },
          reason: formData.reason,
        });

        setMessage({
          type: "success",
          text: "Inspector Addition Request submitted to Admin for approval!",
        });
        loadRequests();
        setActiveTab("requests");
        onSuccess?.();
      }

      // Reset form
      setFormData({
        full_name: "",
        email: "",
        password: "Password@123",
        inspector_id: `INS-KA-00${Math.floor(10 + Math.random() * 90)}`,
        phone: "",
        district: currentUser.district || "Bengaluru Urban",
        state: currentUser.state || "Karnataka",
        reason: "",
      });
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.message || "Failed to process inspector request.",
      });
    } finally {
      setSubmittingAdd(false);
    }
  };

  // Handle Remove (Direct for Admin, Request for District Officer)
  const handleRemoveSubmit = async (targetId: string, inspectorName: string, promptReason = false) => {
    setMessage(null);

    if (isAdmin) {
      if (!confirm(`Are you sure you want to deactivate and remove Field Inspector "${inspectorName}"? Any active project assignments will be revoked.`)) {
        return;
      }

      try {
        setSubmittingRemove(true);
        await api.deleteUser(targetId);
        setMessage({
          type: "success",
          text: `Field Inspector ${inspectorName} has been deactivated and removed.`,
        });
        loadInspectors();
        onSuccess?.();
      } catch (err: any) {
        setMessage({
          type: "error",
          text: err.message || "Failed to remove inspector.",
        });
      } finally {
        setSubmittingRemove(false);
      }
    } else {
      // District Officer proposal
      if (!removalReason.trim()) {
        setMessage({
          type: "error",
          text: "Please provide a reason for the removal/transfer request.",
        });
        return;
      }

      try {
        setSubmittingRemove(true);
        await api.createInspectorRequest({
          request_type: "remove",
          target_inspector_id: targetId,
          inspector_data: { full_name: inspectorName },
          reason: removalReason,
        });

        setMessage({
          type: "success",
          text: `Removal request for ${inspectorName} submitted to Admin for approval.`,
        });
        setSelectedInspectorForRemoval("");
        setRemovalReason("");
        loadRequests();
        setActiveTab("requests");
        onSuccess?.();
      } catch (err: any) {
        setMessage({
          type: "error",
          text: err.message || "Failed to submit removal request.",
        });
      } finally {
        setSubmittingRemove(false);
      }
    }
  };

  // Handle Admin Review (Approve / Reject)
  const handleProcessReview = async () => {
    if (!reviewingId || !reviewingAction) return;

    setSubmittingReview(true);
    setMessage(null);

    try {
      if (reviewingAction === "approve") {
        await api.approveInspectorRequest(reviewingId, adminReviewNotes);
        setMessage({
          type: "success",
          text: "Request approved! The inspector configuration has been executed.",
        });
      } else {
        await api.rejectInspectorRequest(reviewingId, adminReviewNotes);
        setMessage({
          type: "success",
          text: "Request has been rejected.",
        });
      }

      setReviewingId(null);
      setAdminReviewNotes("");
      setReviewingAction(null);
      loadRequests();
      loadInspectors();
      onSuccess?.();
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.message || "Failed to process review.",
      });
    } finally {
      setSubmittingReview(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-3xl w-full p-6 my-8 text-slate-900 dark:text-slate-100 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                Field Inspector Management
                {isAdmin ? (
                  <span className="text-[11px] font-semibold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 px-2 py-0.5 rounded-full">
                    Admin Authority
                  </span>
                ) : (
                  <span className="text-[11px] font-semibold bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded-full">
                    District Officer Workflow
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {isAdmin
                  ? "Directly provision, deactivate, or approve field inspectors across all districts."
                  : "Submit formal requests to the Admin for adding or removing field officers in your jurisdiction."}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Message Banner */}
        {message && (
          <div
            className={`mt-4 p-3.5 rounded-lg flex items-start gap-2.5 text-xs font-medium ${
              message.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-800"
                : "bg-red-50 dark:bg-red-950/50 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">{message.text}</div>
            <button onClick={() => setMessage(null)} className="text-slate-400 hover:text-slate-600">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 mt-4 border-b border-slate-200 dark:border-slate-800 pb-2">
          <button
            onClick={() => {
              setActiveTab("add");
              setMessage(null);
            }}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
              activeTab === "add"
                ? "bg-emerald-600 text-white shadow-xs"
                : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <UserPlus className="w-3.5 h-3.5" />
            {isAdmin ? "Add Field Inspector" : "Request Add Inspector"}
          </button>

          <button
            onClick={() => {
              setActiveTab("remove");
              setMessage(null);
            }}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
              activeTab === "remove"
                ? "bg-red-600 text-white shadow-xs"
                : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <UserMinus className="w-3.5 h-3.5" />
            {isAdmin ? "Active Inspectors & Remove" : "Request Remove Inspector"}
          </button>

          <button
            onClick={() => {
              setActiveTab("requests");
              setMessage(null);
            }}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-colors relative cursor-pointer ${
              activeTab === "requests"
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            {isAdmin ? "Approval Requests" : "My Submitted Requests"}
            {pendingRequestsCount > 0 && (
              <span
                className={`ml-1 text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  activeTab === "requests"
                    ? "bg-white text-indigo-700"
                    : "bg-amber-500 text-white"
                }`}
              >
                {pendingRequestsCount}
              </span>
            )}
          </button>
        </div>

        {/* Tab Content Container */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {/* TAB 1: ADD INSPECTOR */}
          {activeTab === "add" && (
            <div>
              {!isAdmin && (
                <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 rounded-lg p-3.5 mb-4 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
                  <Shield className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <p>
                    <strong>Approval Policy:</strong> As District Officer, your request to register a new field officer will be reviewed by the SATARK Admin. Once approved, login access will be activated immediately.
                  </p>
                </div>
              )}

              <form onSubmit={handleAddSubmit} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                    Inspector Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    placeholder="e.g. Ramesh Chandra Gowda"
                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      Official Email (Login ID) *
                    </label>
                    <input
                      type="email"
                      required
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="ramesh.gowda@satark.gov.in"
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      Password *
                    </label>
                    <input
                      type="password"
                      required
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      Unique Inspector ID Code *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.inspector_id}
                      onChange={(e) => setFormData({ ...formData, inspector_id: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg font-mono text-sm"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      Mobile Number
                    </label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="+91 98765 43210"
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      District Jurisdiction *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.district}
                      onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      State *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.state}
                      onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                    />
                  </div>
                </div>

                {!isAdmin && (
                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      Justification / Reason for Addition *
                    </label>
                    <textarea
                      required
                      rows={2}
                      value={formData.reason}
                      onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                      placeholder="e.g. Required for newly sanctioned rural drinking water and hospital projects in North Bengaluru block."
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                    />
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-xs font-semibold cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingAdd}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold disabled:opacity-50 flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    {submittingAdd ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : isAdmin ? (
                      <UserPlus className="w-3.5 h-3.5" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                    {isAdmin ? "Directly Create Inspector" : "Submit Request to Admin"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 2: REMOVE INSPECTOR */}
          {activeTab === "remove" && (
            <div className="space-y-4">
              {isAdmin ? (
                <div>
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <div className="relative flex-1">
                      <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Search inspectors by name, code, or district..."
                        value={searchInspector}
                        onChange={(e) => setSearchInspector(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-xs"
                      />
                    </div>
                    <button
                      onClick={loadInspectors}
                      className="p-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-600 dark:text-slate-300 cursor-pointer"
                      title="Refresh list"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${loadingInspectors ? "animate-spin" : ""}`} />
                    </button>
                  </div>

                  <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden divide-y divide-slate-200 dark:divide-slate-800">
                    {filteredInspectors.length === 0 ? (
                      <div className="p-8 text-center text-xs text-slate-500">
                        No active field inspectors found.
                      </div>
                    ) : (
                      filteredInspectors.map((insp) => (
                        <div
                          key={insp.id}
                          className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white dark:bg-slate-900/50 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                        >
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300 font-bold text-xs mt-0.5">
                              {insp.full_name?.charAt(0) || "I"}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="font-bold text-xs text-slate-900 dark:text-white">
                                  {insp.full_name}
                                </h4>
                                <span className="font-mono text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-1.5 py-0.5 rounded">
                                  {insp.inspector_id}
                                </span>
                              </div>
                              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                                <span className="flex items-center gap-1">
                                  <Mail className="w-3 h-3" /> {insp.email}
                                </span>
                                {insp.phone && (
                                  <span className="flex items-center gap-1">
                                    <Phone className="w-3 h-3" /> {insp.phone}
                                  </span>
                                )}
                                <span className="flex items-center gap-1">
                                  <Building className="w-3 h-3" /> {insp.district || "Unassigned"}, {insp.state || ""}
                                </span>
                              </div>
                            </div>
                          </div>

                          <button
                            type="button"
                            disabled={submittingRemove}
                            onClick={() => handleRemoveSubmit(insp.id, insp.full_name)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-50 dark:bg-red-950/60 hover:bg-red-600 hover:text-white text-red-700 dark:text-red-300 border border-red-200 dark:border-red-900/60 rounded-md text-xs font-semibold transition-colors cursor-pointer self-start sm:self-auto"
                          >
                            <Trash2 className="w-3 h-3" />
                            Deactivate / Remove
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                /* District Officer removal request workflow */
                <div className="space-y-4 text-xs">
                  <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 rounded-lg p-3.5 text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
                    <Shield className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <p>
                      <strong>Decommissioning Request:</strong> Select an inspector operating in your district and state the formal reason for removal or transfer. The Admin will review and execute the revocation upon approval.
                    </p>
                  </div>

                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      Select Field Inspector to Decommission *
                    </label>
                    <select
                      value={selectedInspectorForRemoval}
                      onChange={(e) => setSelectedInspectorForRemoval(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm text-slate-900 dark:text-white"
                      required
                    >
                      <option value="">-- Choose Field Inspector --</option>
                      {inspectors.map((insp) => (
                        <option key={insp.id} value={insp.id}>
                          {insp.full_name} ({insp.inspector_id}) — {insp.district || "District"}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold uppercase text-slate-700 dark:text-slate-300 mb-1">
                      Reason / Justification for Removal *
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={removalReason}
                      onChange={(e) => setRemovalReason(e.target.value)}
                      placeholder="e.g. Officer transferred to another administrative division / completed project inspection cycle."
                      className="w-full px-3 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-lg text-sm"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-xs font-semibold cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={submittingRemove || !selectedInspectorForRemoval || !removalReason.trim()}
                      onClick={() => {
                        const target = inspectors.find((i) => i.id === selectedInspectorForRemoval);
                        if (target) {
                          handleRemoveSubmit(target.id, target.full_name);
                        }
                      }}
                      className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold disabled:opacity-50 flex items-center gap-1.5 cursor-pointer shadow-xs"
                    >
                      {submittingRemove ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <UserMinus className="w-3.5 h-3.5" />
                      )}
                      Submit Removal Request to Admin
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: APPROVAL REQUESTS */}
          {activeTab === "requests" && (
            <div className="space-y-4">
              {/* Filter Buttons */}
              <div className="flex items-center justify-between gap-2 flex-wrap pb-1">
                <div className="flex items-center gap-1.5 text-xs">
                  <button
                    onClick={() => setRequestFilter("all")}
                    className={`px-2.5 py-1 rounded-full font-semibold transition-colors cursor-pointer ${
                      requestFilter === "all"
                        ? "bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                    }`}
                  >
                    All ({requests.length})
                  </button>
                  <button
                    onClick={() => setRequestFilter("pending")}
                    className={`px-2.5 py-1 rounded-full font-semibold transition-colors cursor-pointer ${
                      requestFilter === "pending"
                        ? "bg-amber-600 text-white"
                        : "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300"
                    }`}
                  >
                    Pending ({requests.filter((r) => r.status === "pending").length})
                  </button>
                  <button
                    onClick={() => setRequestFilter("approved")}
                    className={`px-2.5 py-1 rounded-full font-semibold transition-colors cursor-pointer ${
                      requestFilter === "approved"
                        ? "bg-emerald-600 text-white"
                        : "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300"
                    }`}
                  >
                    Approved ({requests.filter((r) => r.status === "approved").length})
                  </button>
                  <button
                    onClick={() => setRequestFilter("rejected")}
                    className={`px-2.5 py-1 rounded-full font-semibold transition-colors cursor-pointer ${
                      requestFilter === "rejected"
                        ? "bg-red-600 text-white"
                        : "bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300"
                    }`}
                  >
                    Rejected ({requests.filter((r) => r.status === "rejected").length})
                  </button>
                </div>

                <button
                  onClick={loadRequests}
                  className="p-1.5 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-600 dark:text-slate-300 cursor-pointer text-xs flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${loadingRequests ? "animate-spin" : ""}`} />
                  Refresh
                </button>
              </div>

              {/* Requests List */}
              <div className="space-y-3">
                {filteredRequests.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500 border border-dashed border-slate-200 dark:border-slate-800 rounded-lg">
                    No requests found matching this filter.
                  </div>
                ) : (
                  filteredRequests.map((req) => {
                    const isPending = req.status === "pending";
                    const isAdd = req.request_type === "add";

                    return (
                      <div
                        key={req.id}
                        className={`p-4 rounded-lg border text-xs transition-all ${
                          isPending
                            ? "bg-amber-50/40 dark:bg-amber-950/20 border-amber-300 dark:border-amber-900/60"
                            : req.status === "approved"
                            ? "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800"
                            : "bg-slate-50/60 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 opacity-80"
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                              {req.request_code}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                                isAdd
                                  ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300"
                                  : "bg-red-100 dark:bg-red-950 text-red-800 dark:text-red-300"
                              }`}
                            >
                              {isAdd ? "+ Add Inspector" : "- Remove Inspector"}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded-full font-semibold text-[10px] ${
                                isPending
                                  ? "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 animate-pulse"
                                  : req.status === "approved"
                                  ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300"
                                  : "bg-red-100 dark:bg-red-950 text-red-800 dark:text-red-300"
                              }`}
                            >
                              {isPending ? "Pending Admin Approval" : req.status.toUpperCase()}
                            </span>
                            <span className="text-[11px] text-slate-400">
                              {new Date(req.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        {/* Request Details */}
                        <div className="py-2.5 space-y-1.5">
                          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300 font-medium">
                            <span>Requested by: <strong>{req.officer_name || "District Officer"}</strong></span>
                          </div>

                          {isAdd ? (
                            <div className="bg-slate-100 dark:bg-slate-800 p-2.5 rounded-md font-mono text-[11px] space-y-0.5">
                              <div><strong>Name:</strong> {req.inspector_data?.full_name}</div>
                              <div><strong>Email:</strong> {req.inspector_data?.email}</div>
                              <div><strong>Inspector ID:</strong> {req.inspector_data?.inspector_id}</div>
                              <div><strong>District / State:</strong> {req.inspector_data?.district}, {req.inspector_data?.state}</div>
                              {req.inspector_data?.phone && <div><strong>Phone:</strong> {req.inspector_data?.phone}</div>}
                            </div>
                          ) : (
                            <div className="bg-slate-100 dark:bg-slate-800 p-2.5 rounded-md text-[11px]">
                              <strong>Target Officer for Revocation:</strong>{" "}
                              {req.target_inspector_name || req.inspector_data?.full_name}
                            </div>
                          )}

                          <p className="text-slate-600 dark:text-slate-400 text-xs">
                            <strong>Reason:</strong> {req.reason}
                          </p>

                          {req.admin_notes && (
                            <div className="mt-2 p-2 rounded bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-[11px]">
                              <span className="font-semibold text-slate-700 dark:text-slate-300">Admin Review Note:</span>{" "}
                              <span className="text-slate-600 dark:text-slate-400">{req.admin_notes}</span>
                            </div>
                          )}
                        </div>

                        {/* Admin Action Buttons */}
                        {isAdmin && isPending && (
                          <div className="pt-2.5 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
                            {reviewingId === req.id ? (
                              <div className="w-full space-y-2 bg-white dark:bg-slate-800 p-3 rounded border border-slate-300 dark:border-slate-700">
                                <label className="block font-semibold text-[11px] text-slate-700 dark:text-slate-300">
                                  Admin Decision Note (Optional):
                                </label>
                                <input
                                  type="text"
                                  value={adminReviewNotes}
                                  onChange={(e) => setAdminReviewNotes(e.target.value)}
                                  placeholder="e.g. Verified and approved for rural monitoring."
                                  className="w-full px-2.5 py-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-xs"
                                />
                                <div className="flex items-center justify-end gap-2">
                                  <button
                                    onClick={() => {
                                      setReviewingId(null);
                                      setReviewingAction(null);
                                      setAdminReviewNotes("");
                                    }}
                                    className="px-2.5 py-1 border border-slate-300 dark:border-slate-600 rounded text-xs"
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    disabled={submittingReview}
                                    onClick={handleProcessReview}
                                    className={`px-3 py-1 text-white rounded text-xs font-bold flex items-center gap-1 ${
                                      reviewingAction === "approve"
                                        ? "bg-emerald-600 hover:bg-emerald-700"
                                        : "bg-red-600 hover:bg-red-700"
                                    }`}
                                  >
                                    {submittingReview ? (
                                      <RefreshCw className="w-3 h-3 animate-spin" />
                                    ) : (
                                      <Check className="w-3 h-3" />
                                    )}
                                    Confirm {reviewingAction === "approve" ? "Approval" : "Rejection"}
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setReviewingId(req.id);
                                    setReviewingAction("reject");
                                    setAdminReviewNotes("");
                                  }}
                                  className="px-3 py-1.5 border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-950/50 rounded font-semibold text-xs flex items-center gap-1 cursor-pointer"
                                >
                                  <XCircle className="w-3.5 h-3.5" />
                                  Reject Request
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setReviewingId(req.id);
                                    setReviewingAction("approve");
                                    setAdminReviewNotes("");
                                  }}
                                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-bold text-xs flex items-center gap-1 cursor-pointer shadow-xs"
                                >
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  Approve & Execute
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
