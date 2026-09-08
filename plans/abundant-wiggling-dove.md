# Plan: Expense Bill Upload with AI Material Price Comparison & Dark/Light Theme Switcher

## Context & Motivation

In MPLADS and public infrastructure projects, a major source of financial leakage is material price over-invoicing and rate escalation fraud (e.g., claiming ₹650 per cement bag when standard market/CPWD benchmark is ₹380, or charging 2x market rates for TMT rebar steel).

The user requested two major capabilities:
1. **Expense Bill Upload & AI Material Price Anomaly Detection**: An option in the Field Inspector dashboard and Project Forensic Dossier to upload project expense bills/material invoices, where AI compares line items against standard material price benchmarks, flags major fluctuations and price inflation, calculates a financial fraud risk score, and triggers alerts and audit events.
2. **Dark and Light Mode Theme Switcher**: A seamless, persistent theme toggle accessible in the navigation bar with complete dark and light mode styling across all pages.

---

## Architectural Design & Components

### Part 1: Backend AI Material Price Comparison & Anomaly Engine

#### 1. Models & Database Schema (`backend/app/models/models.py`)
- **`ExpenseBill` Model**:
  - `id`: UUID (String 36)
  - `bill_code`: Unique code (e.g. `BILL-2026-0042`)
  - `project_id`: Foreign key to `Project`
  - `inspector_user_id`: Foreign key to `User`
  - `vendor_name`: String (e.g., `Balaji Cement & Steel Traders`)
  - `invoice_number`: String (e.g., `INV-2026-8901`)
  - `bill_date`: DateTime
  - `total_amount`: Numeric(15, 2)
  - `file_url` / `file_name`: Uploaded bill document/receipt (optional)
  - `items`: JSON array of line items:
    ```json
    [
      {
        "item_name": "OPC 53 Grade Cement",
        "category": "cement",
        "quantity": 250,
        "unit": "bags",
        "claimed_unit_price": 580.0,
        "total_amount": 145000.0,
        "benchmark_unit_price": 380.0,
        "deviation_pct": 52.63,
        "status": "severe_inflation",
        "notes": "52.6% above CPWD Schedule of Rates (₹380/bag)"
      }
    ]
    ```
  - `overall_deviation_pct`: Float (weighted price inflation across all items)
  - `anomaly_score`: Float (0-100 risk score)
  - `fraud_risk_level`: String (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`)
  - `ai_analysis_summary`: Text
  - `status`: Enum (`verified`, `flagged_for_review`, `approved`, `rejected`)
  - `created_at`, `updated_at`

#### 2. Material Price Benchmark & AI Anomaly Service (`backend/app/services/material_prices.py`)
- Standardized CPWD / State Schedule of Rates benchmark database for civil materials:
  - **Cement (OPC 53 / PPC)**: ₹380 / bag (Tolerance: ±15%)
  - **TMT Rebar Steel (Fe500D / 550D)**: ₹62,000 / metric tonne (or ₹62/kg) (Tolerance: ±12%)
  - **River Sand / M-Sand**: ₹1,800 / cu.m (Tolerance: ±18%)
  - **Coarse Aggregate 20mm/40mm**: ₹1,200 / cu.m (Tolerance: ±15%)
  - **Red Clay Bricks (Class 1 / Fly Ash)**: ₹8.50 / brick (₹8,500/1000 nos) (Tolerance: ±15%)
  - **Ready Mix Concrete (RMC M25)**: ₹4,200 / cu.m (Tolerance: ±14%)
  - **Bitumen (VG-30)**: ₹48,000 / metric tonne (Tolerance: ±15%)
  - **Structural Steel (ISMB/Angles)**: ₹68,000 / metric tonne (Tolerance: ±12%)
  - **PVC / HDPE Pipes (110mm)**: ₹420 / meter (Tolerance: ±15%)
  - **Skilled Mason / Labor**: ₹850 / person-day (Tolerance: ±15%)
  - **Unskilled Helper Labor**: ₹550 / person-day (Tolerance: ±15%)
  - **Excavator / JCB**: ₹1,600 / hour (Tolerance: ±15%)
- **AI Anomaly Evaluation Logic**:
  - Calculates exact percentage deviation per item.
  - Tiers:
    - $\le 15\%$: `NORMAL`
    - $> 15\%$ and $\le 35\%$: `ELEVATED`
    - $> 35\%$ and $\le 60\%$: `SEVERE_INFLATION`
    - $> 60\%$: `FRAUD_RISK`
  - Calculates weighted anomaly score (0-100).
  - When anomaly score $> 40\%$, automatically creates an `Alert` with type `FINANCIAL_ANOMALY` or `CONTRACTOR_ANOMALY`.
  - Recalculates Project `expenditure` and updates `RiskScore`.

#### 3. New API Endpoints (`backend/app/api/routes/bills.py`)
- `POST /api/bills` or `POST /api/projects/{project_id}/bills`: Upload and analyze bill (accepts JSON line items or multipart form with invoice file).
- `GET /api/projects/{project_id}/bills`: List all expense bills and AI reports for a project.
- `GET /api/bills/{bill_id}`: Get full bill analysis and forensic breakdown.
- `GET /api/bills/benchmarks`: Fetch standard material rates and categories for frontend autocompletion.

---

### Part 2: Frontend Theme Switcher (Dark & Light Mode)

#### 1. Theme Context (`frontend/src/context/ThemeContext.tsx`)
- Provides `theme: "light" | "dark"`, `toggleTheme()`, and `setTheme()`.
- Reads initial preference from `localStorage.getItem("satark_theme")` with fallback to `window.matchMedia("(prefers-color-scheme: dark)")`.
- Updates `document.documentElement.classList.add("dark")` or removes it on toggle.
- Wraps app in `RootLayout` (`src/app/layout.tsx`).

#### 2. Tailwind Configuration (`frontend/src/app/globals.css`)
- Configure Tailwind v4 `@custom-variant dark (&:where(.dark, .dark *));` to ensure all `dark:` utility classes apply cleanly.
- Define dark mode color palette (Slate 900/950 backgrounds, Slate 800 cards, Slate 700 borders, crisp text hierarchy).

#### 3. Navbar Theme Toggle (`frontend/src/components/Navbar.tsx`)
- Sun/Moon icon toggle button with smooth micro-interactions, tooltips, and accessible keyboard support.

#### 4. Dark Mode Styling Across Pages
- Update `Navbar`, `DashboardPage`, `ProjectsPage`, `ProjectDetailPage`, `InspectionsPage`, `AlertsPage`, `AuditLogsPage`, `LoginPage`, and modals with `dark:` utility variants.

---

### Part 3: Frontend Expense Bill Upload & Material AI Comparison UI

#### 1. New Modal Component: `frontend/src/components/ExpenseBillModal.tsx`
- **Interactive Line Items Editor**:
  - Add/remove items with Name, Category selector, Quantity, Unit, Claimed Unit Price, Total.
  - Category auto-fills standard units and displays the CPWD standard benchmark price for reference.
- **Quick Preset Buttons (1-Click Demo for Hackathon Evaluation)**:
  - 🟢 *Load Standard Market Bill (Normal)*: All materials within normal market rates (₹380 cement, ₹62 steel, etc.).
  - 🔴 *Load Inflated Steel & Cement Bill (Fraud Anomaly)*: Cement at ₹620/bag (+63%), TMT Steel at ₹105/kg (+69%), triggering high risk alert.
  - 🟡 *Load Elevated Labor & Aggregate Bill*: Labor at ₹1,200 (+41%), Bricks at ₹12.50 (+47%).
- **File Upload Area**: Drag-and-drop or file picker for invoice receipts.
- **Live AI Analysis Preview**: Instant comparison metrics before and after submission.

#### 2. Project Forensic Dossier Expense Tab (`frontend/src/app/projects/[id]/page.tsx`)
- Dedicated **"Financial Auditing & Material Invoices"** section.
- Displays table of all submitted bills with:
  - Bill Code, Vendor, Date, Total Amount, Anomaly Score & Risk Badge.
  - Expandable line-item breakdown showing Claimed vs Benchmark Price, Deviation %, and AI Explanations.
  - "Upload New Bill" action button.

#### 3. Field Inspector Quick Action (`frontend/src/app/inspections/page.tsx` & `/dashboard`)
- "Upload Expense Bill" button on assigned project cards so inspectors can easily submit material invoices directly from the field.

#### 4. API Client Updates (`frontend/src/lib/api.ts`)
- Add interfaces: `ExpenseBillItem`, `ExpenseBillResponse`, `MaterialBenchmarkItem`.
- Add API methods: `createBill`, `getProjectBills`, `getBillDetails`, `getMaterialBenchmarks`.

---

## Verification Plan

1. **Backend Tests**:
   - Run `pytest` to test bill creation, material price deviation calculation, anomaly scoring, alert triggering, and project risk re-evaluation.
2. **Material Price AI Analysis Validation**:
   - Submit normal bill $\to$ verify `NORMAL` status, low anomaly score ($\le 15\%$), no fraud alert.
   - Submit inflated bill $\to$ verify `FRAUD_RISK` / `SEVERE_INFLATION`, anomaly score $> 50\%$, automatic `FINANCIAL_ANOMALY` alert generated in Alerts center.
3. **Theme Switcher Validation**:
   - Toggle Dark/Light mode in Navbar $\to$ verify dark classes applied to entire DOM, card backgrounds switch to slate-900, text remains high-contrast, theme persists upon browser refresh.
4. **Frontend Production Build**:
   - Run `npm run build` in `satark-mplads/frontend` to verify 0 TypeScript/Turbopack compilation errors.
