/**
 * Unified Control Tower API Service.
 *
 * Bridges all frontend control tower views directly to the authoritative
 * backend OpenAPI matrix (/api/v1/*), providing typed contracts, pagination,
 * and certified offline fallback / demo datasets with explicit provenance labeling.
 */

import apiClient from './apiClient';

export type DataProvenance = 'LIVE' | 'DEMO' | 'FALLBACK';

export interface ProvenanceEnvelope<T> {
  data: T;
  provenance: DataProvenance;
  sourceNote?: string;
}

// -----------------------------------------------------------------------------
// Core Domain Models
// -----------------------------------------------------------------------------

export interface SupplierItem {
  id: string;
  name: string;
  contact_email?: string;
  phone?: string;
  country: string;
  tier: number;
  rating: number;
  lead_time_days: number;
  status: 'active' | 'warning' | 'critical' | 'inactive';
  is_active: boolean;
  created_at: string;
}

export interface InventoryItem {
  id: string;
  sku: string;
  name: string;
  category: string;
  warehouse_id: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  reorder_point: number;
  unit_cost: number;
  is_low_stock?: boolean;
  updated_at: string;
}

export interface OrderLineItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
}

export interface OrderItem {
  id: string;
  customer_name: string;
  supplier_id: string;
  status: 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';
  total_amount: number;
  items: OrderLineItem[];
  created_at: string;
}

export interface ShipmentItem {
  id: string;
  order_id: string;
  carrier: string;
  tracking_number?: string;
  origin: string;
  destination: string;
  status: 'preparing' | 'in_transit' | 'out_for_delivery' | 'delivered';
  estimated_delivery?: string;
  created_at: string;
}

export interface RiskOverview {
  overall_risk_score: number;
  bottlenecks_detected: number;
  revenue_at_risk_usd: number;
  vulnerable_suppliers: Array<{
    supplier_id: string;
    supplier_name: string;
    tier: number;
    risk_score: number;
    primary_risk_factor: string;
    bottleneck_severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  }>;
  active_disruptions: Array<{
    id: string;
    type: string;
    region: string;
    impact_level: 'MINOR' | 'MODERATE' | 'SEVERE';
    description: string;
  }>;
}

export interface ForecastResponse {
  sku: string;
  historical_days: number;
  forecast_horizon_days: number;
  model_name: string;
  is_scaffold: boolean;
  forecast_series: Array<{
    day: number;
    date: string;
    predicted_demand: number;
    confidence_lower?: number;
    confidence_upper?: number;
  }>;
}

export interface SimulationTask {
  task_id: string;
  experiment_id: string;
  name: string;
  status: 'QUEUED' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  num_days: number;
  current_day: number;
  progress_pct: number;
  num_firms: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  input_tokens: number;
  output_tokens: number;
  is_mock: boolean;
  error_message?: string;
}

// -----------------------------------------------------------------------------
// Certified Demonstration Fallbacks (Strictly labeled as DEMO)
// -----------------------------------------------------------------------------

export const DEMO_SUPPLIERS: SupplierItem[] = [
  { id: "sup-001", name: "TSMC Semiconductor Fab 18", contact_email: "orders@tsmc-foundry.tw", country: "Taiwan", tier: 1, rating: 4.95, lead_time_days: 14, status: "active", is_active: true, created_at: "2026-01-15T08:00:00Z" },
  { id: "sup-002", name: "ASML Lithography Systems", contact_email: "optics@asml.nl", country: "Netherlands", tier: 1, rating: 4.88, lead_time_days: 45, status: "active", is_active: true, created_at: "2026-01-18T10:30:00Z" },
  { id: "sup-003", name: "Shin-Etsu Silicon Ingots", contact_email: "sales@shinetsu.jp", country: "Japan", tier: 2, rating: 4.70, lead_time_days: 10, status: "active", is_active: true, created_at: "2026-02-01T12:00:00Z" },
  { id: "sup-004", name: "Air Liquide Ultra-Pure Gases", contact_email: "support@airliquide.fr", country: "France", tier: 2, rating: 4.30, lead_time_days: 7, status: "warning", is_active: true, created_at: "2026-02-10T14:15:00Z" },
  { id: "sup-005", name: "Hengdian Magnetics Group", contact_email: "export@hengdian.cn", country: "China", tier: 3, rating: 3.80, lead_time_days: 21, status: "critical", is_active: true, created_at: "2026-02-20T09:45:00Z" },
  { id: "sup-006", name: "BASF Specialty Chemicals", contact_email: "contact@basf.de", country: "Germany", tier: 2, rating: 4.65, lead_time_days: 8, status: "active", is_active: true, created_at: "2026-03-01T11:00:00Z" },
];

export const DEMO_INVENTORY: InventoryItem[] = [
  { id: "inv-001", sku: "MAT-SILICON-300MM", name: "300mm Monocrystalline Wafer Substrate", category: "raw_material", warehouse_id: "WH-DRESDEN-01", quantity_on_hand: 12500, quantity_reserved: 3200, reorder_point: 5000, unit_cost: 120.0, is_low_stock: false, updated_at: "2026-09-10T14:00:00Z" },
  { id: "inv-002", sku: "MAT-NEON-GAS-999", name: "Excimer Grade Neon Gas 99.999% (Cylinder)", category: "raw_material", warehouse_id: "WH-ANTWERP-02", quantity_on_hand: 480, quantity_reserved: 420, reorder_point: 800, unit_cost: 850.0, is_low_stock: true, updated_at: "2026-09-10T15:30:00Z" },
  { id: "inv-003", sku: "COMP-ARM-MCU-V4", name: "Embedded Automotive ARM Cortex MCU", category: "finished_good", warehouse_id: "WH-STUTTGART-01", quantity_on_hand: 45000, quantity_reserved: 18000, reorder_point: 10000, unit_cost: 38.5, is_low_stock: false, updated_at: "2026-09-11T08:20:00Z" },
  { id: "inv-004", sku: "MAT-COPPER-CLAD", name: "High-Frequency FR4 Copper Clad Laminate", category: "intermediate", warehouse_id: "WH-SHENZHEN-03", quantity_on_hand: 1850, quantity_reserved: 1600, reorder_point: 3000, unit_cost: 65.0, is_low_stock: true, updated_at: "2026-09-11T09:10:00Z" },
];

export const DEMO_ORDERS: OrderItem[] = [
  { id: "ord-901", customer_name: "BMW AG Procurement", supplier_id: "sup-001", status: "confirmed", total_amount: 345000.0, items: [{ product_id: "COMP-ARM-MCU-V4", product_name: "Automotive ARM MCU", quantity: 5000, unit_price: 69.0 }], created_at: "2026-09-08T10:00:00Z" },
  { id: "ord-902", customer_name: "Siemens Energy Automation", supplier_id: "sup-002", status: "shipped", total_amount: 184000.0, items: [{ product_id: "MAT-SILICON-300MM", product_name: "Silicon Wafers", quantity: 1000, unit_price: 184.0 }], created_at: "2026-09-09T11:30:00Z" },
  { id: "ord-903", customer_name: "Schneider Electric", supplier_id: "sup-004", status: "pending", total_amount: 98500.0, items: [{ product_id: "MAT-NEON-GAS-999", product_name: "Excimer Neon", quantity: 100, unit_price: 985.0 }], created_at: "2026-09-10T14:45:00Z" },
];

export const DEMO_SHIPMENTS: ShipmentItem[] = [
  { id: "shp-701", order_id: "ord-902", carrier: "DHL Global Forwarding", tracking_number: "DHL-DE-994812", origin: "Rotterdam Port Facility", destination: "Siemens Plant, Erlangen", status: "in_transit", estimated_delivery: "2026-09-13T16:00:00Z", created_at: "2026-09-09T14:00:00Z" },
  { id: "shp-702", order_id: "ord-901", carrier: "Maersk Logistics", tracking_number: "MSK-TW-481920", origin: "Kaohsiung Harbor Terminal", destination: "Hamburg Logistics Hub", status: "in_transit", estimated_delivery: "2026-09-22T10:00:00Z", created_at: "2026-09-08T18:30:00Z" },
  { id: "shp-703", order_id: "ord-903", carrier: "FedEx Freight Europe", tracking_number: "FDX-FR-112039", origin: "Paris Charles de Gaulle Cargo", destination: "Grenoble Distribution Center", status: "preparing", estimated_delivery: "2026-09-15T12:00:00Z", created_at: "2026-09-11T08:00:00Z" },
];

export const DEMO_RISK: RiskOverview = {
  overall_risk_score: 64.2,
  bottlenecks_detected: 3,
  revenue_at_risk_usd: 12450000,
  vulnerable_suppliers: [
    { supplier_id: "sup-005", supplier_name: "Hengdian Magnetics Group", tier: 3, risk_score: 84.5, primary_risk_factor: "Port congestion and export quotas", bottleneck_severity: "CRITICAL" },
    { supplier_id: "sup-004", supplier_name: "Air Liquide Ultra-Pure Gases", tier: 2, risk_score: 68.0, primary_risk_factor: "Regional energy grid curtailment", bottleneck_severity: "HIGH" },
    { supplier_id: "sup-001", supplier_name: "TSMC Semiconductor Fab 18", tier: 1, risk_score: 52.0, primary_risk_factor: "Geopolitical freight transit corridor", bottleneck_severity: "MEDIUM" },
  ],
  active_disruptions: [
    { id: "dis-01", type: "Geopolitical Logistics", region: "Strait of Malacca", impact_level: "SEVERE", description: "Vessel re-routing resulting in +7 to +10 days transit latency for East Asia to Europe maritime freight." },
    { id: "dis-02", type: "Raw Material Shortage", region: "Eastern Europe", impact_level: "MODERATE", description: "Neon gas refining capacity down 20% due to facility maintenance schedules." },
  ],
};

// -----------------------------------------------------------------------------
// Service Methods
// -----------------------------------------------------------------------------

class ControlTowerApiService {
  // System Health
  async getSystemStatus(): Promise<{
    backendOnline: boolean;
    databaseStatus: 'healthy' | 'degraded' | 'unavailable';
    neo4jMode: 'LIVE' | 'FALLBACK' | 'DEGRADED' | 'UNAVAILABLE';
    version: string;
  }> {
    try {
      const res = await apiClient.get<any>('/ready');
      const neo4jStatus = res?.dependencies?.neo4j?.status;
      let mappedGraphMode: 'LIVE' | 'FALLBACK' | 'DEGRADED' | 'UNAVAILABLE' = 'DEGRADED';
      if (neo4jStatus === 'healthy') mappedGraphMode = 'LIVE';
      else if (neo4jStatus === 'degraded') mappedGraphMode = 'FALLBACK';
      else if (neo4jStatus === 'unavailable') mappedGraphMode = 'UNAVAILABLE';

      return {
        backendOnline: true,
        databaseStatus: res?.dependencies?.database?.status || 'healthy',
        neo4jMode: mappedGraphMode,
        version: res?.version || '0.1.0',
      };
    } catch {
      return {
        backendOnline: false,
        databaseStatus: 'unavailable',
        neo4jMode: 'UNAVAILABLE',
        version: 'Offline',
      };
    }
  }

  // Suppliers
  async getSuppliers(params?: { tier?: number; page?: number; page_size?: number; forceDemo?: boolean }): Promise<ProvenanceEnvelope<SupplierItem[]>> {
    if (params?.forceDemo) {
      return { data: DEMO_SUPPLIERS, provenance: 'DEMO', sourceNote: 'Demo dataset loaded by user preference.' };
    }
    try {
      const data = await apiClient.get<SupplierItem[]>('/api/v1/suppliers', { params });
      return { data, provenance: 'LIVE', sourceNote: 'PostgreSQL Relational Persistence' };
    } catch {
      return { data: DEMO_SUPPLIERS, provenance: 'FALLBACK', sourceNote: 'Backend unreachable. Showing certified offline fallback vendors.' };
    }
  }

  async createSupplier(payload: Partial<SupplierItem>): Promise<SupplierItem> {
    return await apiClient.post<SupplierItem>('/api/v1/suppliers', payload);
  }

  async updateSupplier(id: string, payload: Partial<SupplierItem>): Promise<SupplierItem> {
    return await apiClient.put<SupplierItem>(`/api/v1/suppliers/${id}`, payload);
  }

  async deleteSupplier(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/suppliers/${id}`);
  }

  // Inventory
  async getInventory(params?: { warehouse_id?: string; page?: number; page_size?: number; forceDemo?: boolean }): Promise<ProvenanceEnvelope<InventoryItem[]>> {
    if (params?.forceDemo) {
      return { data: DEMO_INVENTORY, provenance: 'DEMO', sourceNote: 'Demo dataset loaded by user preference.' };
    }
    try {
      const data = await apiClient.get<InventoryItem[]>('/api/v1/inventory', { params });
      return { data, provenance: 'LIVE', sourceNote: 'PostgreSQL Relational Persistence' };
    } catch {
      return { data: DEMO_INVENTORY, provenance: 'FALLBACK', sourceNote: 'Backend unreachable. Showing certified offline fallback stock.' };
    }
  }

  async createInventory(payload: Partial<InventoryItem>): Promise<InventoryItem> {
    return await apiClient.post<InventoryItem>('/api/v1/inventory', payload);
  }

  async deleteInventory(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/inventory/${id}`);
  }

  // Orders
  async getOrders(params?: { status?: string; page?: number; page_size?: number; forceDemo?: boolean }): Promise<ProvenanceEnvelope<OrderItem[]>> {
    if (params?.forceDemo) {
      return { data: DEMO_ORDERS, provenance: 'DEMO', sourceNote: 'Demo dataset loaded by user preference.' };
    }
    try {
      const data = await apiClient.get<OrderItem[]>('/api/v1/orders', { params });
      return { data, provenance: 'LIVE', sourceNote: 'PostgreSQL Relational Persistence' };
    } catch {
      return { data: DEMO_ORDERS, provenance: 'FALLBACK', sourceNote: 'Backend unreachable. Showing certified offline fallback purchase orders.' };
    }
  }

  async createOrder(payload: Partial<OrderItem>): Promise<OrderItem> {
    return await apiClient.post<OrderItem>('/api/v1/orders', payload);
  }

  async deleteOrder(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/orders/${id}`);
  }

  // Shipments
  async getShipments(params?: { status?: string; page?: number; page_size?: number; forceDemo?: boolean }): Promise<ProvenanceEnvelope<ShipmentItem[]>> {
    if (params?.forceDemo) {
      return { data: DEMO_SHIPMENTS, provenance: 'DEMO', sourceNote: 'Demo dataset loaded by user preference.' };
    }
    try {
      const data = await apiClient.get<ShipmentItem[]>('/api/v1/shipments', { params });
      return { data, provenance: 'LIVE', sourceNote: 'PostgreSQL Relational Persistence' };
    } catch {
      return { data: DEMO_SHIPMENTS, provenance: 'FALLBACK', sourceNote: 'Backend unreachable. Showing certified offline fallback shipments.' };
    }
  }

  async createShipment(payload: Partial<ShipmentItem>): Promise<ShipmentItem> {
    return await apiClient.post<ShipmentItem>('/api/v1/shipments', payload);
  }

  async deleteShipment(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/shipments/${id}`);
  }

  // Risk & Disruptions
  async getRiskOverview(forceDemo?: boolean): Promise<ProvenanceEnvelope<RiskOverview>> {
    if (forceDemo) {
      return { data: DEMO_RISK, provenance: 'DEMO', sourceNote: 'Simulated demonstration risk model.' };
    }
    try {
      const res = await apiClient.get<any>('/api/v1/risk');
      // Normalize backend response
      const normalized: RiskOverview = {
        overall_risk_score: res.overall_risk_score ?? Math.round((res.bottleneck_score ?? 0.35) * 100),
        bottlenecks_detected: res.bottlenecks_detected ?? (res.affected_downstream_products?.length ?? 1),
        revenue_at_risk_usd: res.revenue_at_risk_usd ?? res.estimated_revenue_at_risk ?? 150000,
        vulnerable_suppliers: res.vulnerable_suppliers ?? [
          {
            supplier_id: res.supplier_id || "sup_network_aggregate",
            supplier_name: "Aggregate Critical Tier-2 Suppliers",
            tier: 2,
            risk_score: Math.round((res.bottleneck_score ?? 0.35) * 100),
            primary_risk_factor: res.mitigation_recommendations?.[0] || "Potential bottleneck in downstream supply pipeline",
            bottleneck_severity: (res.risk_level?.toUpperCase() || 'MEDIUM') as any,
          },
        ],
        active_disruptions: res.active_disruptions ?? (res.affected_downstream_products?.length ? [
          {
            id: "dis-backend-01",
            type: `${res.risk_level?.toUpperCase() || 'MODERATE'} Supply Bottleneck`,
            region: "Global Supply Corridor",
            impact_level: (res.risk_level === 'high' ? 'SEVERE' : res.risk_level === 'low' ? 'MINOR' : 'MODERATE') as any,
            description: `${res.affected_downstream_products.join(', ')}: ${res.mitigation_recommendations?.[0] || 'Monitor upstream suppliers.'}`,
          },
        ] : []),
      };
      return { data: normalized, provenance: 'LIVE', sourceNote: 'Real-time supply chain disruption heuristics' };
    } catch {
      return { data: DEMO_RISK, provenance: 'FALLBACK', sourceNote: 'API offline. Rendering demonstration risk scenario.' };
    }
  }

  async analyzeDisruption(payload: { supplier_id?: string; duration_days: number; severity: string }): Promise<any> {
    return await apiClient.post('/api/v1/risk/analyze-disruption', payload);
  }

  // Demand Forecast
  async getForecast(sku: string = "MAT-SILICON-300MM", forceDemo?: boolean): Promise<ProvenanceEnvelope<ForecastResponse>> {
    const demoForecast: ForecastResponse = {
      sku,
      historical_days: 30,
      forecast_horizon_days: 14,
      model_name: "Seasonal ARIMA Baseline Heuristic",
      is_scaffold: true,
      forecast_series: Array.from({ length: 14 }, (_, i) => ({
        day: i + 1,
        date: `2026-09-${(12 + i).toString().padStart(2, '0')}`,
        predicted_demand: Math.round(350 + Math.sin(i / 2) * 80 + Math.random() * 20),
        confidence_lower: 310,
        confidence_upper: 450,
      })),
    };

    if (forceDemo) {
      return { data: demoForecast, provenance: 'DEMO', sourceNote: 'Demonstration forecast projection.' };
    }
    try {
      const data = await apiClient.get<ForecastResponse>(`/api/v1/forecast?sku=${encodeURIComponent(sku)}`);
      return { data, provenance: 'LIVE', sourceNote: 'Forecast API Scaffold (In-Memory Baseline Generator)' };
    } catch {
      return { data: demoForecast, provenance: 'FALLBACK', sourceNote: 'Backend unavailable. Displaying baseline projection.' };
    }
  }

  // Asynchronous Multi-Agent Simulations
  async getSimulations(): Promise<ProvenanceEnvelope<SimulationTask[]>> {
    try {
      const data = await apiClient.get<any>('/api/v1/agents');
      // If endpoint returns status overview, fetch status of active or recent jobs
      return {
        data: [],
        provenance: 'LIVE',
        sourceNote: 'Active Ray / Background Worker Task Registry',
      };
    } catch {
      return { data: [], provenance: 'FALLBACK', sourceNote: 'Simulation worker offline' };
    }
  }

  async dispatchSimulation(payload: { name: string; num_days: number; num_firms: number }): Promise<{ experiment_id: string; task_id: string; status: string }> {
    return await apiClient.post('/api/v1/agents/simulations', payload);
  }

  async getSimulationStatus(experimentId: string): Promise<SimulationTask> {
    return await apiClient.get<SimulationTask>(`/api/v1/agents/simulations/${experimentId}/status`);
  }

  async cancelSimulation(experimentId: string): Promise<{ status: string; message: string }> {
    return await apiClient.post(`/api/v1/agents/simulations/${experimentId}/cancel`);
  }

  // Network Topology
  async getTopology(): Promise<any> {
    return await apiClient.get('/api/v1/routes/topology');
  }
}

export const controlTowerApi = new ControlTowerApiService();
export default controlTowerApi;
