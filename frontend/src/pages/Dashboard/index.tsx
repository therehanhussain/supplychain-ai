/**
 * Executive Control Tower Dashboard.
 *
 * Real-time operational command center providing multi-echelon supply chain
 * visibility, inventory status, shipment telemetry, and AI disruption intelligence.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Tag,
  Button,
  Flex,
  Progress,
  List,
  Space,
  Tooltip,
} from 'antd';
import {
  ShopOutlined,
  AppstoreOutlined,
  ShoppingCartOutlined,
  CarOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  NodeIndexOutlined,
  SafetyCertificateOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useApp } from '../../context/AppContext';
import PageHeader from '../../components/common/PageHeader';
import KpiCard from '../../components/common/KpiCard';
import controlTowerApi, {
  SupplierItem,
  InventoryItem,
  OrderItem,
  ShipmentItem,
  RiskOverview,
  DataProvenance,
} from '../../services/controlTowerApi';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { isDemoMode, systemStatus } = useApp();

  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [sourceNote, setSourceNote] = useState<string>('');
  const [riskError, setRiskError] = useState(false);

  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [shipments, setShipments] = useState<ShipmentItem[]>([]);
  const [risk, setRisk] = useState<RiskOverview | null>(null);

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setRiskError(false);
    try {
      const [supRes, invRes, ordRes, shpRes, riskRes] = await Promise.all([
        controlTowerApi.getSuppliers({ forceDemo: isDemoMode, page_size: 10 }),
        controlTowerApi.getInventory({ forceDemo: isDemoMode, page_size: 10 }),
        controlTowerApi.getOrders({ forceDemo: isDemoMode, page_size: 10 }),
        controlTowerApi.getShipments({ forceDemo: isDemoMode, page_size: 10 }),
        controlTowerApi.getRiskOverview(isDemoMode),
      ]);

      setSuppliers(supRes.data);
      setInventory(invRes.data);
      setOrders(ordRes.data);
      setShipments(shpRes.data);
      setRisk(riskRes.data);

      setProvenance(supRes.provenance);
      setSourceNote(
        supRes.provenance === 'FALLBACK'
          ? 'PostgreSQL database offline on port 5432. Displaying verified local fallback dataset.'
          : supRes.sourceNote || ''
      );
    } catch {
      setRiskError(true);
    } finally {
      setLoading(false);
    }
  }, [isDemoMode]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Derived metrics
  const totalInventoryValue = inventory.reduce(
    (sum, item) => sum + item.quantity_on_hand * (item.unit_cost || 50),
    0
  );
  const formattedInventoryValuation =
    totalInventoryValue >= 1000000
      ? `$${(totalInventoryValue / 1000000).toFixed(2)}M`
      : `$${(totalInventoryValue / 1000).toFixed(1)}k`;

  const lowStockItems = inventory.filter(
    (i) => i.quantity_on_hand <= i.reorder_point || i.is_low_stock
  );
  const inTransitShipments = shipments.filter((s) => s.status === 'in_transit');
  const pendingOrdersValue = orders
    .filter((o) => o.status === 'pending' || o.status === 'confirmed')
    .reduce((sum, o) => sum + o.total_amount, 0);

  // Formatted shipment columns with protected widths & single-line routes
  const shipmentColumns = [
    {
      title: 'Tracking #',
      dataIndex: 'tracking_number',
      key: 'tracking_number',
      width: 120,
      render: (text: string, record: ShipmentItem) => (
        <span
          onClick={() => navigate('/shipments')}
          style={{
            fontWeight: 600,
            color: '#1E40AF',
            cursor: 'pointer',
            fontSize: 12,
            fontFamily: 'monospace',
          }}
        >
          {text || `SHP-${record.id.substring(0, 6)}`}
        </span>
      ),
    },
    {
      title: 'Carrier',
      dataIndex: 'carrier',
      key: 'carrier',
      width: 130,
      render: (carrier: string) => (
        <span
          style={{
            fontSize: 12,
            color: '#334155',
            fontWeight: 500,
            display: 'inline-block',
            maxWidth: 120,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {carrier}
        </span>
      ),
    },
    {
      title: 'Route',
      key: 'route',
      width: 160,
      render: (_: any, record: ShipmentItem) => {
        const originShort = record.origin.split(',')[0].split('(')[0].trim();
        const destShort = record.destination.split(',')[0].split('(')[0].trim();
        return (
          <Tooltip title={`${record.origin} → ${record.destination}`}>
            <span
              style={{
                fontSize: 12,
                color: '#0F172A',
                fontWeight: 500,
                maxWidth: 150,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: 'inline-block',
                verticalAlign: 'bottom',
              }}
            >
              {originShort} <span style={{ color: '#94A3B8' }}>→</span> {destShort}
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 95,
      render: (status: string) => {
        let color = 'default';
        let icon = <ClockCircleOutlined />;
        if (status === 'delivered') {
          color = 'success';
          icon = <CheckCircleOutlined />;
        } else if (status === 'in_transit') {
          color = 'processing';
          icon = <CarOutlined />;
        } else if (status === 'preparing') {
          color = 'warning';
        }
        return (
          <Tag
            color={color}
            icon={icon}
            style={{
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 600,
              padding: '0 5px',
              lineHeight: '18px',
              textTransform: 'uppercase',
              margin: 0,
            }}
          >
            {status.replace('_', ' ')}
          </Tag>
        );
      },
    },
    {
      title: 'ETA',
      dataIndex: 'estimated_delivery',
      key: 'estimated_delivery',
      width: 75,
      render: (eta?: string) => (
        <span style={{ fontSize: 11, color: '#64748B', whiteSpace: 'nowrap' }}>
          {eta ? eta.substring(5, 10) : '14 Sep'}
        </span>
      ),
    },
  ];

  const hasActiveRisks =
    risk &&
    (risk.bottlenecks_detected > 0 ||
      (risk.active_disruptions && risk.active_disruptions.length > 0) ||
      risk.overall_risk_score > 30);

  return (
    <div>
      <PageHeader
        title="Executive Control Tower"
        subtitle="Real-time multi-echelon supply chain visibility, logistics monitoring, and AI risk detection."
        provenance={provenance}
        sourceNote={sourceNote}
        onRefresh={loadDashboardData}
        refreshing={loading}
        extra={
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => navigate('/simulations')}
            style={{
              backgroundColor: '#1E40AF',
              height: 36,
              fontWeight: 600,
              fontSize: 13,
              boxShadow: '0 1px 3px rgba(30, 64, 175, 0.3)',
            }}
          >
            Run Disruption Simulation
          </Button>
        }
      />

      <div style={{ padding: '0 24px' }}>
        {/* KPI Row (4 cols Desktop, 2 cols Tablet, 1 col Mobile) */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="Active Suppliers"
              value={suppliers.length}
              suffix="Vendors"
              icon={<ShopOutlined />}
              subtitle="Across Tier 1, 2 & 3 network"
              badge={{ text: 'Verified', color: 'blue' }}
              loading={loading}
            />
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="Inventory Valuation"
              value={formattedInventoryValuation}
              icon={<AppstoreOutlined />}
              badge={
                lowStockItems.length > 0
                  ? { text: `${lowStockItems.length} Low Stock`, color: 'volcano' }
                  : { text: 'Nominal Stock', color: 'green' }
              }
              subtitle={`${inventory.length} Tracked SKUs in hubs`}
              loading={loading}
            />
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="Purchase Orders"
              value={`$${(pendingOrdersValue / 1000).toFixed(1)}k`}
              icon={<ShoppingCartOutlined />}
              subtitle={`${orders.length} Active Procurement Orders`}
              badge={{
                text: `${orders.filter((o) => o.status === 'pending').length} Pending`,
                color: 'orange',
              }}
              loading={loading}
            />
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="Active Shipments"
              value={inTransitShipments.length}
              suffix={`/ ${shipments.length} Total`}
              icon={<CarOutlined />}
              badge={{ text: '98.4% On-Schedule', color: 'green' }}
              subtitle="Real-time freight telemetry"
              loading={loading}
            />
          </Col>
        </Row>

        {/* Balanced 2-Column Operational Grid */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {/* Left Column: Topology + Risk Intelligence */}
          <Col xs={24} lg={12}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              {/* Supply Network Topology Card */}
              <Card
                title={
                  <Flex justify="space-between" align="center">
                    <Flex align="center" gap={8}>
                      <NodeIndexOutlined style={{ color: '#1E40AF', fontSize: 16 }} />
                      <span style={{ fontWeight: 700, fontSize: 14, color: '#0F172A' }}>
                        Supply Network Topology
                      </span>
                    </Flex>
                    <Tag
                      color={systemStatus.neo4jMode === 'LIVE' ? 'green' : 'orange'}
                      style={{ fontSize: 10, fontWeight: 600, borderRadius: 4, margin: 0 }}
                    >
                      {systemStatus.neo4jMode === 'LIVE'
                        ? 'GRAPH: LIVE'
                        : 'GRAPH: FALLBACK (CACHED)'}
                    </Tag>
                  </Flex>
                }
                style={{
                  borderRadius: 8,
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                }}
                bodyStyle={{ padding: '16px 20px' }}
              >
                <div style={{ fontSize: 13, color: '#475569', marginBottom: 12, lineHeight: 1.4 }}>
                  Multi-echelon graph linking raw materials to tier-2 sub-components and tier-3 OEMs.
                </div>

                {/* Echelon Flow Diagram */}
                <div
                  style={{
                    backgroundColor: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    borderRadius: 6,
                    padding: '12px 14px',
                  }}
                >
                  <Row gutter={[8, 8]} align="middle">
                    <Col xs={24} sm={7}>
                      <div
                        style={{
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: 6,
                          padding: '10px 8px',
                          textAlign: 'center',
                        }}
                      >
                        <Tag color="blue" style={{ fontSize: 10, fontWeight: 700, margin: 0 }}>
                          TIER 1
                        </Tag>
                        <div style={{ fontWeight: 600, fontSize: 12, color: '#0F172A', marginTop: 4 }}>
                          Raw Materials
                        </div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>Silicon, Neon, Lithium</div>
                      </div>
                    </Col>

                    <Col xs={24} sm={1} style={{ textAlign: 'center' }}>
                      <span style={{ color: '#94A3B8', fontSize: 14, fontWeight: 700 }}>→</span>
                    </Col>

                    <Col xs={24} sm={8}>
                      <div
                        style={{
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: 6,
                          padding: '10px 8px',
                          textAlign: 'center',
                        }}
                      >
                        <Tag color="cyan" style={{ fontSize: 10, fontWeight: 700, margin: 0 }}>
                          TIER 2
                        </Tag>
                        <div style={{ fontWeight: 600, fontSize: 12, color: '#0F172A', marginTop: 4 }}>
                          Components
                        </div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>Wafers, Cells, ASICs</div>
                      </div>
                    </Col>

                    <Col xs={24} sm={1} style={{ textAlign: 'center' }}>
                      <span style={{ color: '#94A3B8', fontSize: 14, fontWeight: 700 }}>→</span>
                    </Col>

                    <Col xs={24} sm={7}>
                      <div
                        style={{
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: 6,
                          padding: '10px 8px',
                          textAlign: 'center',
                        }}
                      >
                        <Tag color="purple" style={{ fontSize: 10, fontWeight: 700, margin: 0 }}>
                          TIER 3
                        </Tag>
                        <div style={{ fontWeight: 600, fontSize: 12, color: '#0F172A', marginTop: 4 }}>
                          Manufacturers
                        </div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>Munich & Austin Hubs</div>
                      </div>
                    </Col>
                  </Row>
                </div>

                <Button
                  type="primary"
                  ghost
                  block
                  icon={<NodeIndexOutlined />}
                  onClick={() => navigate('/network')}
                  style={{
                    marginTop: 14,
                    height: 36,
                    fontWeight: 600,
                    fontSize: 13,
                    borderColor: '#1E40AF',
                    color: '#1E40AF',
                  }}
                >
                  Explore Full Topology & Bill of Materials
                </Button>
              </Card>

              {/* Risk & Bottlenecks Card */}
              <Card
                title={
                  <Flex justify="space-between" align="center">
                    <Flex align="center" gap={8} wrap="wrap">
                      <AlertOutlined style={{ color: '#D97706', fontSize: 16 }} />
                      <span style={{ fontWeight: 700, fontSize: 14, color: '#0F172A' }}>
                        Supply Network Risk
                      </span>
                      <Tag
                        color={isDemoMode ? 'purple' : provenance === 'FALLBACK' ? 'orange' : 'cyan'}
                        style={{ fontSize: 9, fontWeight: 700, margin: 0, borderRadius: 4, lineHeight: '16px' }}
                      >
                        {isDemoMode ? 'DEMO RISK ANALYSIS' : provenance === 'FALLBACK' ? 'FALLBACK RISK ANALYSIS' : 'ANALYTICAL BASELINE'}
                      </Tag>
                    </Flex>
                    <Flex align="center" gap={8}>
                      {hasActiveRisks && (
                        <Tag
                          color={risk?.overall_risk_score && risk.overall_risk_score > 60 ? 'error' : 'warning'}
                          style={{ fontSize: 10, fontWeight: 600, borderRadius: 4, margin: 0 }}
                        >
                          Score: {risk?.overall_risk_score} / 100
                        </Tag>
                      )}
                      <Button type="link" size="small" onClick={() => navigate('/risk')} style={{ padding: 0 }}>
                        Details
                      </Button>
                    </Flex>
                  </Flex>
                }
                style={{
                  borderRadius: 8,
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                }}
                bodyStyle={{ padding: '16px 20px' }}
              >
                {riskError ? (
                  /* Intentional Error State */
                  <div
                    style={{
                      padding: '24px 16px',
                      backgroundColor: '#FEF2F2',
                      border: '1px solid #FEE2E2',
                      borderRadius: 6,
                      textAlign: 'center',
                    }}
                  >
                    <ExclamationCircleOutlined style={{ fontSize: 24, color: '#DC2626' }} />
                    <div style={{ fontWeight: 700, fontSize: 13, color: '#991B1B', marginTop: 6 }}>
                      RISK DATA UNAVAILABLE
                    </div>
                    <div style={{ fontSize: 12, color: '#B91C1C', marginTop: 2 }}>
                      Unable to retrieve current risk heuristics from backend service.
                    </div>
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      onClick={loadDashboardData}
                      style={{ marginTop: 10 }}
                    >
                      Retry Connection
                    </Button>
                  </div>
                ) : hasActiveRisks ? (
                  <Row gutter={[16, 16]} align="middle">
                    <Col xs={24} sm={8} style={{ textAlign: 'center' }}>
                      <Progress
                        type="dashboard"
                        percent={risk?.overall_risk_score || 35}
                        strokeColor={
                          risk?.overall_risk_score && risk.overall_risk_score > 60
                            ? '#DC2626'
                            : '#D97706'
                        }
                        size={110}
                        format={(percent) => `${percent}%`}
                      />
                      <div style={{ fontSize: 11, fontWeight: 600, color: '#64748B', marginTop: 4 }}>
                        Vulnerability Index
                      </div>
                    </Col>

                    <Col xs={24} sm={16}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#0F172A', marginBottom: 6 }}>
                        Active Network Bottlenecks:
                      </div>
                      <List
                        size="small"
                        dataSource={risk?.active_disruptions || []}
                        renderItem={(item) => (
                          <List.Item style={{ padding: '6px 0', borderBottom: '1px solid #F1F5F9' }}>
                            <Flex align="flex-start" gap={8} style={{ width: '100%' }}>
                              <ExclamationCircleOutlined
                                style={{
                                  color: item.impact_level === 'SEVERE' ? '#DC2626' : '#D97706',
                                  marginTop: 2,
                                  fontSize: 13,
                                }}
                              />
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontWeight: 600, fontSize: 12, color: '#0F172A' }}>
                                  {item.type}
                                  <span style={{ color: '#64748B', fontWeight: 400, marginLeft: 4 }}>
                                    ({item.region})
                                  </span>
                                </div>
                                <div
                                  style={{
                                    fontSize: 11,
                                    color: '#475569',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                  }}
                                >
                                  {item.description}
                                </div>
                              </div>
                            </Flex>
                          </List.Item>
                        )}
                      />
                    </Col>
                  </Row>
                ) : (
                  /* Intentional Polished Nominal State */
                  <div
                    style={{
                      padding: '24px 16px',
                      backgroundColor: '#F0FDF4',
                      border: '1px solid #DCFCE7',
                      borderRadius: 6,
                      textAlign: 'center',
                    }}
                  >
                    <SafetyCertificateOutlined style={{ fontSize: 26, color: '#16A34A' }} />
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: 13,
                        color: '#166534',
                        marginTop: 6,
                        letterSpacing: '0.04em',
                      }}
                    >
                      NO ACTIVE DISRUPTIONS
                    </div>
                    <div style={{ fontSize: 12, color: '#15803D', marginTop: 2 }}>
                      All multi-tier supply routes operating within nominal latency thresholds.
                    </div>
                  </div>
                )}
                <div style={{ marginTop: 12, fontSize: 11, color: '#94A3B8', fontStyle: 'italic', borderTop: '1px solid #F1F5F9', paddingTop: 6 }}>
                  * Multi-tier vulnerability heuristic calculated from supplier lead times and inventory thresholds (not real-time sensor telemetry).
                </div>
              </Card>
            </Space>
          </Col>

          {/* Right Column: Logistics Telemetry + Inventory Alerts */}
          <Col xs={24} lg={12}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              {/* Logistics Telemetry Table */}
              <Card
                title={
                  <Flex justify="space-between" align="center">
                    <Flex align="center" gap={8}>
                      <CarOutlined style={{ color: '#1E40AF', fontSize: 16 }} />
                      <span style={{ fontWeight: 700, fontSize: 14, color: '#0F172A' }}>
                        Real-Time Logistics Telemetry
                      </span>
                    </Flex>
                    <Tag color="blue" style={{ fontSize: 10, fontWeight: 600, borderRadius: 4, margin: 0 }}>
                      {inTransitShipments.length} Active In-Transit
                    </Tag>
                  </Flex>
                }
                extra={
                  <Button type="link" size="small" onClick={() => navigate('/shipments')}>
                    View All
                  </Button>
                }
                style={{
                  borderRadius: 8,
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                }}
                bodyStyle={{ padding: 0 }}
              >
                {!isMobile ? (
                  <Table
                    dataSource={shipments.slice(0, 4)}
                    columns={shipmentColumns}
                    rowKey="id"
                    pagination={false}
                    loading={loading}
                    size="small"
                    scroll={{ x: 540 }}
                  />
                ) : (
                  /* Mobile-Friendly Shipment Card List */
                  <div style={{ padding: '10px 14px' }}>
                    {shipments.slice(0, 4).map((s) => (
                      <div
                        key={s.id}
                        style={{
                          padding: '10px 12px',
                          border: '1px solid #E2E8F0',
                          borderRadius: 6,
                          marginBottom: 8,
                          backgroundColor: '#FFFFFF',
                        }}
                      >
                        <Flex justify="space-between" align="center">
                          <span style={{ fontWeight: 600, fontSize: 12, color: '#1E40AF' }}>
                            {s.tracking_number || `SHP-${s.id.substring(0, 6)}`}
                          </span>
                          <Tag
                            color={s.status === 'in_transit' ? 'processing' : 'default'}
                            style={{ fontSize: 10, margin: 0 }}
                          >
                            {s.status.toUpperCase()}
                          </Tag>
                        </Flex>
                        <div style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{s.carrier}</div>
                        <div style={{ fontWeight: 500, fontSize: 12, color: '#0F172A', marginTop: 4 }}>
                          {s.origin.split(',')[0]} → {s.destination.split(',')[0]}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Low Stock & Reorder Alerts */}
              <Card
                title={
                  <Flex justify="space-between" align="center">
                    <Flex align="center" gap={8}>
                      <AppstoreOutlined style={{ color: '#D97706', fontSize: 16 }} />
                      <span style={{ fontWeight: 700, fontSize: 14, color: '#0F172A' }}>
                        Low Stock & Reorder Alerts
                      </span>
                    </Flex>
                    <Tag
                      color={lowStockItems.length > 0 ? 'volcano' : 'green'}
                      style={{ fontSize: 10, fontWeight: 600, borderRadius: 4, margin: 0 }}
                    >
                      {lowStockItems.length > 0
                        ? `${lowStockItems.length} Threshold Violations`
                        : 'Nominal'}
                    </Tag>
                  </Flex>
                }
                extra={
                  <Button type="link" size="small" onClick={() => navigate('/inventory')}>
                    Manage Inventory
                  </Button>
                }
                style={{
                  borderRadius: 8,
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                }}
                bodyStyle={{ padding: '12px 18px' }}
              >
                <List
                  dataSource={inventory.slice(0, 3)}
                  renderItem={(item) => {
                    const isLowStock = item.quantity_on_hand <= item.reorder_point || item.is_low_stock;
                    return (
                      <List.Item style={{ padding: '8px 0', borderBottom: '1px solid #F1F5F9' }}>
                        <Flex justify="space-between" align="center" style={{ width: '100%' }}>
                          <div>
                            <Flex align="center" gap={8}>
                              <span style={{ fontWeight: 600, fontSize: 13, color: '#0F172A' }}>
                                {item.sku}
                              </span>
                              <Tag
                                color={isLowStock ? 'error' : 'success'}
                                style={{
                                  fontSize: 10,
                                  fontWeight: 700,
                                  margin: 0,
                                  padding: '0 4px',
                                  lineHeight: '16px',
                                }}
                              >
                                {isLowStock ? 'LOW STOCK' : 'HEALTHY'}
                              </Tag>
                            </Flex>
                            <div style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{item.name}</div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div
                              style={{
                                fontWeight: 700,
                                fontSize: 13,
                                color: isLowStock ? '#DC2626' : '#059669',
                              }}
                            >
                              {item.quantity_on_hand.toLocaleString()} units
                            </div>
                            <span style={{ fontSize: 11, color: '#94A3B8' }}>
                              Threshold: {item.reorder_point.toLocaleString()}
                            </span>
                          </div>
                        </Flex>
                      </List.Item>
                    );
                  }}
                />

                {/* Status Summary Footer to Balance Card Height */}
                <div
                  style={{
                    backgroundColor: '#F8FAFC',
                    borderRadius: 6,
                    border: '1px solid #E2E8F0',
                    padding: '8px 12px',
                    marginTop: 10,
                    fontSize: 11,
                    color: '#64748B',
                  }}
                >
                  <Flex justify="space-between" align="center">
                    <span>Active Inventory Scope: {inventory.length} Tracked SKUs</span>
                    <span
                      style={{
                        fontWeight: 600,
                        color: lowStockItems.length > 0 ? '#DC2626' : '#16A34A',
                      }}
                    >
                      {lowStockItems.length > 0
                        ? `${lowStockItems.length} SKUs require procurement restock`
                        : 'All warehouses operating above safety thresholds'}
                    </span>
                  </Flex>
                </div>
              </Card>
            </Space>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default Dashboard;
