import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Typography, Select, Input, Badge, Spin } from 'antd';
import {
  FileTextOutlined,
  ArrowRightOutlined,
  ReloadOutlined,
  SearchOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import controlTowerApi, { WorkOrderDetailItem, DataProvenance } from '../../services/controlTowerApi';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import EmptyState from '../../components/common/EmptyState';
import ErrorState from '../../components/common/ErrorState';

const { Title, Text } = Typography;
const { Option } = Select;

export const MyWorkOrders: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [workOrders, setWorkOrders] = useState<WorkOrderDetailItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadWorkOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await controlTowerApi.getMyWorkOrders(statusFilter === 'ALL' ? undefined : statusFilter);
      setWorkOrders(res.data);
      setProvenance(res.provenance);
    } catch (err: any) {
      setError(err?.message || 'Failed to load assigned work orders.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkOrders();
  }, [statusFilter]);

  const filteredOrders = workOrders.filter((w) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      w.work_order_number.toLowerCase().includes(q) ||
      (w.production_order_number && w.production_order_number.toLowerCase().includes(q)) ||
      (w.product_name && w.product_name.toLowerCase().includes(q)) ||
      (w.product_sku && w.product_sku.toLowerCase().includes(q)) ||
      (w.production_area && w.production_area.toLowerCase().includes(q))
    );
  });

  const columns = [
    {
      title: 'Work Order #',
      dataIndex: 'work_order_number',
      key: 'work_order_number',
      render: (text: string, record: WorkOrderDetailItem) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#1E40AF', fontSize: 14 }}>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>PO: {record.production_order_number || 'Discrete'}</Text>
        </Space>
      ),
    },
    {
      title: 'Finished Good Assembly',
      key: 'product',
      render: (_: any, record: WorkOrderDetailItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.product_name || record.product_sku || 'Product Assembly'}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>SKU: {record.product_sku || 'N/A'}</Text>
        </Space>
      ),
    },
    {
      title: 'Production Area',
      dataIndex: 'production_area',
      key: 'production_area',
      render: (area: string) => <Tag color="geekblue">{area || 'General Assembly'}</Tag>,
    },
    {
      title: 'Planned Qty',
      dataIndex: 'planned_quantity',
      key: 'planned_quantity',
      render: (qty: number, r: WorkOrderDetailItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{qty} units</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>Completed: {r.completed_quantity}</Text>
        </Space>
      ),
    },
    {
      title: 'Materials Tracking',
      key: 'materials_summary',
      render: (_: any, r: WorkOrderDetailItem) => {
        const matCount = r.materials ? r.materials.length : 0;
        const activeHolding = r.materials ? r.materials.filter((m) => m.remaining_issued_holding > 0).length : 0;
        return (
          <Space direction="vertical" size={0}>
            <Text>{matCount} materials required</Text>
            {activeHolding > 0 ? (
              <Badge status="processing" text={<Text style={{ color: '#0284C7', fontSize: 12 }}>{activeHolding} items with holding</Text>} />
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>0 holding</Text>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'default';
        if (status === 'IN_PROGRESS') color = 'processing';
        else if (status === 'COMPLETED') color = 'success';
        else if (status === 'ON_HOLD') color = 'warning';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: WorkOrderDetailItem) => (
        <Button
          type="primary"
          icon={<ArrowRightOutlined />}
          onClick={() => navigate(`/employee/work-orders/${record.id}`)}
          style={{ borderRadius: 6, fontWeight: 600 }}
        >
          View Job & Materials
        </Button>
      ),
    },
  ];

  if (loading && workOrders.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="Loading assigned work orders..." />
      </div>
    );
  }

  if (error && workOrders.length === 0) {
    return (
      <ErrorState
        title="Failed to load work orders"
        message={error}
        onRetry={loadWorkOrders}
      />
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <Title level={2} style={{ margin: 0, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 10 }}>
            <FileTextOutlined style={{ color: '#1E40AF' }} />
            My Work Orders
          </Title>
          <Text type="secondary">
            Manufacturing jobs and discrete assemblies assigned to your account.
          </Text>
        </div>
        <Space>
          <ProvenanceBadge provenance={provenance} sourceNote="Assigned Work Orders from Central Ledger" />
          <Button icon={<ReloadOutlined />} onClick={loadWorkOrders} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      {/* Filter Bar */}
      <Card bordered style={{ borderRadius: 8, marginBottom: 20 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', justifyContent: 'space-between' }}>
          <Input
            placeholder="Search by WO#, PO#, Product, or Line..."
            prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ maxWidth: 360, borderRadius: 6 }}
            allowClear
          />

          <Space>
            <FilterOutlined style={{ color: '#64748B' }} />
            <Text type="secondary">Status Filter:</Text>
            <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 160 }}>
              <Option value="ALL">All Statuses</Option>
              <Option value="PLANNED">PLANNED</Option>
              <Option value="IN_PROGRESS">IN_PROGRESS</Option>
              <Option value="ON_HOLD">ON_HOLD</Option>
              <Option value="COMPLETED">COMPLETED</Option>
            </Select>
          </Space>
        </div>
      </Card>

      {/* Table */}
      <Card bordered style={{ borderRadius: 8 }}>
        {filteredOrders.length === 0 ? (
          <EmptyState
            title="No Work Orders Found"
            description={
              searchQuery
                ? `No work orders matched "${searchQuery}".`
                : 'No work orders are currently assigned to you.'
            }
          />
        ) : (
          <Table
            dataSource={filteredOrders}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10, showSizeChanger: true }}
          />
        )}
      </Card>
    </div>
  );
};

export default MyWorkOrders;
