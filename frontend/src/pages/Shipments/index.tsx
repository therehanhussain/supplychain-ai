/**
 * Logistics & Shipments Control View.
 *
 * Real-time freight tracking, carrier dispatches, and route telemetry
 * backed by PostgreSQL persistence (/api/v1/shipments).
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
  message,
  Popconfirm,
  Drawer,
  Flex,
  Typography,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  CarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SendOutlined,
} from '@ant-design/icons';

import { useApp } from '../../context/AppContext';
import PageHeader from '../../components/common/PageHeader';
import EmptyState from '../../components/common/EmptyState';
import controlTowerApi, { ShipmentItem, DataProvenance } from '../../services/controlTowerApi';

const { Option } = Select;
const { Text } = Typography;

export const ShipmentsPage: React.FC = () => {
  const { isDemoMode } = useApp();
  const [shipments, setShipments] = useState<ShipmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [sourceNote, setSourceNote] = useState<string>('');

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const [drawerVisible, setDrawerVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchShipments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await controlTowerApi.getShipments({
        status: statusFilter,
        forceDemo: isDemoMode,
      });
      setShipments(res.data);
      setProvenance(res.provenance);
      setSourceNote(res.sourceNote || '');
    } catch {
      message.error('Failed to load shipments');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, isDemoMode]);

  useEffect(() => {
    fetchShipments();
  }, [fetchShipments]);

  const handleOpenCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      order_id: 'ord-901',
      carrier: 'DHL Global Forwarding',
      tracking_number: `DHL-${Math.floor(100000 + Math.random() * 900000)}`,
      origin: 'Rotterdam Port Facility, Netherlands',
      destination: 'Munich Technology Logistics Hub, Germany',
      status: 'in_transit',
    });
    setDrawerVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await controlTowerApi.deleteShipment(id);
      message.success('Shipment dispatch record deleted');
      fetchShipments();
    } catch {
      message.error('Failed to delete shipment');
    }
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      await controlTowerApi.createShipment(values);
      message.success('Shipment dispatched successfully');
      setDrawerVisible(false);
      fetchShipments();
    } catch {
      message.error('Failed to create shipment dispatch');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredShipments = shipments.filter((s) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      (s.tracking_number && s.tracking_number.toLowerCase().includes(term)) ||
      s.carrier.toLowerCase().includes(term) ||
      s.origin.toLowerCase().includes(term) ||
      s.destination.toLowerCase().includes(term);
    const matchesStatus = statusFilter ? s.status === statusFilter : true;
    return matchesSearch && matchesStatus;
  });

  const columns = [
    {
      title: 'Tracking #',
      dataIndex: 'tracking_number',
      key: 'tracking_number',
      render: (tracking: string, record: ShipmentItem) => (
        <span style={{ fontWeight: 700, color: '#1E40AF', fontFamily: 'monospace' }}>
          {tracking || `SHP-${record.id.substring(0, 8).toUpperCase()}`}
        </span>
      ),
    },
    {
      title: 'Carrier Partner',
      dataIndex: 'carrier',
      key: 'carrier',
      render: (carrier: string) => (
        <Space size={6}>
          <CarOutlined style={{ color: '#64748B' }} />
          <span style={{ fontWeight: 600, color: '#0F172A' }}>{carrier}</span>
        </Space>
      ),
    },
    {
      title: 'Route',
      key: 'route',
      render: (_: any, record: ShipmentItem) => {
        const origShort = record.origin.split(',')[0].split('(')[0].trim();
        const destShort = record.destination.split(',')[0].split('(')[0].trim();
        return (
          <Tooltip title={`${record.origin} → ${record.destination}`}>
            <span style={{ fontWeight: 500, fontSize: 13, color: '#0F172A', whiteSpace: 'nowrap' }}>
              {origShort} <span style={{ color: '#94A3B8' }}>→</span> {destShort}
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'default';
        let icon = <ClockCircleOutlined />;
        if (status === 'delivered') { color = 'success'; icon = <CheckCircleOutlined />; }
        if (status === 'in_transit') { color = 'processing'; icon = <SendOutlined />; }
        if (status === 'preparing') { color = 'warning'; }
        return (
          <Tag color={color} icon={icon} style={{ borderRadius: 4, textTransform: 'capitalize' }}>
            {status.replace('_', ' ')}
          </Tag>
        );
      },
    },
    {
      title: 'Dispatch Date',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (d: string) => <span style={{ color: '#64748B', fontSize: 12 }}>{new Date(d).toLocaleDateString()}</span>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: ShipmentItem) => (
        <Popconfirm
          title="Delete shipment record?"
          description="Permanently delete this logistics dispatch."
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
        title="Logistics & Shipments"
        subtitle="End-to-end freight monitoring, route tracking, carrier transit milestones, and delivery ETAs."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Shipments' }]}
        provenance={provenance}
        sourceNote={sourceNote}
        onRefresh={fetchShipments}
        refreshing={loading}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
            Dispatch Freight
          </Button>
        }
      />

      <div style={{ padding: '0 24px' }}>
        <Flex gap="middle" style={{ marginBottom: 16 }} wrap="wrap">
          <Input
            placeholder="Search tracking #, carrier, origin, or destination..."
            prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: 340 }}
            allowClear
          />

          <Select
            placeholder="Filter Status"
            style={{ width: 160 }}
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
          >
            <Option value="preparing">Preparing</Option>
            <Option value="in_transit">In Transit</Option>
            <Option value="out_for_delivery">Out for Delivery</Option>
            <Option value="delivered">Delivered</Option>
          </Select>
        </Flex>

        <div style={{ backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
          <Table
            dataSource={filteredShipments}
            columns={columns}
            rowKey="id"
            loading={loading}
            locale={{
              emptyText: <EmptyState title="No Shipments Tracked" description="No active freight dispatches found matching filters." onAction={handleOpenCreate} actionText="Dispatch Freight" />,
            }}
            pagination={{ pageSize: 8, showSizeChanger: true }}
          />
        </div>
      </div>

      <Drawer
        title="Dispatch New Shipment"
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={420}
        extra={
          <Space>
            <Button onClick={() => setDrawerVisible(false)}>Cancel</Button>
            <Button type="primary" onClick={() => form.submit()} loading={submitting}>
              Confirm Dispatch
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="order_id" label="Linked Purchase Order ID" rules={[{ required: true }]}>
            <Input placeholder="e.g. ord-901 or PO-001" />
          </Form.Item>

          <Form.Item name="carrier" label="Carrier Partner" rules={[{ required: true }]}>
            <Input placeholder="e.g. DHL Global Forwarding, Maersk, FedEx" />
          </Form.Item>

          <Form.Item name="tracking_number" label="Carrier Tracking Identifier">
            <Input placeholder="e.g. DHL-984712" />
          </Form.Item>

          <Form.Item name="origin" label="Origin Facility / Port" rules={[{ required: true }]}>
            <Input placeholder="e.g. Rotterdam Port Terminal" />
          </Form.Item>

          <Form.Item name="destination" label="Destination Distribution Center" rules={[{ required: true }]}>
            <Input placeholder="e.g. Munich Logistics Hub" />
          </Form.Item>

          <Form.Item name="status" label="Initial Status" rules={[{ required: true }]}>
            <Select>
              <Option value="preparing">Preparing</Option>
              <Option value="in_transit">In Transit</Option>
            </Select>
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
};

export default ShipmentsPage;
