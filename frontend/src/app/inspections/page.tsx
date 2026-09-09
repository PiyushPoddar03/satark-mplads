"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, ProjectItem, SummonsItem } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { StatusBadge, RiskBadge } from "@/components/StatusBadge";
import { LiveCameraModal } from "@/components/LiveCameraModal";
import { ExpenseBillModal } from "@/components/ExpenseBillModal";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Clock,
  FileCheck,
  FileText,
  FolderKanban,
  MapPin,
  Navigation,
  Receipt,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function InspectionsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [summonsList, setSummonsList] = useState<SummonsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<ProjectItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Expense Bill Modal state
  const [billModalProject, setBillModalProject] = useState<ProjectItem | null>(null);

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push("/login");
        return;
      }
      if (user.role !== "field_inspector" && user.role !== "admin") {
        router.push("/dashboard");
        return;
      }
    }

    loadAssignedProjects();
  }, [user, authLoading, router]);

  const loadAssignedProjects = async () => {
    try {
      setLoading(true);
      const [projRes, summonsRes] = await Promise.all([
        api.getProjects(),
        api.getSummons("pending").catch(() => []),
      ]);
      setProjects(projRes.projects);
      setSummonsList(summonsRes);
    } catch (err) {
      console.error("Failed to load assigned projects:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartInspection = (project: ProjectItem) => {
    setSelectedProject(project);
    setIsModalOpen(true);
  };

  const handleInspectionComplete = (inspectionId: string) => {
    setSuccessMessage(
      `Inspection successfully submitted! AI Forensics and Risk Engine evaluation completed.`
    );
    setTimeout(() => setSuccessMessage(null), 6000);
    loadAssignedProjects();
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Camera className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
              Live Field Evidence & Material Expense Audit
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
              Authorized field inspections with hardware-enforced GPS geofencing & SHA-256 evidence integrity
            </p>
          </div>

          <div className="flex items-center gap-2 bg-indigo-50 dark:bg-indigo-950/70 border border-indigo-200 dark:border-indigo-900/60 px-3 py-1.5 rounded-lg text-xs text-indigo-800 dark:text-indigo-300">
            <ShieldCheck className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <span>Inspector ID: <strong className="font-mono">{user?.inspector_id || "ADMIN-OVERRIDE"}</strong></span>
          </div>
        </div>

        {/* Success Alert Banner */}
        {successMessage && (
          <div className="mb-6 p-4 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 rounded-lg flex items-center gap-3 text-emerald-800 dark:text-emerald-300 shadow-sm animate-fade-in">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <div className="text-sm font-medium">{successMessage}</div>
          </div>
        )}

        {/* Assigned Projects Grid */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Authorized Projects for On-Site Verification ({projects.length})
          </h2>

          {projects.length === 0 ? (
            <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-12 text-center shadow-sm">
              <FolderKanban className="w-12 h-12 text-slate-400 dark:text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">No Projects Assigned</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                You currently have no active project assignments in your designated district.
              </p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-all flex flex-col justify-between overflow-hidden"
                >
                  <div className="p-5">
                    {/* Header Badges */}
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="font-mono text-xs font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700">
                        {project.project_code}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {summonsList.some((s) => s.project_id === project.id && s.status === "pending") && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 rounded text-[10px] font-bold">
                            <AlertTriangle className="w-3 h-3" />
                            Summons Pending
                          </span>
                        )}
                        <StatusBadge status={project.status} />
                      </div>
                    </div>

                    {/* Title */}
                    <h3 className="font-bold text-slate-900 dark:text-white text-base line-clamp-2 mt-1">
                      {project.name}
                    </h3>

                    {/* Location & Geofence info */}
                    <div className="mt-3 space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="line-clamp-1">{project.village_locality}, {project.district}</span>
                      </div>
                      <div className="flex items-center gap-1.5 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                        <Navigation className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>Lat: {project.latitude.toFixed(4)}, Lon: {project.longitude.toFixed(4)}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] text-indigo-700 dark:text-indigo-300 bg-indigo-50/70 dark:bg-indigo-950/50 px-2 py-0.5 rounded font-medium border border-indigo-100 dark:border-indigo-900/40">
                        <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
                        <span>Geofence Radius: {project.inspection_radius_m} meters</span>
                      </div>
                    </div>

                    {/* Progress Metrics */}
                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-400 block text-[11px]">Physical Progress</span>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <div className="flex-1 bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-indigo-600 h-full rounded-full"
                              style={{ width: `${project.physical_progress}%` }}
                            ></div>
                          </div>
                          <span className="font-semibold text-slate-800 dark:text-slate-200 text-[11px]">{project.physical_progress}%</span>
                        </div>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Sanction Amount</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5 block">
                          ₹{(project.sanction_amount / 100000).toFixed(1)} Lakhs
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions footer */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-850 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
                    <Link
                      href={`/projects/${project.id}`}
                      className="text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white font-medium flex items-center gap-1"
                    >
                      {summonsList.some((s) => s.project_id === project.id && s.status === "pending") ? (
                        <span className="text-amber-700 dark:text-amber-400 font-semibold flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" /> Submit Report →
                        </span>
                      ) : (
                        "View Dossier →"
                      )}
                    </Link>

                    <div className="flex items-center gap-2">
                      {user?.role === "field_inspector" && (
                        <button
                          onClick={() => setBillModalProject(project)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-200 dark:bg-slate-750 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 rounded text-xs font-semibold transition-colors cursor-pointer"
                          title="Upload Vendor Invoice & Check Material Prices with AI"
                        >
                          <Receipt className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                          Upload Bill
                        </button>
                      )}

                      <button
                        onClick={() => handleStartInspection(project)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                      >
                        <Camera className="w-3.5 h-3.5" />
                        Live Capture
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Live Camera Modal */}
      {selectedProject && (
        <LiveCameraModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedProject(null);
          }}
          project={selectedProject}
          onInspectionComplete={handleInspectionComplete}
        />
      )}

      {/* Expense Bill Modal */}
      {billModalProject && (
        <ExpenseBillModal
          projectId={billModalProject.id}
          projectCode={billModalProject.project_code}
          projectName={billModalProject.name}
          isOpen={!!billModalProject}
          onClose={() => setBillModalProject(null)}
          onSuccess={() => {
            setSuccessMessage("Expense bill uploaded and audited against CPWD benchmarks successfully!");
            setTimeout(() => setSuccessMessage(null), 6000);
            loadAssignedProjects();
          }}
        />
      )}
    </div>
  );
}
