import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Typography, Table, Tag, Button, Space, Statistic, Alert, Spin } from 'antd';
import {
  ToolOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  ThunderboltOutlined,
  RollbackOutlined,
  DeleteOutlined,
  ArrowRightOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import controlTowerApi, {
  WorkOrderDetailItem,
  EmployeeDashboardStats,
  EmployeeActivityItem,
  DataProvenance,
} from '../../services/controlTowerApi';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import EmptyState from '../../components/common/EmptyState';
import ErrorState from '../../components/common/ErrorState';

const { Title, Text } = Typography;

export const EmployeeDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useApp();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [stats, setStats] = useState<EmployeeDashboardStats>({
    active_work_orders: 0,
    materials_in_holding: 0,
    today_consumed_qty: 0,
    today_returned_qty: 0,
    today_wastage_qty: 0,
    unit: 'kg / units',
  });
  const [workOrders, setWorkOrders] = useState<WorkOrderDetailItem[]>([]);
  const [recentActivity, setRecentActivity] = useState<EmployeeActivityItem[]>([]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, woRes, actRes] = await Promise.all([
        controlTowerApi.getEmployeeDashboardStats(),
        controlTowerApi.getMyWorkOrders(),
        controlTowerApi.getEmployeeActivity(5),
      ]);

      setStats(statsRes.data);
      setWorkOrders(woRes.data);
      setRecentActivity(actRes.data);
      setProvenance(statsRes.provenance);
    } catch (err: any) {
      setError(err?.message || 'Failed to load employee operations data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const woColumns = [
    {
      title: 'Work Order',
      dataIndex: 'work_order_number',
      key: 'work_order_number',
      render: (text: string, record: WorkOrderDetailItem) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#1E40AF', fontSize: 14 }}>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.production_order_number || 'Discrete Job'}</Text>
        </Space>
      ),
    },
    {
      title: 'Target Product',
      key: 'product',
      render: (_: any, record: WorkOrderDetailItem) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: 13 }}>{record.product_name || record.product_sku || 'Assembly'}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>SKU: {record.product_sku || 'N/A'}</Text>
        </Space>
      ),
    },
    {
      title: 'Production Area',
      dataIndex: 'production_area',
      key: 'production_area',
      render: (area: string) => <Tag color="blue">{area || 'Assembly Line'}</Tag>,
    },
    {
      title: 'Planned Qty',
      dataIndex: 'planned_quantity',
      key: 'planned_quantity',
      render: (qty: number) => <Text strong>{qty}</Text>,
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
          size="middle"
          icon={<ArrowRightOutlined />}
          onClick={() => navigate(`/employee/work-orders/${record.id}`)}
          style={{ borderRadius: 6, fontWeight: 600 }}
        >
          Open Job
        </Button>
      ),
    },
  ];

  const activityColumns = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (t: string) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
    {
      title: 'Action',
      dataIndex: 'transaction_type',
      key: 'transaction_type',
      render: (type: string) => {
        let color = 'default';
        if (type === 'CONSUMPTION') color = 'green';
        else if (type === 'RETURN') color = 'orange';
        else if (type === 'WASTAGE') color = 'red';
        else if (type === 'RECEIPT' || type === 'ISSUE') color = 'blue';
        return <Tag color={color}>{type}</Tag>;
      },
    },
    {
      title: 'Material',
      dataIndex: 'product_sku',
      key: 'product_sku',
      render: (sku: string, r: EmployeeActivityItem) => `${sku || 'Item'} (${r.product_name || ''})`,
    },
    {
      title: 'Quantity',
      key: 'quantity',
      render: (_: any, r: EmployeeActivityItem) => (
        <Text strong>{r.quantity} {r.unit_of_measure}</Text>
      ),
    },
    {
      title: 'Reason / Note',
      dataIndex: 'reason',
      key: 'reason',
      render: (reason: string, r: EmployeeActivityItem) => reason || r.notes || '—',
    },
  ];

  if (loading && workOrders.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="Loading shop floor operational data..." />
      </div>
    );
  }

  if (error && workOrders.length === 0) {
    return (
      <ErrorState
        title="Unable to load operations hub"
        message={error}
        onRetry={loadData}
      />
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 10 }}>
            <ToolOutlined style={{ color: '#1E40AF' }} />
            Shop Floor Operations Hub
          </Title>
          <Text type="secondary" style={{ fontSize: 14 }}>
            Operator: <Text strong>{user?.full_name || user?.email || 'Authenticated Operator'}</Text> &bull; Role: <Tag color="geekblue">{user?.role || 'OPERATOR'}</Tag>
          </Text>
        </div>
        <Space>
          <ProvenanceBadge provenance={provenance} sourceNote="Live PostgreSQL Ledger" />
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      {/* KPI Cards Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#BFDBFE', background: '#EFF6FF' }}>
            <Statistic
              title={<span style={{ color: '#1E40AF', fontWeight: 600 }}>Active Jobs</span>}
              value={stats.active_work_orders}
              prefix={<FileTextOutlined style={{ color: '#1E40AF' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={5}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#BAE6FD', background: '#F0F9FF' }}>
            <Statistic
              title={<span style={{ color: '#0284C7', fontWeight: 600 }}>Materials with Me</span>}
              value={stats.materials_in_holding}
              suffix="items"
              prefix={<AppstoreOutlined style={{ color: '#0284C7' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={5}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#A7F3D0', background: '#ECFDF5' }}>
            <Statistic
              title={<span style={{ color: '#059669', fontWeight: 600 }}>Today Consumed</span>}
              value={stats.today_consumed_qty}
              suffix="kg"
              prefix={<ThunderboltOutlined style={{ color: '#059669' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={5}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#FDE68A', background: '#FFFBEB' }}>
            <Statistic
              title={<span style={{ color: '#D97706', fontWeight: 600 }}>Today Returned</span>}
              value={stats.today_returned_qty}
              suffix="kg"
              prefix={<RollbackOutlined style={{ color: '#D97706' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={5}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#FECACA', background: '#FEF2F2' }}>
            <Statistic
              title={<span style={{ color: '#DC2626', fontWeight: 600 }}>Today Scrap/Loss</span>}
              value={stats.today_wastage_qty}
              suffix="kg"
              prefix={<DeleteOutlined style={{ color: '#DC2626' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Action Tables */}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <FileTextOutlined style={{ color: '#1E40AF' }} />
                <span>My Active Work Orders</span>
              </Space>
            }
            extra={
              <Button type="link" onClick={() => navigate('/employee/work-orders')}>
                View All &rarr;
              </Button>
            }
            bordered
            style={{ borderRadius: 8 }}
          >
            {workOrders.length === 0 ? (
              <EmptyState
                title="No Work Orders Assigned"
                description="No active work orders are currently assigned to your shift. Speak with your floor supervisor."
              />
            ) : (
              <Table
                dataSource={workOrders}
                columns={woColumns}
                rowKey="id"
                pagination={false}
                size="middle"
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined style={{ color: '#059669' }} />
                <span>Recent Material Actions</span>
              </Space>
            }
            extra={
              <Button type="link" onClick={() => navigate('/employee/activity')}>
                Full History &rarr;
              </Button>
            }
            bordered
            style={{ borderRadius: 8 }}
          >
            {recentActivity.length === 0 ? (
              <EmptyState
                title="No Movements Recorded Today"
                description="Materials consumed, returned, or reported as scrap will appear here."
              />
            ) : (
              <Table
                dataSource={recentActivity}
                columns={activityColumns}
                rowKey="id"
                pagination={false}
                size="small"
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default EmployeeDashboard;
