# SupplyChainAgent: Frontend Architecture & Comprehensive Audit

**Document Version:** 1.0.0  
**Phase:** Frontend-First Review, Redesign & Production UI  
**Date:** September 2026  
**Auditor:** Lead Production Frontend Engineer  

---

## 1. Executive Summary

This document audits the existing frontend application located under `frontend/` (built with React 18, Vite 6, TypeScript 5.6, Ant Design 5.22, `@antv/g6` 4.8, and `@ant-design/pro-components`). 

The current application functions primarily as a research-stage multi-agent experiment runner and simulation replay player. While it features sophisticated graph visualization (`IndustryGraph.tsx`) and spatial replay capabilities (`Replay/Deck.tsx`), it lacks the unified information architecture, operational workflows, and visual polish of a professional, enterprise-grade **Supply Chain Control Tower SaaS**.

---

## 2. Inventory of Existing Pages & Routes

| Path | Component File | Current Role | Data Source | Status |
|:---|:---|:---|:---|:---:|
| `/` | `src/pages/Home/index.tsx` | Research landing page with hero banner & quick links | Static content | Prototype |
| `/console` | `src/pages/Console/index.tsx` | Experiment run history table with tokens & day counts | `/api/experiments` (SQLite bridge) | Functional Bridge |
| `/exp/:id` / `/replay/:id` | `src/pages/Replay/index.tsx` | Interactive spatial replay player with Deck.gl map, timeline, info panel, and chat | `/api/experiments/{id}/*` | Functional Bridge |
| `/industry` | `src/pages/maps/IndustryGraph.tsx` | Multi-tier supply chain network topology (AntV G6) | `/api/v1/routes` or fallback file | Functional (Migrated) |
| `/create-experiment` | `src/pages/Experiment/CreateExperiment.tsx` | Step-based experiment configuration wizard | Browser `localForage` | Prototype |
| `/llms` | `src/pages/Experiment/LLMList.tsx` | List and modal editor for LLM API configurations | Browser `localForage` | Prototype |
| `/agents` | `src/pages/Experiment/AgentList.tsx` | Configuration cards for firm, bank, government agents | Browser `localForage` | Prototype |
| `/workflows` | `src/pages/Experiment/WorkflowList.tsx` | Simulation step sequence configuration | Browser `localForage` | Prototype |
| `/survey` | `src/pages/Survey/index.tsx` | SurveyJS creator and questionnaire manager | `/api/surveys` / in-memory | Functional Bridge |

---

## 3. Existing Component & Styling Architecture

* **UI Framework**: Ant Design 5.22.5 (`antd`) paired with `@ant-design/icons` and `@ant-design/pro-components`.
* **Current Theme Configuration (`main.tsx`)**:
  * `colorPrimary`: `#0000CC` (Harsh, high-saturation blue lacking enterprise subtlety).
  * `borderRadius`: `16px` (Excessively rounded for high-density enterprise data tables and control towers).
  * `colorBgLayout`: `#FFFFFF` (Flat white background eliminating depth between cards and layout shell).
* **Graph & Data Visualization**:
  * `@antv/g6` 4.8.24: Powering interactive node-edge diagrams with dagre layout, level-based coloring, and custom node cards.
  * `@deck.gl/react` & `mapbox-gl`: High-performance geospatial rendering for agent coordinates.

---

## 4. Audit Findings & Gap Analysis

### 4.1 Missing Core Control Tower Modules
The backend API exposes rich, verified production endpoints that are completely absent from the frontend UI:
1. **Executive Overview Dashboard**: No unified bird's-eye view showing active supplier counts, inventory health, pending orders, in-transit shipments, or critical disruption alerts.
2. **Supplier Management**: No interface consuming `/api/v1/suppliers` (CRUD, risk ratings, tier badges, contact info).
3. **Inventory Operations**: No interface consuming `/api/v1/inventory` (SKU stock balances, warehouse allocation, reorder points, low-stock warnings).
4. **Purchase & Sales Orders**: No interface consuming `/api/v1/orders` (PO tracking, order items, customer details, fulfillment status).
5. **Logistics & Shipments**: No interface consuming `/api/v1/shipments` (carrier telemetry, route origins/destinations, delay risks).
6. **Risk & Disruption Intelligence**: No interface consuming `/api/v1/risk` or triggering `/api/v1/risk/analyze-disruption` simulations.
7. **Demand Forecasting**: No interface consuming `/api/v1/forecast`.
8. **Asynchronous Simulation Manager**: No interface allowing operators to launch, monitor (`QUEUED` -> `RUNNING` -> `COMPLETED`), and abort (`CANCELLED`) simulations via `/api/v1/agents/simulations`.

### 4.2 Navigation & App Shell UX Flaws
* **Header-Only Navigation**: Navigation is currently cramped in a single top header bar with nested dropdown menus. It cannot scale to enterprise multi-module workflows.
* **Absence of Sidebar**: Professional control towers require a collapsible, semantic sidebar organizing modules into distinct functional groups:
  * **Control Tower** (Overview, Network Graph)
  * **Operations** (Suppliers, Inventory, Orders, Shipments)
  * **Intelligence & AI** (Risk Analysis, Forecasting, Simulations)
  * **System** (Configuration, Audit Logs)
* **Missing User & Tenant Context**: No display of active user identity, organization name, or RBAC role (`ADMIN`, `OPERATOR`, `ANALYST`, `VIEWER`).
* **Vite Proxy Port Mismatch**: `vite.config.ts` proxies `/api` to `http://localhost:8080`, whereas the unified production backend runs on `http://localhost:8000`.

### 4.3 Data Provenance & Honesty Issues
* Several components do not visibly inform the operator whether data is **LIVE** (from PostgreSQL / Neo4j cluster), **FALLBACK** (from local static JSON), or **SIMULATED / DEMO**.
* Offline fallback datasets are occasionally rendered without status badges.

### 4.4 Responsive Design & Mobile Limitations
* Navigation bar collapses poorly on tablet/mobile screens.
* Tables lack horizontal scrolling containers on narrow viewports.
* Graph canvas in `IndustryGraph.tsx` does not resize dynamically when window dimensions shift.

### 4.5 Accessibility (a11y)
* Semantic landmarks (`<header>`, `<nav>`, `<main>`, `<aside>`) are inconsistently applied.
* Contrast ratio of white text on `#0000CC` primary buttons is acceptable, but secondary link states have low contrast.
* Dialog modals lack explicit `aria-describedby` associations.

---

## 5. Modernization Strategy

1. **Enterprise Design System**:
   * Professional color palette: Slate `#0F172A`, Enterprise Navy `#1E40AF`, Slate 50/100 layout backgrounds.
   * Tight border radii (`6px` / `8px`) for high-density information architecture.
   * Universal component wrappers for KPI Metric Cards, Status Badges, and Data Source Provenance Tags (`LIVE`, `SIMULATED`, `DEMO`).
2. **Global App Shell**:
   * Fixed collapsible sidebar with categorized sections.
   * Top app bar with breadcrumbs, organization selector, live system status beacon, and user profile avatar with RBAC badge.
   * Seamless mobile drawer navigation.
3. **Module Implementations**:
   * Build unified, real-API-connected views for Overview, Suppliers, Inventory, Orders, Shipments, Risk, Forecast, and Simulations.
   * Preserve all existing simulation replay player (`/exp/:id`) and industry graph (`/industry`) functionality.
4. **Data Honesty**:
   * Every screen must explicitly show a **Provenance Badge** (`LIVE BACKEND`, `OFFLINE FALLBACK`, or `DEMO MODE`).
