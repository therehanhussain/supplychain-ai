/**
 * Inventory Management Operations View.
 *
 * Operational SKU inventory, warehouse balances, and Material Lot / Batch Traceability
 * backed by PostgreSQL (/api/v1/inventory and /api/v1/manufacturing/lots).
 * Features stockout risk detection, lot-level holding tracking, and end-to-end traceability.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Modal,
  Form,
  InputNumber,
  message,
  Drawer,
  Flex,
  Typography,
  Tabs,
  Card,
  Row,
  Col,
  Statistic,
  Alert,
  Timeline,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  WarningOutlined,
  InboxOutlined,
  BarcodeOutlined,
  DeploymentUnitOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
  ThunderboltOutlined,
  ShopOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useApp } from '../../context/AppContext';
import PageHeader from '../../components/common/PageHeader';
import EmptyState from '../../components/common/EmptyState';
import controlTowerApi, {
  InventoryItem,
  DataProvenance,
  MaterialLotItem,
  LotTraceabilityReport,
} from '../../services/controlTowerApi';

const { Option } = Select;
const { Text, Title, Paragraph } = Typography;

export const InventoryPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isDemoMode } = useApp();

  // Active Tab: 'inventory' | 'lots'
  const [activeTab, setActiveTab] = useState<'inventory' | 'lots'>('inventory');

  // Inventory State
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [sourceNote, setSourceNote] = useState<string>('');

  // Lots State
  const [lots, setLots] = useState<MaterialLotItem[]>([]);
  const [loadingLots, setLoadingLots] = useState(false);
  const [lotSearchTerm, setLotSearchTerm] = useState('');
  const [lotStatusFilter, setLotStatusFilter] = useState<string>('ALL');

  // Modals & Drawers
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [receiveLotModalVisible, setReceiveLotModalVisible] = useState(false);
  const [traceabilityModalVisible, setTraceabilityModalVisible] = useState(false);
  const [selectedLotReport, setSelectedLotReport] = useState<LotTraceabilityReport | null>(null);
  const [loadingTraceability, setLoadingTraceability] = useState(false);

  // Forms
  const [form] = Form.useForm();
  const [receiveForm] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [warehouseFilter, setWarehouseFilter] = useState<string | undefined>(undefined);
  const [lowStockOnly, setLowStockOnly] = useState<boolean>(false);

  const fetchInventory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await controlTowerApi.getInventory({
        warehouse_id: warehouseFilter,
        forceDemo: isDemoMode,
      });
      setInventory(res.data);
      setProvenance(res.provenance);
      setSourceNote(res.sourceNote || '');
    } catch {
      message.error('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  }, [warehouseFilter, isDemoMode]);

  const fetchLots = useCallback(async () => {
    setLoadingLots(true);
    try {
      const res = await controlTowerApi.listLots();
      setLots(res.data);
    } catch {
      message.error('Failed to load material lots');
    } finally {
      setLoadingLots(false);
    }
  }, []);

  useEffect(() => {
    fetchInventory();
    fetchLots();
  }, [fetchInventory, fetchLots]);

  // Open Traceability Report
  const handleOpenTraceability = async (lot: MaterialLotItem) => {
    setLoadingTraceability(true);
    setSelectedLotReport(null);
    setTraceabilityModalVisible(true);
    try {
      const res = await controlTowerApi.getLotTraceability(lot.id);
      setSelectedLotReport(res.data);
    } catch {
      message.error('Failed to retrieve lot traceability report.');
    } finally {
      setLoadingTraceability(false);
    }
  };

  // Submit Inbound Lot Receipt
  const handleReceiveLotSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      await controlTowerApi.receiveLot({
        product_id: values.product_id,
        warehouse_id: values.warehouse_id,
        supplier_id: values.supplier_id || undefined,
        lot_number: values.lot_number,
        quantity: values.quantity,
        unit_of_measure: values.unit_of_measure || 'kg',
        notes: values.notes,
      });
      message.success(`Lot ${values.lot_number} received into stock successfully.`);
      setReceiveLotModalVisible(false);
      receiveForm.resetFields();
      await Promise.all([fetchInventory(), fetchLots()]);
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to receive inbound lot.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      category: 'raw_material',
      warehouse_id: 'WH-01',
      quantity_on_hand: 1000,
      quantity_reserved: 0,
      reorder_point: 500,
      unit_cost: 45.0,
    });
    setDrawerVisible(true);
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      await controlTowerApi.createInventory(values);
      message.success('Inventory SKU added successfully');
      setDrawerVisible(false);
      fetchInventory();
    } catch {
      message.error('Operation failed. Please verify parameters.');
    } finally {
      setSubmitting(false);
    }
  };

  // Filtered Inventory
  const filteredItems = inventory.filter((item) => {
    const matchesSearch =
      item.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.name.toLowerCase().includes(searchTerm.toLowerCase());
    const isLow = item.quantity_on_hand <= item.reorder_point || item.is_low_stock;
    const matchesLowStock = lowStockOnly ? isLow : true;
    return matchesSearch && matchesLowStock;
  });

  // Filtered Lots
  const filteredLots = lots.filter((lot) => {
    if (lotStatusFilter !== 'ALL' && lot.status !== lotStatusFilter) return false;
    if (!lotSearchTerm.trim()) return true;
    const q = lotSearchTerm.toLowerCase();
    return (
      lot.lot_number.toLowerCase().includes(q) ||
      (lot.product_sku && lot.product_sku.toLowerCase().includes(q)) ||
      (lot.product_name && lot.product_name.toLowerCase().includes(q)) ||
      (lot.supplier_name && lot.supplier_name.toLowerCase().includes(q)) ||
      (lot.warehouse_code && lot.warehouse_code.toLowerCase().includes(q))
    );
  });

  const inventoryColumns = [
    {
      title: 'SKU Code',
      dataIndex: 'sku',
      key: 'sku',
      render: (sku: string) => (
        <span style={{ fontWeight: 700, color: '#1E40AF', fontFamily: 'monospace' }}>
          {sku}
        </span>
      ),
    },
    {
      title: 'Product Description',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: InventoryItem) => (
        <div>
          <div style={{ fontWeight: 600, color: '#0F172A', fontSize: 13 }}>{name}</div>
          <span style={{ fontSize: 11, color: '#64748B', textTransform: 'capitalize' }}>
            {record.category.replace('_', ' ')}
          </span>
        </div>
      ),
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_id',
      key: 'warehouse_id',
      render: (wh: string) => <Tag color="blue">{wh}</Tag>,
    },
    {
      title: 'Stock Health',
      key: 'health',
      render: (_: any, record: InventoryItem) => {
        const isLow = record.quantity_on_hand <= record.reorder_point || record.is_low_stock;
        const isOut = record.quantity_on_hand <= 0;

        let statusText = 'Healthy';
        let color = '#059669';
        let tagColor = 'green';

        if (isOut) {
          statusText = 'Stockout';
          color = '#DC2626';
          tagColor = 'red';
        } else if (isLow) {
          statusText = 'Low Stock';
          color = '#D97706';
          tagColor = 'orange';
        }

        return (
          <Space size={8}>
            <Tag color={tagColor} style={{ fontWeight: 600 }}>{statusText}</Tag>
            <span style={{ fontSize: 12, color }}>{record.quantity_on_hand.toLocaleString()} units</span>
          </Space>
        );
      },
    },
    {
      title: 'Unit Cost',
      dataIndex: 'unit_cost',
      key: 'unit_cost',
      render: (cost: number) => `$${Number(cost || 0).toFixed(2)}`,
    },
  ];

  const lotColumns = [
    {
      title: 'Lot / Batch Number',
      key: 'lot_number',
      render: (_: any, r: MaterialLotItem) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#1E40AF', fontFamily: 'monospace', fontSize: 14 }}>
            {r.lot_number}
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            ID: <Text code>{r.id.substring(0, 8)}...</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: 'Product Material',
      key: 'product',
      render: (_: any, r: MaterialLotItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{r.product_name || r.product_sku}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            SKU: <Text code>{r.product_sku || 'N/A'}</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_code',
      key: 'warehouse',
      render: (wh: string) => <Tag color="blue">{wh || 'Central WH'}</Tag>,
    },
    {
      title: 'Supplier',
      dataIndex: 'supplier_name',
      key: 'supplier',
      render: (sup: string) => sup ? <Tag color="purple">{sup}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: 'Initial Received',
      key: 'received_quantity',
      render: (_: any, r: MaterialLotItem) => `${r.received_quantity} ${r.unit_of_measure}`,
    },
    {
      title: 'Warehouse Stock',
      key: 'current_quantity',
      render: (_: any, r: MaterialLotItem) => (
        <Tag color={r.current_quantity > 0 ? 'green' : 'default'} style={{ fontWeight: 600, fontSize: 13 }}>
          {r.current_quantity} {r.unit_of_measure}
        </Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => {
        const color = st === 'ACTIVE' ? 'success' : st === 'DEPLETED' ? 'default' : 'warning';
        return <Tag color={color}>{st}</Tag>;
      },
    },
    {
      title: 'Received Date',
      dataIndex: 'received_at',
      key: 'received_at',
      render: (dt: string) => dt ? new Date(dt).toLocaleDateString() : '—',
    },
    {
      title: 'Traceability',
      key: 'action',
      render: (_: any, r: MaterialLotItem) => (
        <Button
          size="small"
          type="primary"
          icon={<HistoryOutlined />}
          onClick={() => handleOpenTraceability(r)}
          style={{ background: '#4F46E5', borderColor: '#4F46E5' }}
        >
          Trace Lifecycle
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Inventory & Material Lots"
        subtitle="Manage multi-facility SKU balances, inbound lot receipts, and complete end-to-end manufacturing material traceability."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Inventory' }]}
        provenance={provenance}
        sourceNote={sourceNote}
        onRefresh={() => { fetchInventory(); fetchLots(); }}
        refreshing={loading || loadingLots}
        extra={
          <Space>
            <Button
              icon={<InboxOutlined />}
              onClick={() => navigate('/inventory/requests')}
              style={{ borderColor: '#BFDBFE', color: '#1E40AF', background: '#EFF6FF', fontWeight: 600 }}
            >
              Open Material Requests
            </Button>
            <Button
              icon={<BarcodeOutlined />}
              onClick={() => setReceiveLotModalVisible(true)}
              style={{ borderColor: '#A7F3D0', color: '#065F46', background: '#ECFDF5', fontWeight: 600 }}
            >
              Receive Material Lot
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
              Restock / Add SKU
            </Button>
          </Space>
        }
      />

      <div style={{ padding: '0 24px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as 'inventory' | 'lots')}
          items={[
            {
              key: 'inventory',
              label: (
                <Space>
                  <ShopOutlined />
                  <span>Warehouse SKUs ({filteredItems.length})</span>
                </Space>
              ),
              children: (
                <div>
                  <Flex gap="middle" style={{ marginBottom: 16 }} wrap="wrap">
                    <Input
                      placeholder="Search SKU code or product title..."
                      prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      style={{ width: 280 }}
                      allowClear
                    />
                    <Button
                      type={lowStockOnly ? 'primary' : 'default'}
                      icon={<WarningOutlined />}
                      onClick={() => setLowStockOnly(!lowStockOnly)}
                    >
                      Low Stock Only
                    </Button>
                  </Flex>

                  <div style={{ backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
                    <Table
                      dataSource={filteredItems}
                      columns={inventoryColumns}
                      rowKey="id"
                      loading={loading}
                      locale={{
                        emptyText: (
                          <EmptyState
                            title="No Inventory Records"
                            description="No inventory items found. Add items to stock catalog."
                            onAction={handleOpenCreate}
                            actionText="Add Stock SKU"
                          />
                        ),
                      }}
                      pagination={{ pageSize: 8, showSizeChanger: true }}
                    />
                  </div>
                </div>
              ),
            },
            {
              key: 'lots',
              label: (
                <Space>
                  <DeploymentUnitOutlined />
                  <span>Material Lots & Traceability ({lots.length})</span>
                </Space>
              ),
              children: (
                <div>
                  <Flex gap="middle" style={{ marginBottom: 16 }} wrap="wrap">
                    <Input
                      placeholder="Search Lot number, SKU, product, or supplier..."
                      prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
                      value={lotSearchTerm}
                      onChange={(e) => setLotSearchTerm(e.target.value)}
                      style={{ width: 320 }}
                      allowClear
                    />
                    <Select
                      value={lotStatusFilter}
                      onChange={setLotStatusFilter}
                      style={{ width: 160 }}
                    >
                      <Option value="ALL">All Lot Statuses</Option>
                      <Option value="ACTIVE">Active Stock</Option>
                      <Option value="DEPLETED">Depleted Lots</Option>
                    </Select>
                  </Flex>

                  <div style={{ backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
                    <Table
                      dataSource={filteredLots}
                      columns={lotColumns}
                      rowKey="id"
                      loading={loadingLots}
                      locale={{
                        emptyText: (
                          <EmptyState
                            title="No Material Lots Found"
                            description="No lots have been received yet. Click 'Receive Material Lot' to register inbound raw materials."
                            onAction={() => setReceiveLotModalVisible(true)}
                            actionText="Receive Inbound Lot"
                          />
                        ),
                      }}
                      pagination={{ pageSize: 8, showSizeChanger: true }}
                    />
                  </div>
                </div>
              ),
            },
          ]}
        />
      </div>

      {/* Receive Inbound Lot Modal */}
      <Modal
        title={
          <Space>
            <BarcodeOutlined style={{ color: '#059669' }} />
            <span>Receive Inbound Material Lot</span>
          </Space>
        }
        open={receiveLotModalVisible}
        onCancel={() => setReceiveLotModalVisible(false)}
        onOk={() => receiveForm.submit()}
        confirmLoading={submitting}
        okText="Confirm Inbound Receipt"
        okButtonProps={{ style: { background: '#059669', borderColor: '#059669' } }}
      >
        <Paragraph type="secondary">
          Registers raw material batch into a unique lot. Atomically increments warehouse stock and initializes the lot audit ledger.
        </Paragraph>
        <Form form={receiveForm} layout="vertical" onFinish={handleReceiveLotSubmit}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="product_id" label="Product SKU or ID" rules={[{ required: true, message: 'SKU is required' }]}>
                <Input placeholder="e.g. MAT-STEEL-001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="warehouse_id" label="Warehouse Code" rules={[{ required: true, message: 'Warehouse is required' }]}>
                <Input placeholder="e.g. WH-01" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="lot_number" label="Lot / Batch Number" rules={[{ required: true, message: 'Lot number required' }]}>
                <Input placeholder="e.g. LOT-2026-A1" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="supplier_id" label="Supplier Name or ID">
                <Input placeholder="e.g. Apex Metals Corp" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="quantity" label="Received Quantity" rules={[{ required: true, message: 'Quantity is required' }]}>
                <InputNumber min={0.01} step={1} style={{ width: '100%' }} placeholder="100.0" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="unit_of_measure" label="Unit of Measure">
                <Input placeholder="kg (default)" defaultValue="kg" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="notes" label="Inbound Receipt Notes (Optional)">
            <Input.TextArea rows={2} placeholder="e.g. Certified ASTM grade A36; Mill test sheet attached" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Lot Traceability Lifecycle Modal */}
      <Modal
        title={
          <Space>
            <DeploymentUnitOutlined style={{ color: '#4F46E5', fontSize: 18 }} />
            <span style={{ fontSize: 17, fontWeight: 700 }}>
              End-to-End Lot Traceability: {selectedLotReport?.lot_number || 'Loading...'}
            </span>
          </Space>
        }
        open={traceabilityModalVisible}
        onCancel={() => setTraceabilityModalVisible(false)}
        footer={[
          <Button key="close" type="primary" onClick={() => setTraceabilityModalVisible(false)}>
            Close Traceability Report
          </Button>,
        ]}
        width={900}
        loading={loadingTraceability}
      >
        {selectedLotReport && (
          <div>
            {/* Header Metadata */}
            <Card bordered size="small" style={{ borderRadius: 8, marginBottom: 16, background: '#F8FAFC' }}>
              <Row gutter={[16, 12]}>
                <Col span={8}>
                  <Text type="secondary">Component SKU:</Text> <Text strong>{selectedLotReport.product_sku}</Text>
                </Col>
                <Col span={8}>
                  <Text type="secondary">Product Name:</Text> <Text strong>{selectedLotReport.product_name}</Text>
                </Col>
                <Col span={8}>
                  <Text type="secondary">Status:</Text> <Tag color={selectedLotReport.status === 'ACTIVE' ? 'green' : 'default'}>{selectedLotReport.status}</Tag>
                </Col>
                <Col span={8}>
                  <Text type="secondary">Supplier Origin:</Text> <Text strong>{selectedLotReport.supplier_name || 'Direct Receipt'}</Text>
                </Col>
                <Col span={8}>
                  <Text type="secondary">Warehouse:</Text> <Tag color="blue">{selectedLotReport.warehouse_code || 'Central WH'}</Tag>
                </Col>
                <Col span={8}>
                  <Text type="secondary">Received At:</Text> <Text>{new Date(selectedLotReport.received_at).toLocaleString()}</Text>
                </Col>
              </Row>
            </Card>

            {/* Reconciliation Balance Grid */}
            <Card bordered size="small" style={{ borderRadius: 8, marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                <Col span={4}>
                  <Statistic
                    title="Received"
                    value={selectedLotReport.initial_received_quantity}
                    suffix={selectedLotReport.unit_of_measure}
                    valueStyle={{ color: '#1E40AF', fontSize: 18 }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="Warehouse Stock"
                    value={selectedLotReport.current_warehouse_balance}
                    suffix={selectedLotReport.unit_of_measure}
                    valueStyle={{ color: '#059669', fontSize: 18 }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="Floor Holding"
                    value={selectedLotReport.total_current_floor_holding}
                    suffix={selectedLotReport.unit_of_measure}
                    valueStyle={{ color: '#0891B2', fontSize: 18 }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="Consumed"
                    value={selectedLotReport.total_consumed_in_production}
                    suffix={selectedLotReport.unit_of_measure}
                    valueStyle={{ color: '#4F46E5', fontSize: 18 }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="Returned"
                    value={selectedLotReport.total_returned_to_warehouse}
                    suffix={selectedLotReport.unit_of_measure}
                    valueStyle={{ color: '#D97706', fontSize: 18 }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="Scrap / Waste"
                    value={selectedLotReport.total_scrapped_or_wasted}
                    suffix={selectedLotReport.unit_of_measure}
                    valueStyle={{ color: '#DC2626', fontSize: 18 }}
                  />
                </Col>
              </Row>
              <Divider style={{ margin: '12px 0' }} />
              <Alert
                type="success"
                showIcon
                message="Physical Conservation & Movement Reconciliation"
                description={
                  <div>
                    <div>
                      <Text strong>Physical Stock Conservation:</Text>{' '}
                      <Text code>Initial ({selectedLotReport.initial_received_quantity}) = Warehouse Balance ({selectedLotReport.current_warehouse_balance}) + Active Floor Holding ({selectedLotReport.total_current_floor_holding}) + Consumed ({selectedLotReport.total_consumed_in_production}) + Scrap ({selectedLotReport.total_scrapped_or_wasted})</Text>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      <Text strong>Movement Dispatch Reconciliation:</Text>{' '}
                      <Text code>Issued ({selectedLotReport.total_issued_to_work_orders}) = Consumed ({selectedLotReport.total_consumed_in_production}) + Returned ({selectedLotReport.total_returned_to_warehouse}) + Scrap ({selectedLotReport.total_scrapped_or_wasted}) + Floor Holding ({selectedLotReport.total_current_floor_holding})</Text>
                    </div>
                  </div>
                }
              />
            </Card>

            {/* Work Order Floor Holdings */}
            <Title level={5} style={{ marginTop: 16 }}>Work Order Floor Holdings</Title>
            {selectedLotReport.work_order_holdings.length === 0 ? (
              <Paragraph type="secondary">No work orders currently hold material from this lot.</Paragraph>
            ) : (
              <Table
                dataSource={selectedLotReport.work_order_holdings}
                rowKey="work_order_id"
                pagination={false}
                size="small"
                style={{ marginBottom: 16 }}
                columns={[
                  {
                    title: 'Work Order',
                    dataIndex: 'work_order_number',
                    key: 'wo',
                    render: (wo: string) => <Text strong style={{ color: '#1E40AF' }}>{wo}</Text>,
                  },
                  {
                    title: 'Issued',
                    dataIndex: 'issued_quantity',
                    key: 'issued',
                    render: (qty: number, r: any) => `${qty} ${r.unit_of_measure}`,
                  },
                  {
                    title: 'Consumed',
                    dataIndex: 'consumed_quantity',
                    key: 'consumed',
                    render: (qty: number, r: any) => `${qty} ${r.unit_of_measure}`,
                  },
                  {
                    title: 'Returned',
                    dataIndex: 'returned_quantity',
                    key: 'returned',
                    render: (qty: number, r: any) => `${qty} ${r.unit_of_measure}`,
                  },
                  {
                    title: 'Wastage',
                    dataIndex: 'wastage_quantity',
                    key: 'wastage',
                    render: (qty: number, r: any) => `${qty} ${r.unit_of_measure}`,
                  },
                  {
                    title: 'Current Holding',
                    dataIndex: 'remaining_holding',
                    key: 'holding',
                    render: (qty: number, r: any) => (
                      <Tag color={qty > 0 ? 'cyan' : 'default'} style={{ fontWeight: 600 }}>
                        {qty} {r.unit_of_measure}
                      </Tag>
                    ),
                  },
                ]}
              />
            )}

            {/* Movement Audit Ledger */}
            <Title level={5} style={{ marginTop: 16 }}>Physical Movement Ledger (Audit Trail)</Title>
            <Table
              dataSource={selectedLotReport.movement_history}
              rowKey="transaction_id"
              pagination={false}
              size="small"
              columns={[
                {
                  title: 'Timestamp',
                  dataIndex: 'timestamp',
                  key: 'timestamp',
                  render: (ts: string) => new Date(ts).toLocaleString(),
                },
                {
                  title: 'Action / Type',
                  dataIndex: 'transaction_type',
                  key: 'type',
                  render: (tp: string) => {
                    const color =
                      tp === 'RECEIPT' ? 'blue' :
                      tp === 'ISSUE' ? 'cyan' :
                      tp === 'CONSUMPTION' ? 'green' :
                      tp === 'RETURN' ? 'orange' : 'red';
                    return <Tag color={color} style={{ fontWeight: 600 }}>{tp}</Tag>;
                  },
                },
                {
                  title: 'Quantity',
                  key: 'qty',
                  render: (_: any, r: any) => <Text strong>{r.quantity} {r.unit_of_measure}</Text>,
                },
                {
                  title: 'Authorized Operator',
                  dataIndex: 'who',
                  key: 'who',
                },
                {
                  title: 'Work Order / Location',
                  key: 'location',
                  render: (_: any, r: any) => r.work_order_number || r.warehouse || 'Store',
                },
                {
                  title: 'Reason / Reference',
                  key: 'reason',
                  render: (_: any, r: any) => (
                    <Space direction="vertical" size={0}>
                      <Text>{r.reason || '—'}</Text>
                      {r.reference && <Text type="secondary" style={{ fontSize: 11 }}>Ref: {r.reference}</Text>}
                    </Space>
                  ),
                },
              ]}
            />
          </div>
        )}
      </Modal>

      {/* Drawer to Add Stock */}
      <Drawer
        title="Add Inventory Item"
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={420}
        extra={
          <Space>
            <Button onClick={() => setDrawerVisible(false)}>Cancel</Button>
            <Button type="primary" onClick={() => form.submit()} loading={submitting}>
              Add to Stock
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="sku" label="SKU Identifier" rules={[{ required: true, message: 'SKU is required' }]}>
            <Input placeholder="e.g. MAT-SILICON-WAFER-01" />
          </Form.Item>

          <Form.Item name="name" label="Product Name" rules={[{ required: true, message: 'Product title required' }]}>
            <Input placeholder="e.g. 300mm Monocrystalline Substrate" />
          </Form.Item>

          <Flex gap="middle">
            <Form.Item name="category" label="Item Category" style={{ flex: 1 }} rules={[{ required: true }]}>
              <Select>
                <Option value="raw_material">Raw Material</Option>
                <Option value="intermediate">Intermediate</Option>
                <Option value="finished_good">Finished Good</Option>
              </Select>
            </Form.Item>

            <Form.Item name="warehouse_id" label="Warehouse Facility" style={{ flex: 1 }} rules={[{ required: true }]}>
              <Input placeholder="e.g. WH-DRESDEN-01" />
            </Form.Item>
          </Flex>

          <Flex gap="middle">
            <Form.Item name="quantity_on_hand" label="Quantity On Hand" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="reorder_point" label="Reorder Threshold" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Flex>

          <Form.Item name="unit_cost" label="Unit Cost ($ USD)" rules={[{ required: true }]}>
            <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
};

export default InventoryPage;
