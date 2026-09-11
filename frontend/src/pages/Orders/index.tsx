/**
 * Purchase & Sales Orders Management View.
 *
 * Tracks enterprise supply orders, fulfillment pipelines, and supplier allocations
 * backed by PostgreSQL persistence (/api/v1/orders).
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Form,
  InputNumber,
  message,
  Popconfirm,
  Drawer,
  Flex,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  ShoppingCartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';

import { useApp } from '../../context/AppContext';
import PageHeader from '../../components/common/PageHeader';
import EmptyState from '../../components/common/EmptyState';
import controlTowerApi, { OrderItem, DataProvenance } from '../../services/controlTowerApi';

const { Option } = Select;
const { Text } = Typography;

export const OrdersPage: React.FC = () => {
  const { isDemoMode } = useApp();
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [sourceNote, setSourceNote] = useState<string>('');

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const [drawerVisible, setDrawerVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const res = await controlTowerApi.getOrders({
        status: statusFilter,
        forceDemo: isDemoMode,
      });
      setOrders(res.data);
      setProvenance(res.provenance);
      setSourceNote(res.sourceNote || '');
    } catch {
      message.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, isDemoMode]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleOpenCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      supplier_id: 'sup-001',
      status: 'pending',
      total_amount: 50000.0,
      item_name: 'Raw Silicon Material Batch A',
      quantity: 500,
      unit_price: 100.0,
    });
    setDrawerVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await controlTowerApi.deleteOrder(id);
      message.success('Order deleted');
      fetchOrders();
    } catch {
      message.error('Failed to delete order');
    }
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      const payload = {
        customer_name: values.customer_name,
        supplier_id: values.supplier_id,
        status: values.status,
        total_amount: values.quantity * values.unit_price,
        items: [
          {
            product_id: 'prod-auto-01',
            product_name: values.item_name,
            quantity: values.quantity,
            unit_price: values.unit_price,
          },
        ],
      };
      await controlTowerApi.createOrder(payload);
      message.success('Purchase order created successfully');
      setDrawerVisible(false);
      fetchOrders();
    } catch {
      message.error('Failed to create order');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredOrders = orders.filter((o) => {
    const matchesSearch =
      o.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      o.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      o.supplier_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter ? o.status === statusFilter : true;
    return matchesSearch && matchesStatus;
  });

  const columns = [
    {
      title: 'Order ID',
      dataIndex: 'id',
      key: 'id',
      render: (id: string) => (
        <span style={{ fontWeight: 700, color: '#1E40AF', fontFamily: 'monospace' }}>
          PO-{id.substring(0, 8).toUpperCase()}
        </span>
      ),
    },
    {
      title: 'Client / Entity',
      dataIndex: 'customer_name',
      key: 'customer_name',
      render: (name: string) => <span style={{ fontWeight: 600, color: '#0F172A' }}>{name}</span>,
    },
    {
      title: 'Supplier Ref',
      dataIndex: 'supplier_id',
      key: 'supplier_id',
      render: (sup: string) => <Tag color="blue">{sup}</Tag>,
    },
    {
      title: 'Order Value',
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (amount: number) => (
        <span style={{ fontWeight: 700, color: '#0F172A' }}>
          ${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      ),
      sorter: (a: OrderItem, b: OrderItem) => a.total_amount - b.total_amount,
    },
    {
      title: 'Line Items',
      dataIndex: 'items',
      key: 'items',
      render: (items: any[]) => <span>{items ? items.length : 0} item(s)</span>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'default';
        let icon = <ClockCircleOutlined />;
        if (status === 'delivered') { color = 'success'; icon = <CheckCircleOutlined />; }
        if (status === 'shipped') { color = 'cyan'; }
        if (status === 'confirmed') { color = 'blue'; }
        if (status === 'cancelled') { color = 'red'; icon = <CloseCircleOutlined />; }
        return (
          <Tag color={color} icon={icon} style={{ borderRadius: 4, textTransform: 'capitalize' }}>
            {status}
          </Tag>
        );
      },
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (d: string) => <span style={{ color: '#64748B', fontSize: 12 }}>{new Date(d).toLocaleDateString()}</span>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: OrderItem) => (
        <Popconfirm
          title="Delete order?"
          description="Permanently remove this purchase order."
          onConfirm={() => handleDelete(record.id)}
          okText="Delete"
          okType="danger"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Purchase Orders"
        subtitle="Manage global procurement orders, contract statuses, and line item fulfillment."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Orders' }]}
        provenance={provenance}
        sourceNote={sourceNote}
        onRefresh={fetchOrders}
        refreshing={loading}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
            Create Purchase Order
          </Button>
        }
      />

      <div style={{ padding: '0 24px' }}>
        <Flex gap="middle" style={{ marginBottom: 16 }} wrap="wrap">
          <Input
            placeholder="Search order ID, client, or vendor..."
            prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />

          <Select
            placeholder="Filter Status"
            style={{ width: 150 }}
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
          >
            <Option value="pending">Pending</Option>
            <Option value="confirmed">Confirmed</Option>
            <Option value="shipped">Shipped</Option>
            <Option value="delivered">Delivered</Option>
            <Option value="cancelled">Cancelled</Option>
          </Select>
        </Flex>

        <div style={{ backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
          <Table
            dataSource={filteredOrders}
            columns={columns}
            rowKey="id"
            loading={loading}
            locale={{
              emptyText: <EmptyState title="No Orders Recorded" description="No purchase orders match your criteria. Create a new purchase order to begin." onAction={handleOpenCreate} actionText="Create Purchase Order" />,
            }}
            pagination={{ pageSize: 8, showSizeChanger: true }}
          />
        </div>
      </div>

      <Drawer
        title="Create Purchase Order"
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={420}
        extra={
          <Space>
            <Button onClick={() => setDrawerVisible(false)}>Cancel</Button>
            <Button type="primary" onClick={() => form.submit()} loading={submitting}>
              Issue Order
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="customer_name" label="Client / Purchasing Entity" rules={[{ required: true, message: 'Client name is required' }]}>
            <Input placeholder="e.g. BMW AG Automotive Division" />
          </Form.Item>

          <Form.Item name="supplier_id" label="Vendor Reference" rules={[{ required: true, message: 'Supplier reference required' }]}>
            <Input placeholder="e.g. sup-001 or TSMC Fab 18" />
          </Form.Item>

          <Form.Item name="item_name" label="Material / Product Description" rules={[{ required: true }]}>
            <Input placeholder="e.g. High-Grade Silicon Ingot Batch 4" />
          </Form.Item>

          <Flex gap="middle">
            <Form.Item name="quantity" label="Quantity" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="unit_price" label="Unit Price ($ USD)" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber min={0.1} step={1.0} style={{ width: '100%' }} />
            </Form.Item>
          </Flex>

          <Form.Item name="status" label="Initial Status" rules={[{ required: true }]}>
            <Select>
              <Option value="pending">Pending</Option>
              <Option value="confirmed">Confirmed</Option>
            </Select>
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
};

export default OrdersPage;
