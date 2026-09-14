import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Select,
  Input,
  Modal,
  Form,
  Statistic,
  Alert,
  Tooltip,
  message,
  Tabs,
  Badge,
} from 'antd';
import {
  InboxOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  SearchOutlined,
  FilterOutlined,
  QuestionCircleOutlined,
  ShopOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import controlTowerApi, { MaterialRequestItem, DataProvenance } from '../../services/controlTowerApi';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import EmptyState from '../../components/common/EmptyState';
import ErrorState from '../../components/common/ErrorState';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

export const MaterialRequestsQueue: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useApp();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [requests, setRequests] = useState<MaterialRequestItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modals
  const [rejectModalVisible, setRejectModalVisible] = useState<boolean>(false);
  const [issueModalVisible, setIssueModalVisible] = useState<boolean>(false);
  const [selectedRequest, setSelectedRequest] = useState<MaterialRequestItem | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const [rejectForm] = Form.useForm();
  const [issueForm] = Form.useForm();

  const loadRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await controlTowerApi.listMaterialRequests(undefined, false);
      setRequests(res.data);
      setProvenance(res.provenance);
    } catch (err: any) {
      setError(err?.message || 'Failed to load material requisition queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const pendingCount = requests.filter((r) => r.status === 'PENDING').length;
  const approvedCount = requests.filter((r) => r.status === 'APPROVED').length;
  const fulfilledCount = requests.filter((r) => r.status === 'FULFILLED').length;
  const rejectedCount = requests.filter((r) => r.status === 'REJECTED').length;

  const filtered = requests.filter((r) => {
    if (statusFilter !== 'ALL' && r.status !== statusFilter) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (r.work_order_number && r.work_order_number.toLowerCase().includes(q)) ||
      (r.product_sku && r.product_sku.toLowerCase().includes(q)) ||
      (r.product_name && r.product_name.toLowerCase().includes(q)) ||
      (r.requested_by_name && r.requested_by_name.toLowerCase().includes(q)) ||
      (r.reason && r.reason.toLowerCase().includes(q))
    );
  });

  // Approve action
  const handleApprove = async (record: MaterialRequestItem) => {
    try {
      setSubmitting(true);
      await controlTowerApi.approveMaterialRequest(record.id);
      message.success(`Requisition approved for ${record.quantity} ${record.unit_of_measure}. Ready for issue.`);
      await loadRequests();
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to approve requisition.');
    } finally {
      setSubmitting(false);
    }
  };

  // Reject action
  const handleOpenReject = (record: MaterialRequestItem) => {
    setSelectedRequest(record);
    rejectForm.resetFields();
    setRejectModalVisible(true);
  };

  const handleConfirmReject = async () => {
    if (!selectedRequest) return;
    try {
      const values = await rejectForm.validateFields();
      setSubmitting(true);
      await controlTowerApi.rejectMaterialRequest(selectedRequest.id, values.reason, values.notes);
      message.info(`Requisition rejected.`);
      setRejectModalVisible(false);
      await loadRequests();
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to reject requisition.');
    } finally {
      setSubmitting(false);
    }
  };

  // Issue action
  const handleOpenIssue = (record: MaterialRequestItem) => {
    setSelectedRequest(record);
    issueForm.resetFields();
    setIssueModalVisible(true);
  };

  const handleConfirmIssue = async () => {
    if (!selectedRequest) return;
    try {
      const values = await issueForm.validateFields();
      setSubmitting(true);
      const idempotencyKey = `issue_req_${selectedRequest.id}_${Date.now()}`;
      await controlTowerApi.issueMaterialRequest(selectedRequest.id, {
        warehouse_id: values.warehouse_id,
        idempotency_key: idempotencyKey,
        notes: values.notes,
      });
      message.success(`Successfully issued ${selectedRequest.quantity} ${selectedRequest.unit_of_measure} to work order holding.`);
      setIssueModalVisible(false);
      await loadRequests();
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to issue material.');
    } finally {
      setSubmitting(false);
    }
  };

  const isAdmin = user?.role === 'ADMIN';

  const columns = [
    {
      title: 'Work Order',
      key: 'work_order',
      render: (_: any, r: MaterialRequestItem) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#1E40AF', fontSize: 14 }}>
            {r.work_order_number || 'Discrete Job'}
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            ID: <Text code>{r.work_order_id.substring(0, 8)}...</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: 'Material Component',
      key: 'product',
      render: (_: any, r: MaterialRequestItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{r.product_name || r.product_sku}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            SKU: <Text code>{r.product_sku || 'N/A'}</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: 'Requested Qty',
      key: 'quantity',
      render: (_: any, r: MaterialRequestItem) => (
        <Text strong style={{ fontSize: 14 }}>
          {r.quantity} {r.unit_of_measure || 'kg'}
        </Text>
      ),
    },
    {
      title: 'Warehouse Stock',
      key: 'warehouse_stock',
      render: (_: any, r: MaterialRequestItem) => {
        const stock = r.warehouse_stock ?? 0;
        const isSufficient = stock >= r.quantity;
        return (
          <Space direction="vertical" size={0}>
            <Tag color={isSufficient ? 'green' : 'red'} style={{ fontWeight: 600 }}>
              {stock} {r.unit_of_measure || 'kg'} Available
            </Tag>
            {!isSufficient && (
              <Text type="danger" style={{ fontSize: 11 }}>
                Stockout risk (short {(r.quantity - stock).toFixed(1)})
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Holding with Job',
      key: 'holding',
      render: (_: any, r: MaterialRequestItem) => (
        <Tag color="cyan">
          {r.holding_quantity ?? 0} {r.unit_of_measure || 'kg'}
        </Tag>
      ),
    },
    {
      title: 'Requested By',
      key: 'requester',
      render: (_: any, r: MaterialRequestItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{r.requested_by_name || 'Operator'}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {new Date(r.created_at).toLocaleDateString()} {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Reason / Usage',
      dataIndex: 'reason',
      key: 'reason',
      render: (text: string, r: MaterialRequestItem) => (
        <Tooltip title={r.notes || text}>
          <Text ellipsis style={{ maxWidth: 160 }}>
            {text}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_: any, r: MaterialRequestItem) => {
        if (r.status === 'PENDING') {
          return <Tag color="gold" style={{ fontWeight: 600 }}>PENDING REVIEW</Tag>;
        }
        if (r.status === 'APPROVED') {
          return <Tag color="blue" style={{ fontWeight: 600 }}>APPROVED (Awaiting Issue)</Tag>;
        }
        if (r.status === 'FULFILLED') {
          return <Tag color="green" style={{ fontWeight: 600 }}>FULFILLED / ISSUED</Tag>;
        }
        if (r.status === 'REJECTED') {
          return (
            <Tooltip title={`Reason: ${r.rejection_reason || 'Requisition denied'}`}>
              <Tag color="red" style={{ fontWeight: 600 }}>REJECTED</Tag>
            </Tooltip>
          );
        }
        return <Tag>{r.status}</Tag>;
      },
    },
    {
      title: 'Storekeeper Actions',
      key: 'actions',
      render: (_: any, r: MaterialRequestItem) => {
        if (!isAdmin) {
          if (r.status === 'PENDING' || r.status === 'APPROVED') {
            return (
              <Tooltip title="Approval and issuance require Storekeeper or Admin authorization">
                <Tag color="default">Auth Required</Tag>
              </Tooltip>
            );
          }
        }
        if (r.status === 'PENDING') {
          return (
            <Space>
              <Button
                type="primary"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handleApprove(r)}
                loading={submitting}
                style={{ background: '#1E40AF', borderColor: '#1E40AF' }}
              >
                Approve
              </Button>
              <Button
                danger
                size="small"
                icon={<CloseCircleOutlined />}
                onClick={() => handleOpenReject(r)}
                loading={submitting}
              >
                Reject
              </Button>
            </Space>
          );
        }
        if (r.status === 'APPROVED') {
          const stock = r.warehouse_stock ?? 0;
          const isSufficient = stock >= r.quantity;
          return (
            <Button
              type="primary"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => handleOpenIssue(r)}
              loading={submitting}
              disabled={!isSufficient}
              style={{ background: isSufficient ? '#059669' : undefined, borderColor: isSufficient ? '#059669' : undefined }}
            >
              Issue Material
            </Button>
          );
        }
        if (r.status === 'FULFILLED') {
          return (
            <Text type="secondary" style={{ fontSize: 12 }}>
              <CheckCircleOutlined style={{ color: '#059669', marginRight: 4 }} />
              Completed
            </Text>
          );
        }
        if (r.status === 'REJECTED') {
          return (
            <Text type="secondary" style={{ fontSize: 12 }}>
              <CloseCircleOutlined style={{ color: '#DC2626', marginRight: 4 }} />
              Denied
            </Text>
          );
        }
        return null;
      },
    },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 10 }}>
            <InboxOutlined style={{ color: '#1E40AF' }} />
            Material Requisition Queue
          </Title>
          <Text type="secondary" style={{ fontSize: 14 }}>
            Review, approve, and issue warehouse stock for shop floor discrete work orders.
          </Text>
        </div>
        <Space>
          <ProvenanceBadge provenance={provenance} sourceNote="Live PostgreSQL Ledger" />
          <Button icon={<ReloadOutlined />} onClick={loadRequests} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#FDE68A', background: '#FFFBEB' }}>
            <Statistic
              title={<span style={{ color: '#D97706', fontWeight: 600 }}>Pending Review</span>}
              value={pendingCount}
              suffix="requests"
              prefix={<InboxOutlined style={{ color: '#D97706' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#BFDBFE', background: '#EFF6FF' }}>
            <Statistic
              title={<span style={{ color: '#1E40AF', fontWeight: 600 }}>Approved (To Issue)</span>}
              value={approvedCount}
              suffix="requests"
              prefix={<CheckCircleOutlined style={{ color: '#1E40AF' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#A7F3D0', background: '#ECFDF5' }}>
            <Statistic
              title={<span style={{ color: '#059669', fontWeight: 600 }}>Fulfilled / Issued</span>}
              value={fulfilledCount}
              suffix="requests"
              prefix={<ThunderboltOutlined style={{ color: '#059669' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card bordered hoverable style={{ borderRadius: 8, borderColor: '#FECACA', background: '#FEF2F2' }}>
            <Statistic
              title={<span style={{ color: '#DC2626', fontWeight: 600 }}>Rejected Requisitions</span>}
              value={rejectedCount}
              suffix="requests"
              prefix={<CloseCircleOutlined style={{ color: '#DC2626' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Table Card */}
      <Card
        bordered
        style={{ borderRadius: 8 }}
        title={
          <Tabs
            activeKey={statusFilter}
            onChange={setStatusFilter}
            items={[
              { key: 'ALL', label: `All Requisitions (${requests.length})` },
              { key: 'PENDING', label: `Pending (${pendingCount})` },
              { key: 'APPROVED', label: `Approved to Issue (${approvedCount})` },
              { key: 'FULFILLED', label: `Fulfilled (${fulfilledCount})` },
              { key: 'REJECTED', label: `Rejected (${rejectedCount})` },
            ]}
          />
        }
        extra={
          <Input
            placeholder="Search WO, SKU, Operator, Reason..."
            prefix={<SearchOutlined />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
        }
      >
        {!isAdmin && (
          <Alert
            type="info"
            showIcon
            message="Storekeeper Control View (Read-Only)"
            description="Your account is currently in floor operator/viewer view. Only users with Storekeeper or Administrator authorization can approve requisitions and dispatch warehouse stock."
            style={{ marginBottom: 16 }}
          />
        )}
        {filtered.length === 0 ? (
          <EmptyState
            title="No Material Requests Found"
            description="Requisitions submitted by floor operators will appear here for storekeeper review."
          />
        ) : (
          <Table
            dataSource={filtered}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 15 }}
            loading={loading}
            scroll={{ x: 1100 }}
          />
        )}
      </Card>

      {/* Reject Modal */}
      <Modal
        title={
          <Space>
            <CloseCircleOutlined style={{ color: '#DC2626' }} />
            <span>Reject Material Requisition</span>
          </Space>
        }
        open={rejectModalVisible}
        onCancel={() => setRejectModalVisible(false)}
        onOk={handleConfirmReject}
        confirmLoading={submitting}
        okText="Confirm Rejection"
        okButtonProps={{ danger: true }}
      >
        <Paragraph type="secondary">
          Rejecting a requisition notifies the floor operator with a mandatory explanation. No inventory movement will occur.
        </Paragraph>
        <Form form={rejectForm} layout="vertical">
          <Form.Item
            name="reason"
            label="Rejection Reason (Mandatory)"
            rules={[{ required: true, message: 'Please provide a clear rejection reason' }]}
          >
            <Input placeholder="e.g. Insufficient warehouse lot; alternate SKU required" />
          </Form.Item>
          <Form.Item name="notes" label="Additional Floor Supervisor Notes (Optional)">
            <Input.TextArea rows={2} placeholder="Optional notes for operator" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Issue Modal */}
      <Modal
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#059669' }} />
            <span>Confirm Physical Material Issue</span>
          </Space>
        }
        open={issueModalVisible}
        onCancel={() => setIssueModalVisible(false)}
        onOk={handleConfirmIssue}
        confirmLoading={submitting}
        okText="Issue Material from Warehouse"
        okButtonProps={{ style: { background: '#059669', borderColor: '#059669' } }}
      >
        <Alert
          type="info"
          showIcon
          message="Inventory Movement Invariant"
          description={`Issuing ${selectedRequest?.quantity} ${selectedRequest?.unit_of_measure} will atomically decrease warehouse stock and increase work order holding. Central warehouse inventory will NOT be decremented again when the operator consumes it.`}
          style={{ marginBottom: 16 }}
        />
        <div style={{ background: '#F8FAFC', padding: 12, borderRadius: 6, marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={12}>
              <Text type="secondary">Work Order:</Text> <Text strong>{selectedRequest?.work_order_number || 'Discrete Job'}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary">Component:</Text> <Text strong>{selectedRequest?.product_sku}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary">Issue Quantity:</Text> <Text strong style={{ color: '#059669' }}>{selectedRequest?.quantity} {selectedRequest?.unit_of_measure}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary">Available Stock:</Text> <Text strong>{selectedRequest?.warehouse_stock ?? '—'} {selectedRequest?.unit_of_measure}</Text>
            </Col>
          </Row>
        </div>
        <Form form={issueForm} layout="vertical">
          <Form.Item name="notes" label="Storekeeper Dispatch Notes (Optional)">
            <Input.TextArea rows={2} placeholder="e.g. Dispatched from Bay 4B via forklift" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MaterialRequestsQueue;
