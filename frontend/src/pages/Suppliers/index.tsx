/**
 * Supplier Management Operations View.
 *
 * Full lifecycle vendor catalog backed by PostgreSQL persistence (/api/v1/suppliers).
 * Supports search, multi-tier filtering, performance ratings, and tenant-scoped CRUD.
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
  Rate,
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
  EditOutlined,
  ShopOutlined,
  GlobalOutlined,
} from '@ant-design/icons';

import { useApp } from '../../context/AppContext';
import PageHeader from '../../components/common/PageHeader';
import EmptyState from '../../components/common/EmptyState';
import controlTowerApi, { SupplierItem, DataProvenance } from '../../services/controlTowerApi';

const { Option } = Select;
const { Text } = Typography;

export const SuppliersPage: React.FC = () => {
  const { isDemoMode } = useApp();
  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [sourceNote, setSourceNote] = useState<string>('');

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTier, setSelectedTier] = useState<number | undefined>(undefined);
  const [selectedStatus, setSelectedStatus] = useState<string | undefined>(undefined);

  // Modal / Drawer state
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<SupplierItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchSuppliers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await controlTowerApi.getSuppliers({
        tier: selectedTier,
        forceDemo: isDemoMode,
      });
      setSuppliers(res.data);
      setProvenance(res.provenance);
      setSourceNote(res.sourceNote || '');
    } catch {
      message.error('Failed to load suppliers');
    } finally {
      setLoading(false);
    }
  }, [selectedTier, isDemoMode]);

  useEffect(() => {
    fetchSuppliers();
  }, [fetchSuppliers]);

  const handleOpenCreate = () => {
    setEditingSupplier(null);
    form.resetFields();
    form.setFieldsValue({ tier: 1, rating: 4.5, lead_time_days: 7, status: 'active', is_active: true });
    setDrawerVisible(true);
  };

  const handleOpenEdit = (record: SupplierItem) => {
    setEditingSupplier(record);
    form.setFieldsValue(record);
    setDrawerVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await controlTowerApi.deleteSupplier(id);
      message.success('Supplier removed successfully');
      fetchSuppliers();
    } catch {
      message.error('Failed to delete supplier');
    }
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      if (editingSupplier) {
        await controlTowerApi.updateSupplier(editingSupplier.id, values);
        message.success('Supplier updated successfully');
      } else {
        await controlTowerApi.createSupplier(values);
        message.success('Supplier created successfully');
      }
      setDrawerVisible(false);
      fetchSuppliers();
    } catch {
      message.error('Operation failed. Please check your parameters.');
    } finally {
      setSubmitting(false);
    }
  };

  // Filtered dataset
  const filteredSuppliers = suppliers.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.country.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.contact_email && s.contact_email.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = selectedStatus ? s.status === selectedStatus : true;
    return matchesSearch && matchesStatus;
  });

  const columns = [
    {
      title: 'Vendor Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: SupplierItem) => (
        <div>
          <span style={{ fontWeight: 600, color: '#0F172A', fontSize: 13 }}>{name}</span>
          {record.contact_email && (
            <div style={{ fontSize: 12, color: '#64748B' }}>{record.contact_email}</div>
          )}
        </div>
      ),
    },
    {
      title: 'Echelon Tier',
      dataIndex: 'tier',
      key: 'tier',
      render: (tier: number) => {
        const colors: Record<number, string> = { 1: 'blue', 2: 'cyan', 3: 'purple', 4: 'geekblue' };
        return <Tag color={colors[tier] || 'default'}>Tier {tier}</Tag>;
      },
    },
    {
      title: 'Location',
      dataIndex: 'country',
      key: 'country',
      render: (country: string) => (
        <Space size={4}>
          <GlobalOutlined style={{ color: '#64748B' }} />
          <span>{country}</span>
        </Space>
      ),
    },
    {
      title: 'Lead Time',
      dataIndex: 'lead_time_days',
      key: 'lead_time_days',
      render: (days: number) => <span>{days} days</span>,
      sorter: (a: SupplierItem, b: SupplierItem) => a.lead_time_days - b.lead_time_days,
    },
    {
      title: 'Quality Rating',
      dataIndex: 'rating',
      key: 'rating',
      render: (rating: number) => (
        <Flex align="center" gap={6}>
          <Rate disabled defaultValue={rating} allowHalf count={5} style={{ fontSize: 13 }} />
          <span style={{ fontSize: 12, fontWeight: 600 }}>{rating}</span>
        </Flex>
      ),
      sorter: (a: SupplierItem, b: SupplierItem) => a.rating - b.rating,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'green';
        if (status === 'warning') color = 'orange';
        if (status === 'critical') color = 'red';
        return <Tag color={color} style={{ borderRadius: 4, textTransform: 'capitalize' }}>{status}</Tag>;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: SupplierItem) => (
        <Space size="small">
          <Button type="text" icon={<EditOutlined />} onClick={() => handleOpenEdit(record)} />
          <Popconfirm
            title="Delete supplier?"
            description="This will permanently delete the supplier under your organization."
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            okType="danger"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Supplier Directory"
        subtitle="Manage global vendor ecosystem, multi-tier reliability rankings, lead times, and operational statuses."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Suppliers' }]}
        provenance={provenance}
        sourceNote={sourceNote}
        onRefresh={fetchSuppliers}
        refreshing={loading}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
            Register Supplier
          </Button>
        }
      />

      <div style={{ padding: '0 24px' }}>
        {/* Filters Bar */}
        <Flex gap="middle" style={{ marginBottom: 16 }} wrap="wrap">
          <Input
            placeholder="Search vendor name, country, or email..."
            prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />

          <Select
            placeholder="Filter by Tier"
            style={{ width: 150 }}
            allowClear
            value={selectedTier}
            onChange={setSelectedTier}
          >
            <Option value={1}>Tier 1 (Raw)</Option>
            <Option value={2}>Tier 2 (Parts)</Option>
            <Option value={3}>Tier 3 (Assembly)</Option>
          </Select>

          <Select
            placeholder="Filter by Status"
            style={{ width: 150 }}
            allowClear
            value={selectedStatus}
            onChange={setSelectedStatus}
          >
            <Option value="active">Active</Option>
            <Option value="warning">Warning</Option>
            <Option value="critical">Critical</Option>
          </Select>
        </Flex>

        {/* Suppliers Table */}
        <div style={{ backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
          <Table
            dataSource={filteredSuppliers}
            columns={columns}
            rowKey="id"
            loading={loading}
            locale={{
              emptyText: <EmptyState title="No Suppliers Found" description="Try clearing your search filters or register a new vendor." onAction={handleOpenCreate} actionText="Register Supplier" />,
            }}
            pagination={{ pageSize: 8, showSizeChanger: true }}
          />
        </div>
      </div>

      {/* Drawer for Create / Edit */}
      <Drawer
        title={editingSupplier ? `Edit Supplier: ${editingSupplier.name}` : 'Register New Vendor'}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={420}
        extra={
          <Space>
            <Button onClick={() => setDrawerVisible(false)}>Cancel</Button>
            <Button type="primary" onClick={() => form.submit()} loading={submitting}>
              {editingSupplier ? 'Save Changes' : 'Register'}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Supplier Company Name" rules={[{ required: true, message: 'Vendor name is required' }]}>
            <Input placeholder="e.g. Taiwan Semiconductor Fab 18" />
          </Form.Item>

          <Form.Item name="country" label="Country / Jurisdiction" rules={[{ required: true, message: 'Country is required' }]}>
            <Input placeholder="e.g. Taiwan, Germany, Japan" />
          </Form.Item>

          <Form.Item name="contact_email" label="Contact Email" rules={[{ type: 'email', message: 'Valid email required' }]}>
            <Input placeholder="orders@vendor.com" />
          </Form.Item>

          <Flex gap="middle">
            <Form.Item name="tier" label="Industry Tier" style={{ flex: 1 }} rules={[{ required: true }]}>
              <Select>
                <Option value={1}>Tier 1 (Raw Materials)</Option>
                <Option value={2}>Tier 2 (Sub-Components)</Option>
                <Option value={3}>Tier 3 (Finished Goods)</Option>
              </Select>
            </Form.Item>

            <Form.Item name="lead_time_days" label="Lead Time (Days)" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber min={1} max={365} style={{ width: '100%' }} />
            </Form.Item>
          </Flex>

          <Flex gap="middle">
            <Form.Item name="status" label="Operational Status" style={{ flex: 1 }} rules={[{ required: true }]}>
              <Select>
                <Option value="active">Active</Option>
                <Option value="warning">Warning</Option>
                <Option value="critical">Critical</Option>
              </Select>
            </Form.Item>

            <Form.Item name="rating" label="Performance Rating" style={{ flex: 1 }}>
              <InputNumber min={1.0} max={5.0} step={0.1} style={{ width: '100%' }} />
            </Form.Item>
          </Flex>
        </Form>
      </Drawer>
    </div>
  );
};

export default SuppliersPage;
