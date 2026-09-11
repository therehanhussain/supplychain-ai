import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Space, Typography, Select, Button, Spin, Input } from 'antd';
import {
  HistoryOutlined,
  ReloadOutlined,
  FilterOutlined,
  SearchOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import controlTowerApi, { EmployeeActivityItem, DataProvenance } from '../../services/controlTowerApi';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import EmptyState from '../../components/common/EmptyState';
import ErrorState from '../../components/common/ErrorState';

const { Title, Text } = Typography;
const { Option } = Select;

export const MyActivity: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [activities, setActivities] = useState<EmployeeActivityItem[]>([]);
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadActivity = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await controlTowerApi.getEmployeeActivity(100);
      setActivities(res.data);
      setProvenance(res.provenance);
    } catch (err: any) {
      setError(err?.message || 'Failed to load personal activity history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActivity();
  }, []);

  const filtered = activities.filter((act) => {
    if (typeFilter !== 'ALL' && act.transaction_type !== typeFilter) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (act.product_sku && act.product_sku.toLowerCase().includes(q)) ||
      (act.product_name && act.product_name.toLowerCase().includes(q)) ||
      (act.reason && act.reason.toLowerCase().includes(q)) ||
      (act.notes && act.notes.toLowerCase().includes(q))
    );
  });

  const columns = [
    {
      title: 'Timestamp (UTC)',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (t: string) => (
        <Space direction="vertical" size={0}>
          <Text strong>{new Date(t).toLocaleDateString()}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>{new Date(t).toLocaleTimeString()}</Text>
        </Space>
      ),
    },
    {
      title: 'Action Type',
      dataIndex: 'transaction_type',
      key: 'transaction_type',
      render: (type: string) => {
        let color = 'default';
        if (type === 'CONSUMPTION') color = 'green';
        else if (type === 'RETURN') color = 'orange';
        else if (type === 'WASTAGE') color = 'red';
        else if (type === 'RECEIPT') color = 'blue';
        else if (type === 'ISSUE') color = 'cyan';
        return (
          <Tag color={color} style={{ fontWeight: 600, padding: '2px 8px' }}>
            {type}
          </Tag>
        );
      },
    },
    {
      title: 'Material Component',
      key: 'material',
      render: (_: any, r: EmployeeActivityItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{r.product_name || r.product_sku}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>SKU: <Text code>{r.product_sku || 'N/A'}</Text></Text>
        </Space>
      ),
    },
    {
      title: 'Quantity',
      key: 'quantity',
      render: (_: any, r: EmployeeActivityItem) => (
        <Text strong style={{ fontSize: 14 }}>
          {r.quantity} {r.unit_of_measure}
        </Text>
      ),
    },
    {
      title: 'Facility / Work Order',
      key: 'facility',
      render: (_: any, r: EmployeeActivityItem) => (
        <Space direction="vertical" size={0}>
          <Text>{r.warehouse_code || 'Warehouse'}</Text>
          {r.work_order_id && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              Job: {r.work_order_id.substring(0, 8)}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Reason / Usage Description',
      key: 'reason',
      render: (_: any, r: EmployeeActivityItem) => (
        <Text>{r.reason || r.notes || '—'}</Text>
      ),
    },
    {
      title: 'Audit Status',
      key: 'audit',
      render: () => (
        <Tag icon={<CheckCircleOutlined />} color="success">
          Committed
        </Tag>
      ),
    },
  ];

  if (loading && activities.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="Loading personal activity ledger..." />
      </div>
    );
  }

  if (error && activities.length === 0) {
    return (
      <ErrorState
        title="Failed to load activity history"
        message={error}
        onRetry={loadActivity}
      />
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <Title level={2} style={{ margin: 0, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 10 }}>
            <HistoryOutlined style={{ color: '#1E40AF' }} />
            My Material Activity Ledger
          </Title>
          <Text type="secondary">
            Immutable log of all material movements executed under your authenticated operator account.
          </Text>
        </div>
        <Space>
          <ProvenanceBadge provenance={provenance} sourceNote="Authoritative Operator Transaction Ledger" />
          <Button icon={<ReloadOutlined />} onClick={loadActivity} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      {/* Filter Card */}
      <Card bordered style={{ borderRadius: 8, marginBottom: 20 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', justifyContent: 'space-between' }}>
          <Input
            placeholder="Search material SKU, name, or reason..."
            prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ maxWidth: 360, borderRadius: 6 }}
            allowClear
          />

          <Space>
            <FilterOutlined style={{ color: '#64748B' }} />
            <Text type="secondary">Transaction Type:</Text>
            <Select value={typeFilter} onChange={setTypeFilter} style={{ width: 170 }}>
              <Option value="ALL">All Actions</Option>
              <Option value="CONSUMPTION">CONSUMPTION</Option>
              <Option value="RETURN">RETURN</Option>
              <Option value="WASTAGE">WASTAGE</Option>
              <Option value="RECEIPT">RECEIPT</Option>
              <Option value="ISSUE">ISSUE</Option>
            </Select>
          </Space>
        </div>
      </Card>

      {/* Table */}
      <Card bordered style={{ borderRadius: 8 }}>
        {filtered.length === 0 ? (
          <EmptyState
            title="No Activity Records Found"
            description="You have not executed any material transactions under this filter yet."
          />
        ) : (
          <Table
            dataSource={filtered}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 15, showSizeChanger: true }}
          />
        )}
      </Card>
    </div>
  );
};

export default MyActivity;
