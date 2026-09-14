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
  Descriptions,
  Modal,
  Form,
  InputNumber,
  Input,
  message,
  Alert,
  Spin,
  Tooltip,
  Select,
} from 'antd';
import {
  ArrowLeftOutlined,
  ThunderboltOutlined,
  RollbackOutlined,
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import controlTowerApi, {
  WorkOrderDetailItem,
  MaterialRequirementItem,
  MaterialRequestItem,
  DataProvenance,
} from '../../services/controlTowerApi';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import EmptyState from '../../components/common/EmptyState';
import ErrorState from '../../components/common/ErrorState';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

export const WorkOrderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [workOrder, setWorkOrder] = useState<WorkOrderDetailItem | null>(null);
  const [materials, setMaterials] = useState<MaterialRequirementItem[]>([]);
  const [requisitions, setRequisitions] = useState<MaterialRequestItem[]>([]);

  // Modal States
  const [consumeModalVisible, setConsumeModalVisible] = useState<boolean>(false);
  const [returnModalVisible, setReturnModalVisible] = useState<boolean>(false);
  const [wasteModalVisible, setWasteModalVisible] = useState<boolean>(false);
  const [requestModalVisible, setRequestModalVisible] = useState<boolean>(false);
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialRequirementItem | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const [form] = Form.useForm();

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [woRes, matRes, reqRes] = await Promise.all([
        controlTowerApi.getWorkOrderDetail(id),
        controlTowerApi.getWorkOrderMaterials(id),
        controlTowerApi.listMaterialRequests(id, true),
      ]);

      if (!woRes.data) {
        throw new Error('Work order not found or access forbidden.');
      }
      setWorkOrder(woRes.data);
      setMaterials(matRes.data || []);
      setRequisitions(reqRes.data || []);
      setProvenance(woRes.provenance);
    } catch (err: any) {
      setError(err?.message || 'Failed to load work order detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  // Open modals
  const handleOpenConsume = (record: MaterialRequirementItem) => {
    setSelectedMaterial(record);
    form.resetFields();
    const lots = (workOrder?.lot_holdings || []).filter(
      (h) => h.product_id === record.product_id && h.remaining_holding > 0
    );
    form.setFieldsValue({
      lot_id: lots.length === 1 ? lots[0].lot_id : undefined,
      quantity: record.remaining_issued_holding > 0 ? Math.min(1.0, record.remaining_issued_holding) : 0,
      reason: 'Production assembly',
    });
    setConsumeModalVisible(true);
  };

  const handleOpenReturn = (record: MaterialRequirementItem) => {
    setSelectedMaterial(record);
    form.resetFields();
    const lots = (workOrder?.lot_holdings || []).filter(
      (h) => h.product_id === record.product_id && h.remaining_holding > 0
    );
    form.setFieldsValue({
      lot_id: lots.length === 1 ? lots[0].lot_id : undefined,
      quantity: record.remaining_issued_holding > 0 ? Math.min(1.0, record.remaining_issued_holding) : 0,
      reason: 'Surplus material returned to store',
    });
    setReturnModalVisible(true);
  };

  const handleOpenWaste = (record: MaterialRequirementItem) => {
    setSelectedMaterial(record);
    form.resetFields();
    const lots = (workOrder?.lot_holdings || []).filter(
      (h) => h.product_id === record.product_id && h.remaining_holding > 0
    );
    form.setFieldsValue({
      lot_id: lots.length === 1 ? lots[0].lot_id : undefined,
      quantity: record.remaining_issued_holding > 0 ? Math.min(1.0, record.remaining_issued_holding) : 0,
      reason: '',
    });
    setWasteModalVisible(true);
  };

  const handleOpenRequest = (record?: MaterialRequirementItem) => {
    setSelectedMaterial(record || null);
    form.resetFields();
    form.setFieldsValue({
      quantity: 10.0,
      unit_of_measure: record?.unit_of_measure || 'kg',
      reason: 'Line replenishment for assembly run',
    });
    setRequestModalVisible(true);
  };

  // Submit Consume
  const handleSubmitConsume = async () => {
    if (!workOrder || !selectedMaterial) return;
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const idempotencyKey = `consume_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      await controlTowerApi.consumeMaterial({
        work_order_id: workOrder.id,
        product_id: selectedMaterial.product_id,
        lot_id: values.lot_id || undefined,
        quantity: values.quantity,
        unit_of_measure: selectedMaterial.unit_of_measure,
        reason: values.reason,
        notes: values.notes,
        idempotency_key: idempotencyKey,
      });

      message.success(`${values.quantity} ${selectedMaterial.unit_of_measure} recorded as consumed.`);
      setConsumeModalVisible(false);
      await loadData();
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to consume material.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Return
  const handleSubmitReturn = async () => {
    if (!workOrder || !selectedMaterial) return;
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const idempotencyKey = `return_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      await controlTowerApi.returnMaterial({
        work_order_id: workOrder.id,
        product_id: selectedMaterial.product_id,
        lot_id: values.lot_id || undefined,
        quantity: values.quantity,
        unit_of_measure: selectedMaterial.unit_of_measure,
        reason: values.reason,
        notes: values.notes,
        idempotency_key: idempotencyKey,
      });

      message.success(`${values.quantity} ${selectedMaterial.unit_of_measure} returned to warehouse.`);
      setReturnModalVisible(false);
      await loadData();
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to return material.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Wastage
  const handleSubmitWaste = async () => {
    if (!workOrder || !selectedMaterial) return;
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const idempotencyKey = `waste_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      await controlTowerApi.reportWastage({
        work_order_id: workOrder.id,
        product_id: selectedMaterial.product_id,
        lot_id: values.lot_id || undefined,
        quantity: values.quantity,
        unit_of_measure: selectedMaterial.unit_of_measure,
        reason: values.reason,
        notes: values.notes,
        idempotency_key: idempotencyKey,
      });

      message.success(`${values.quantity} ${selectedMaterial.unit_of_measure} scrap logged.`);
      setWasteModalVisible(false);
      await loadData();
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to report scrap.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Request
  const handleSubmitRequest = async () => {
    if (!workOrder) return;
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await controlTowerApi.createMaterialRequest({
        work_order_id: workOrder.id,
        product_id: selectedMaterial ? selectedMaterial.product_id : values.product_id,
        quantity: values.quantity,
        unit_of_measure: values.unit_of_measure || 'kg',
        reason: values.reason,
        notes: values.notes,
      });

      message.success(`Requisition submitted for ${values.quantity} ${values.unit_of_measure}.`);
      setRequestModalVisible(false);
      await loadData();
    } catch (err: any) {
      message.error(err?.response?.data?.message || err?.message || 'Failed to submit request.');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      title: 'Material / Component',
      key: 'product',
      render: (_: any, r: MaterialRequirementItem) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: 14 }}>{r.product_name || r.product_sku}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            SKU: <Text code>{r.product_sku}</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: 'Required',
      dataIndex: 'required_quantity',
      key: 'required_quantity',
      render: (qty: number, r: MaterialRequirementItem) => (
        <Text>{qty} {r.unit_of_measure}</Text>
      ),
    },
    {
      title: 'Issued (Store -> Floor)',
      dataIndex: 'issued_quantity',
      key: 'issued_quantity',
      render: (qty: number, r: MaterialRequirementItem) => (
        <Text strong style={{ color: qty > 0 ? '#1E40AF' : '#94A3B8' }}>
          {qty} {r.unit_of_measure}
        </Text>
      ),
    },
    {
      title: 'Consumed',
      dataIndex: 'consumed_quantity',
      key: 'consumed_quantity',
      render: (qty: number, r: MaterialRequirementItem) => (
        <Text style={{ color: '#059669' }}>{qty} {r.unit_of_measure}</Text>
      ),
    },
    {
      title: 'Returned',
      dataIndex: 'returned_quantity',
      key: 'returned_quantity',
      render: (qty: number, r: MaterialRequirementItem) => (
        <Text style={{ color: '#D97706' }}>{qty} {r.unit_of_measure}</Text>
      ),
    },
    {
      title: 'Scrap / Loss',
      dataIndex: 'wastage_quantity',
      key: 'wastage_quantity',
      render: (qty: number, r: MaterialRequirementItem) => (
        <Text style={{ color: '#DC2626' }}>{qty} {r.unit_of_measure}</Text>
      ),
    },
    {
      title: 'Holding Available to Use',
      key: 'holding',
      render: (_: any, r: MaterialRequirementItem) => {
        const h = r.remaining_issued_holding;
        return (
          <Tag
            color={h > 0 ? 'cyan' : 'default'}
            style={{ fontSize: 13, padding: '4px 8px', fontWeight: 700 }}
          >
            {h} {r.unit_of_measure}
          </Tag>
        );
      },
    },
    {
      title: 'Floor Actions',
      key: 'actions',
      render: (_: any, r: MaterialRequirementItem) => {
        const canAct = r.remaining_issued_holding > 0;
        return (
          <Space wrap>
            <Button
              type="primary"
              size="small"
              icon={<ThunderboltOutlined />}
              disabled={!canAct}
              onClick={() => handleOpenConsume(r)}
              style={{ background: canAct ? '#059669' : undefined, borderColor: canAct ? '#059669' : undefined }}
            >
              Use
            </Button>
            <Button
              size="small"
              icon={<RollbackOutlined />}
              disabled={!canAct}
              onClick={() => handleOpenReturn(r)}
            >
              Return
            </Button>
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
              disabled={!canAct}
              onClick={() => handleOpenWaste(r)}
            >
              Waste
            </Button>
            <Button
              size="small"
              icon={<PlusOutlined />}
              onClick={() => handleOpenRequest(r)}
            >
              Request
            </Button>
          </Space>
        );
      },
    },
  ];

  if (loading && !workOrder) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="Loading work order details..." />
      </div>
    );
  }

  if (error && !workOrder) {
    return (
      <ErrorState
        title="Unable to open work order"
        message={error}
        onRetry={loadData}
      />
    );
  }

  if (!workOrder) return null;

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
      {/* Top Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/employee/work-orders')}>
            Back to Orders
          </Button>
          <Title level={3} style={{ margin: 0 }}>
            {workOrder.work_order_number}
          </Title>
          <Tag color="processing" style={{ fontSize: 13, padding: '2px 8px' }}>
            {workOrder.status}
          </Tag>
        </Space>
        <Space>
          <ProvenanceBadge provenance={provenance} sourceNote="Authoritative Work Order Detail" />
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            Refresh
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleOpenRequest()}
            style={{ borderRadius: 6 }}
          >
            Request Extra Material
          </Button>
        </Space>
      </div>

      {/* Info Card */}
      <Card bordered style={{ borderRadius: 8, marginBottom: 24 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 4 }} bordered size="middle">
          <Descriptions.Item label="Target Assembly">
            <Text strong>{workOrder.product_name || workOrder.product_sku || 'Assembly'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Production Order">
            <Text code>{workOrder.production_order_number || 'Discrete Job'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Production Area">
            <Tag color="blue">{workOrder.production_area || 'Main Plant'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Assigned Operator">
            <Text strong>{workOrder.assigned_user_name || 'Assigned Operator'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Planned Quantity">
            <Text strong>{workOrder.planned_quantity} units</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Completed Quantity">
            <Text>{workOrder.completed_quantity} units</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Source Warehouse">
            <Text>{workOrder.warehouse_code || 'Central Store'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Created At">
            <Text type="secondary">{new Date(workOrder.created_at).toLocaleDateString()}</Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Materials Table */}
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text strong style={{ fontSize: 16 }}>Bill of Materials & Floor Holding</Text>
              <Tag color="geekblue">{materials.length} Materials</Tag>
            </Space>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Invariance: <Text code>Issued = Consumed + Returned + Wastage + Holding</Text>
            </Text>
          </div>
        }
        bordered
        style={{ borderRadius: 8 }}
      >
        {materials.length === 0 ? (
          <EmptyState
            title="No Material Requirements"
            description="No materials have been defined for this work order yet. Click 'Request Extra Material' to submit a requisition."
          />
        ) : (
          <Table
            dataSource={materials}
            columns={columns}
            rowKey="id"
            pagination={false}
            scroll={{ x: 950 }}
          />
        )}
      </Card>

      {/* Work Order Lot Holdings Table */}
      {workOrder.lot_holdings && workOrder.lot_holdings.length > 0 && (
        <Card
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <ThunderboltOutlined style={{ color: '#059669' }} />
                <Text strong style={{ fontSize: 16 }}>Physical Material Lot Holdings</Text>
                <Tag color="cyan">{workOrder.lot_holdings.length} Active Lots</Tag>
              </Space>
              <Text type="secondary" style={{ fontSize: 13 }}>
                Multi-Lot Isolation: <Text code>Holding = Issued - Consumed - Returned - Wastage</Text>
              </Text>
            </div>
          }
          bordered
          style={{ borderRadius: 8, marginTop: 24 }}
        >
          <Table
            dataSource={workOrder.lot_holdings}
            rowKey="id"
            pagination={false}
            columns={[
              {
                title: 'Lot Number',
                key: 'lot_number',
                render: (_: any, r: any) => (
                  <Space direction="vertical" size={0}>
                    <Text strong style={{ color: '#1E40AF', fontFamily: 'monospace' }}>
                      {r.lot_number || 'LOT-N/A'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      ID: <Text code>{r.lot_id.substring(0, 8)}...</Text>
                    </Text>
                  </Space>
                ),
              },
              {
                title: 'Material Component',
                key: 'product',
                render: (_: any, r: any) => (
                  <Space direction="vertical" size={0}>
                    <Text strong>{r.product_name || r.product_sku}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      SKU: <Text code>{r.product_sku || 'N/A'}</Text>
                    </Text>
                  </Space>
                ),
              },
              {
                title: 'Issued to WO',
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
                title: 'Floor Holding Balance',
                key: 'remaining_holding',
                render: (_: any, r: any) => (
                  <Tag color={r.remaining_holding > 0 ? 'green' : 'default'} style={{ fontWeight: 600, fontSize: 13, padding: '2px 8px' }}>
                    {r.remaining_holding} {r.unit_of_measure}
                  </Tag>
                ),
              },
            ]}
          />
        </Card>
      )}

      {/* Material Requisitions Status Table */}
      <Card
        title={
          <Space>
            <PlusOutlined style={{ color: '#1E40AF' }} />
            <Text strong style={{ fontSize: 16 }}>Requisitions for this Work Order</Text>
            <Tag color="blue">{requisitions.length} Requests</Tag>
          </Space>
        }
        bordered
        style={{ borderRadius: 8, marginTop: 24 }}
      >
        {requisitions.length === 0 ? (
          <EmptyState
            title="No Extra Requisitions Submitted"
            description="If additional material is needed from the warehouse for this job, click 'Request Extra Material'."
          />
        ) : (
          <Table
            dataSource={requisitions}
            rowKey="id"
            pagination={false}
            scroll={{ x: 850 }}
            columns={[
              {
                title: 'Component / Material',
                key: 'product',
                render: (_: any, r: MaterialRequestItem) => (
                  <Space direction="vertical" size={0}>
                    <Text strong>{r.product_name || r.product_sku}</Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>SKU: <Text code>{r.product_sku}</Text></Text>
                  </Space>
                ),
              },
              {
                title: 'Requested Qty',
                key: 'quantity',
                render: (_: any, r: MaterialRequestItem) => (
                  <Text strong>{r.quantity} {r.unit_of_measure}</Text>
                ),
              },
              {
                title: 'Reason / Usage Note',
                dataIndex: 'reason',
                key: 'reason',
              },
              {
                title: 'Requested At',
                dataIndex: 'created_at',
                key: 'created_at',
                render: (t: string) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + new Date(t).toLocaleDateString(),
              },
              {
                title: 'Reviewer / Storekeeper',
                key: 'reviewer',
                render: (_: any, r: MaterialRequestItem) => {
                  if (r.reviewed_by_name) {
                    return <Text strong style={{ fontSize: 12 }}>{r.reviewed_by_name}</Text>;
                  }
                  if (r.status === 'PENDING') {
                    return <Text type="secondary" style={{ fontStyle: 'italic', fontSize: 12 }}>Awaiting Review</Text>;
                  }
                  return <Text type="secondary">—</Text>;
                },
              },
              {
                title: 'Requisition Status',
                key: 'status',
                render: (_: any, r: MaterialRequestItem) => {
                  if (r.status === 'PENDING') {
                    return <Tag color="gold" style={{ fontWeight: 600 }}>PENDING REVIEW</Tag>;
                  }
                  if (r.status === 'APPROVED') {
                    return <Tag color="blue" style={{ fontWeight: 600 }}>APPROVED (Awaiting Warehouse Issue)</Tag>;
                  }
                  if (r.status === 'FULFILLED') {
                    return <Tag color="green" style={{ fontWeight: 600 }}>FULFILLED / ISSUED TO HOLDING</Tag>;
                  }
                  if (r.status === 'REJECTED') {
                    return (
                      <Tooltip title={`Rejection Reason: ${r.rejection_reason || 'Denied by storekeeper'}`}>
                        <Tag color="red" style={{ fontWeight: 600 }}>REJECTED</Tag>
                      </Tooltip>
                    );
                  }
                  return <Tag>{r.status}</Tag>;
                },
              },
            ]}
          />
        )}
      </Card>

      {/* ---------------------------------------------------------------------- */}
      {/* CONSUME MODAL */}
      {/* ---------------------------------------------------------------------- */}
      <Modal
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#059669' }} />
            <span>Record Material Consumption</span>
          </Space>
        }
        open={consumeModalVisible}
        onCancel={() => setConsumeModalVisible(false)}
        onOk={handleSubmitConsume}
        confirmLoading={submitting}
        okText="Confirm Consumption"
        okButtonProps={{ style: { background: '#059669', borderColor: '#059669' } }}
      >
        <Paragraph type="secondary">
          Deducts material from your work order holding. Central warehouse inventory is not altered.
        </Paragraph>
        <Alert
          type="info"
          message={`Available Holding: ${selectedMaterial?.remaining_issued_holding} ${selectedMaterial?.unit_of_measure}`}
          style={{ marginBottom: 16 }}
        />
        <Form form={form} layout="vertical">
          {((workOrder?.lot_holdings || []).filter((h) => h.product_id === selectedMaterial?.product_id).length > 0) && (
            <Form.Item
              name="lot_id"
              label="Select Work Order Lot Holding"
              tooltip="Specify which raw material lot you are using for strict traceability."
            >
              <Select placeholder="Select holding lot (optional if unallocated)" allowClear>
                {(workOrder?.lot_holdings || [])
                  .filter((h) => h.product_id === selectedMaterial?.product_id)
                  .map((h) => (
                    <Option key={h.lot_id} value={h.lot_id} disabled={h.remaining_holding <= 0}>
                      {h.lot_number || h.lot_id} — Holding: {h.remaining_holding} {h.unit_of_measure}
                    </Option>
                  ))}
              </Select>
            </Form.Item>
          )}
          <Form.Item
            name="quantity"
            label={`Quantity to Consume (${selectedMaterial?.unit_of_measure})`}
            rules={[
              { required: true, message: 'Please enter quantity' },
              {
                type: 'number',
                min: 0.001,
                max: selectedMaterial?.remaining_issued_holding,
                message: `Must be between 0.001 and ${selectedMaterial?.remaining_issued_holding}`,
              },
            ]}
          >
            <InputNumber style={{ width: '100%' }} step={0.1} precision={2} />
          </Form.Item>
          <Form.Item
            name="reason"
            label="Usage Rationale / Operation"
            rules={[{ required: true, message: 'Please specify usage note' }]}
          >
            <Input placeholder="e.g. Frame fabrication and welding" />
          </Form.Item>
          <Form.Item name="notes" label="Additional Floor Notes (Optional)">
            <Input.TextArea rows={2} placeholder="Optional notes" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---------------------------------------------------------------------- */}
      {/* RETURN MODAL */}
      {/* ---------------------------------------------------------------------- */}
      <Modal
        title={
          <Space>
            <RollbackOutlined style={{ color: '#D97706' }} />
            <span>Return Surplus Material to Store</span>
          </Space>
        }
        open={returnModalVisible}
        onCancel={() => setReturnModalVisible(false)}
        onOk={handleSubmitReturn}
        confirmLoading={submitting}
        okText="Confirm Return"
      >
        <Paragraph type="secondary">
          Returns unused material back to central store shelving. Central warehouse inventory will increment.
        </Paragraph>
        <Alert
          type="warning"
          message={`Holding with you: ${selectedMaterial?.remaining_issued_holding} ${selectedMaterial?.unit_of_measure}`}
          style={{ marginBottom: 16 }}
        />
        <Form form={form} layout="vertical">
          {((workOrder?.lot_holdings || []).filter((h) => h.product_id === selectedMaterial?.product_id).length > 0) && (
            <Form.Item
              name="lot_id"
              label="Select Work Order Lot Holding"
              tooltip="Specify which lot balance you are returning to store."
            >
              <Select placeholder="Select holding lot (optional if unallocated)" allowClear>
                {(workOrder?.lot_holdings || [])
                  .filter((h) => h.product_id === selectedMaterial?.product_id)
                  .map((h) => (
                    <Option key={h.lot_id} value={h.lot_id} disabled={h.remaining_holding <= 0}>
                      {h.lot_number || h.lot_id} — Holding: {h.remaining_holding} {h.unit_of_measure}
                    </Option>
                  ))}
              </Select>
            </Form.Item>
          )}
          <Form.Item
            name="quantity"
            label={`Quantity to Return (${selectedMaterial?.unit_of_measure})`}
            rules={[
              { required: true, message: 'Please enter quantity' },
              {
                type: 'number',
                min: 0.001,
                max: selectedMaterial?.remaining_issued_holding,
                message: `Cannot exceed holding balance of ${selectedMaterial?.remaining_issued_holding}`,
              },
            ]}
          >
            <InputNumber style={{ width: '100%' }} step={0.1} precision={2} />
          </Form.Item>
          <Form.Item
            name="reason"
            label="Return Reason"
            rules={[{ required: true, message: 'Please provide return reason' }]}
          >
            <Input placeholder="e.g. Surplus material returned at end of shift" />
          </Form.Item>
          <Form.Item name="notes" label="Additional Notes (Optional)">
            <Input.TextArea rows={2} placeholder="Optional notes" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---------------------------------------------------------------------- */}
      {/* WASTAGE MODAL */}
      {/* ---------------------------------------------------------------------- */}
      <Modal
        title={
          <Space>
            <DeleteOutlined style={{ color: '#DC2626' }} />
            <span>Report Scrap / Process Wastage</span>
          </Space>
        }
        open={wasteModalVisible}
        onCancel={() => setWasteModalVisible(false)}
        onOk={handleSubmitWaste}
        confirmLoading={submitting}
        okText="Report Scrap"
        okButtonProps={{ danger: true }}
      >
        <Paragraph type="secondary">
          Logs trimmings, kerf loss, or damaged components. Requires mandatory compliance reason.
        </Paragraph>
        <Alert
          type="error"
          message={`Available Holding: ${selectedMaterial?.remaining_issued_holding} ${selectedMaterial?.unit_of_measure}`}
          style={{ marginBottom: 16 }}
        />
        <Form form={form} layout="vertical">
          {((workOrder?.lot_holdings || []).filter((h) => h.product_id === selectedMaterial?.product_id).length > 0) && (
            <Form.Item
              name="lot_id"
              label="Select Work Order Lot Holding"
              tooltip="Specify which lot balance this scrap is attributed to."
            >
              <Select placeholder="Select holding lot (optional if unallocated)" allowClear>
                {(workOrder?.lot_holdings || [])
                  .filter((h) => h.product_id === selectedMaterial?.product_id)
                  .map((h) => (
                    <Option key={h.lot_id} value={h.lot_id} disabled={h.remaining_holding <= 0}>
                      {h.lot_number || h.lot_id} — Holding: {h.remaining_holding} {h.unit_of_measure}
                    </Option>
                  ))}
              </Select>
            </Form.Item>
          )}
          <Form.Item
            name="quantity"
            label={`Scrap Quantity (${selectedMaterial?.unit_of_measure})`}
            rules={[
              { required: true, message: 'Please enter scrap quantity' },
              {
                type: 'number',
                min: 0.001,
                max: selectedMaterial?.remaining_issued_holding,
                message: `Cannot exceed holding of ${selectedMaterial?.remaining_issued_holding}`,
              },
            ]}
          >
            <InputNumber style={{ width: '100%' }} step={0.1} precision={2} />
          </Form.Item>
          <Form.Item
            name="reason"
            label="Mandatory Reason for Scrap"
            rules={[{ required: true, message: 'Reason is required for scrap logging' }]}
          >
            <Input placeholder="e.g. Contaminated during milling; Trimming residue" />
          </Form.Item>
          <Form.Item name="notes" label="Additional Notes (Optional)">
            <Input.TextArea rows={2} placeholder="Optional details" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---------------------------------------------------------------------- */}
      {/* REQUEST MODAL */}
      {/* ---------------------------------------------------------------------- */}
      <Modal
        title={
          <Space>
            <PlusOutlined style={{ color: '#1E40AF' }} />
            <span>Request Additional Material</span>
          </Space>
        }
        open={requestModalVisible}
        onCancel={() => setRequestModalVisible(false)}
        onOk={handleSubmitRequest}
        confirmLoading={submitting}
        okText="Submit Requisition"
      >
        <Paragraph type="secondary">
          Submits a formal requisition to the store room. The store will inspect and issue stock.
        </Paragraph>
        <Form form={form} layout="vertical">
          {selectedMaterial ? (
            <Alert
              type="info"
              message={`Requisition for: ${selectedMaterial.product_name || selectedMaterial.product_sku}`}
              style={{ marginBottom: 16 }}
            />
          ) : (
            <Form.Item
              name="product_id"
              label="Material SKU or Identifier"
              rules={[{ required: true, message: 'Please enter material SKU' }]}
            >
              <Input placeholder="e.g. RM-STEEL-SHEET" />
            </Form.Item>
          )}

          <Form.Item
            name="quantity"
            label="Requested Quantity"
            rules={[{ required: true, message: 'Please enter quantity' }, { type: 'number', min: 0.01 }]}
          >
            <InputNumber style={{ width: '100%' }} step={1} precision={2} />
          </Form.Item>

          <Form.Item name="unit_of_measure" label="Unit of Measure">
            <Input disabled={!!selectedMaterial} placeholder="e.g. kg, piece, meter" />
          </Form.Item>

          <Form.Item
            name="reason"
            label="Requisition Rationale"
            rules={[{ required: true, message: 'Please specify reason for request' }]}
          >
            <Input placeholder="e.g. High demand line run; replacement for damaged batch" />
          </Form.Item>

          <Form.Item name="notes" label="Shift Notes (Optional)">
            <Input.TextArea rows={2} placeholder="Optional note for storekeeper" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WorkOrderDetail;
