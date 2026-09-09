"""Enumeration types used across the SATARK-MPLADS platform."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    FIELD_INSPECTOR = "field_inspector"
    DISTRICT_OFFICER = "district_officer"
    AUDITOR = "auditor"


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    INSPECTOR_ASSIGNED = "inspector_assigned"
    INSPECTION_PENDING = "inspection_pending"
    UNDER_INSPECTION = "under_inspection"
    UNDER_REVIEW = "under_review"
    HIGH_RISK = "high_risk"
    ESCALATED = "escalated"
    COMPLETION_REQUESTED = "completion_requested"  # Inspector requested completion
    COMPLETED = "completed"
    CLOSED = "closed"


class ProjectType(str, enum.Enum):
    ROAD = "road"
    BRIDGE = "bridge"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    COMMUNITY_HALL = "community_hall"
    DRINKING_WATER = "drinking_water"
    SANITATION = "sanitation"
    ELECTRIFICATION = "electrification"
    OTHER = "other"


class AssignmentStatus(str, enum.Enum):
    ACTIVE = "active"
    REASSIGNED = "reassigned"
    COMPLETED = "completed"
    REVOKED = "revoked"


class InspectionStatus(str, enum.Enum):
    STARTED = "started"
    EVIDENCE_COLLECTED = "evidence_collected"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    REJECTED = "rejected"


class EvidenceStatus(str, enum.Enum):
    CAPTURED = "captured"
    PROCESSING = "processing"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertType(str, enum.Enum):
    EVIDENCE_MANIPULATION = "evidence_manipulation"
    DUPLICATE_EVIDENCE = "duplicate_evidence"
    GEOFENCE_VIOLATION = "geofence_violation"
    GPS_ACCURACY_LOW = "gps_accuracy_low"
    FINANCIAL_ANOMALY = "financial_anomaly"
    PROGRESS_MISMATCH = "progress_mismatch"
    SATELLITE_MISMATCH = "satellite_mismatch"
    CONTRACTOR_ANOMALY = "contractor_anomaly"
    RISK_SCORE_CHANGE = "risk_score_change"


class RiskLevel(str, enum.Enum):
    LOW = "low"           # 0-29
    MODERATE = "moderate"  # 30-59
    HIGH = "high"          # 60-79
    CRITICAL = "critical"  # 80-100


class SummonsStatus(str, enum.Enum):
    PENDING = "pending"
    RESPONDED = "responded"
    REVIEWED = "reviewed"
    CLOSED = "closed"


class ExpenseBillStatus(str, enum.Enum):
    VERIFIED = "verified"
    FLAGGED = "flagged"
    APPROVED = "approved"
    REJECTED = "rejected"


class InspectorRequestType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"


class InspectorRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


