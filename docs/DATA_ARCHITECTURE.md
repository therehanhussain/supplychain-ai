# SupplyChainAgent: Data Architecture & Storage Classification

**Document Version:** 1.0.0  
**Phase:** Phase 3 — Architecture & Data Boundary Definition  
**Status:** Canonical Reference  

---

## 1. Overview & Core Tenet

In Phase 3, we adhere strictly to the principle: **Do NOT perform a blanket database rewrite.**
The existing heterogeneous data layer combines PostgreSQL, Neo4j, MLflow, and transient memory structures. Each storage engine serves a distinct domain function where it provides superior performance or structural alignment.

This document classifies all system data into three distinct tiers, defining schema contracts, access models, and transition pathways.

---

## 2. Three-Tier Data Classification

```mermaid
flowchart LR
    subgraph ClientData [Application & Ingress]
        API[FastAPI Backend /api/v1/*]
    end

    subgraph RelationalTier [PostgreSQL 15+]
        Users[Users, Roles & Tenancy]
        Suppliers[Supplier Master Data]
        Inventory[Inventory Balances & SKUs]
        Orders[Purchase & Sales Orders]
        Shipments[Shipments & Carrier Records]
        Alerts[System Alerts & Disruptions]
        Audit[Audit Trails & Access Logs]
        ExpMeta[Experiment Metadata & Steps]
    end

    subgraph GraphTier [Neo4j Graph Database]
        CompanyNodes[Enterprise Nodes]
        SuppliesRel[[:SUPPLIES] Multi-Tier Edges]
        BOM[Material Composition Trees]
        PropModel[Disruption Propagation Paths]
    end

    subgraph TelemetryTier [MLflow & Experiment Metrics]
        RunLogs[MLflow Runs & Run UUIDs]
        Params[Agent Intelligence & Hyperparameters]
        TimeSeries[Time-Series Metrics per Step]
        AgentStates[Snapshot States & Raw Dialogs]
    end

    API --> RelationalTier
    API --> GraphTier
    API --> TelemetryTier
```

---

## 3. Tier 1: Relational Data Tier (PostgreSQL)

PostgreSQL serves as the system of record for structured transactional, identity, organizational, and audit data requiring ACID guarantees.

### 3.1 Data Entities & Scope
* **Users, Roles & Organizations**: Multi-tenant organization boundaries, user accounts, hashed passwords, RBAC permissions (`admin`, `operator`, `viewer`).
* **Supplier Master Records**: Formal supplier catalog, tier levels (Tier 1, Tier 2, Tier 3), geographical locations, compliance statuses, and rating scores.
* **Inventory Master & Stock**: Material IDs, product names, warehouse SKU balances, reserved quantities, reorder thresholds, and unit costs.
* **Order & Transaction Records**: Purchase orders, sales deals, agreed unit prices, quantities, payment terms, delivery schedules, and lifecycle states (`pending`, `confirmed`, `in_transit`, `fulfilled`, `cancelled`).
* **Shipments & Logistics**: Logistics tracking, origins, destinations, carrier assignments, estimated delivery windows, and shipment events.
* **Alerts & Audit Logs**: Real-time supply chain bottleneck alerts, price spike warnings, and user action audit trails (`timestamp`, `user_id`, `action`, `resource_id`, `ip_address`).
* **Historical Experiment Structure**: Experiment runs table (`as_experiment`), company state snapshots (`company_states`), and communication exchange logs (`company_records`).

### 3.2 Access Pattern
* Primary client: SQLAlchemy async engine (`asyncpg` / `psycopg`) with connection pooling.
* Access abstraction: `backend/app/repositories/` implementing clean CRUD and query pagination.

---

## 4. Tier 2: Graph Relationship Tier (Neo4j)

Neo4j is the dedicated graph engine for non-relational, highly connected topological supply chain structures. Relational databases struggle with arbitrary-depth graph traversals (e.g. finding 4th-tier supplier bottlenecks); Neo4j excels at this via native graph storage and Cypher index-free adjacency.

### 4.1 Data Entities & Scope
* **Enterprise Nodes (`(:Company)`)**:
  * Labels: `level1_company`, `level2_company`, `level3_company`, `terminal_company`.
  * Node Attributes: `company_id`, `name`, `level`, `initial_inventory`, `avg_profit_margin`.
* **Supply Relationships (`[:SUPPLIES]`)**:
  * Directed edges: `(Supplier)-[:SUPPLIES]->(Consumer)`.
  * Edge Attributes: `material_id`, `material_name`, `for_product_id`, `for_product_name`, `supply_price`, `available_inventory`, `usage_ratio`, `cost_contribution`, `product_construct`.
* **BOM (Bill of Materials) Trees**: Multi-level product recipe decomposition (e.g., *Product A = Material 1 (74%) + Material 4 (26%)*).
* **Topological Disruption Impact**: Real-time graph traversal to calculate blast radius when an upstream supplier fails or experiences lead-time delays.

### 4.2 Access Pattern
* Primary client: Neo4j Python Driver with Bolt protocol.
* Query mechanism: Strictly parameterized Cypher queries wrapped inside `backend/app/services/neo4j_service.py`.
* Offline Fallback: In local dev or CI without a running Neo4j instance, graph endpoints automatically read cached static topology fixtures (`industry_test.json`).

---

## 5. Tier 3: Experiment & Telemetry Tier (MLflow / Time-Series)

Simulations produce high-volume time-series telemetry, dynamic parameter logs, and agent negotiation histories across tens or hundreds of iterative steps.

### 5.1 Data Entities & Scope
* **Run Metadata**: MLflow run UUIDs, experiment associations, start/end timestamps, and execution statuses.
* **Agent Parameters**: Static hyperparameters logged per enterprise at experiment initialization (e.g., `intelligence_level_{agent_name}`, `initial_cash_{agent_name}`).
* **Step Metrics**: Time-series metrics logged at every round:
  * `company_fund_{agent_name}`
  * `material_inventory_ratio_{agent_name}`
  * `product_inventory_ratio_{agent_name}`
  * `net_transaction_amount_{agent_name}`
  * `supply_total_quantity_{agent_name}`, `supply_total_amount_{agent_name}`, `supply_total_orders_{agent_name}`
  * `purchase_total_quantity_{agent_name}`, `purchase_total_amount_{agent_name}`, `purchase_total_orders_{agent_name}`
* **Agent Dialog & Thinking Logs**: Step-by-step reflection transcripts and negotiation dialogs between autonomous agents.

### 5.2 Access Pattern
* Primary client: MLflow Client & direct analytical query interfaces (`LatestExperimentQuery`) wrapped in `backend/app/repositories/experiment_repo.py`.
* Output: Visual analytics consumed by the Frontend Replay player and Console dashboards.

---

## 6. Data Integrity & Migration Boundaries

```text
┌───────────────────────────────┐
│     FastAPI Presentation      │
├───────────────────────────────┤
│    Domain Services Layer      │
│  (SupplyChain, Neo4j, LLM)    │
├───────────────┬───────────────┤
│ PostgreSQL    │ Neo4j Graph   │
│ Repositories  │ Service       │
│ (Transactional│ (Topological  │
│  & Audit)     │  Traversal)   │
└───────────────┴───────────────┘
```

1. **Transactional vs. Graph Separation**:
   * Master records (e.g., current inventory quantity, supplier business address) live in PostgreSQL.
   * Connectivity structure (who supplies whom and with what usage ratio) lives in Neo4j.
   * Graph node attributes point to PostgreSQL IDs (`company_id`, `product_id`, `material_id`) maintaining clean referential integrity without cross-database foreign key coupling.
2. **Preservation of Existing Schemas**:
   * Tables `as_experiment`, `company_states`, `company_records`, and `company_transaction_lists` remain active in PostgreSQL.
   * New schemas (`users`, `suppliers`, `inventory_items`, `orders`, `shipments`, `alerts`) are introduced as cleanly typed SQLAlchemy models alongside the legacy tables.
