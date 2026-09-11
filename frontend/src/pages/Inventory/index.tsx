/**
 * Inventory Management Operations View.
 *
 * Operational SKU inventory and warehouse balances backed by PostgreSQL (/api/v1/inventory).
 * Features stockout risk detection, warehouse distribution, and restock actions.
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
  Popconfirm,
  Drawer,
  Flex,
  Typography,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  AppstoreOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

import { useApp } from '../../context/AppContext';
import PageHeader from '../../components/common/PageHeader';
import EmptyState from '../../components/common/EmptyState';
import controlTowerApi, { InventoryItem, DataProvenance } from '../../services/controlTowerApi';

const { Option } = Select;
const { Text } = Typography;

export const InventoryPage: React.FC = () => {
  const { isDemoMode } = useApp();
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<DataProvenance>('LIVE');
  const [sourceNote, setSourceNote] = useState<string>('');

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [warehouseFilter, setWarehouseFilter] = useState<string | undefined>(undefined);
  const [lowStockOnly, setLowStockOnly] = useState<boolean>(false);

  // Modal / Drawer state
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

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

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);

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

  const handleDelete = async (id: string) => {
    try {
      await controlTowerApi.deleteInventory(id);
      message.success('Inventory item removed');
      fetchInventory();
    } catch {
      message.error('Failed to delete item');
    }
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

  // Filtered dataset
  const filteredItems = inventory.filter((item) => {
    const matchesSearch =
      item.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.name.toLowerCase().includes(searchTerm.toLowerCase());
    const isLow = item.quantity_on_hand <= item.reorder_point || item.is_low_stock;
    const matchesLowStock = lowStockOnly ? isLow : true;
    return matchesSearch && matchesLowStock;
  });

  const columns = [
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
        const ratio = record.reorder_point > 0 ? (record.quantity_on_hand / (record.reorder_point * 2)) * 100 : 100;
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
          <div style={{ width: 140 }}>
            <Flex justify="space-between" style={{ marginBottom: 2 }}>
              <Tag color={tagColor} style={{ fontSize: 10, margin: 0, padding: '0 4px', lineHeight: '16px' }}>
                {statusText}
              </Tag>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#334155' }}>
                {record.quantity_on_hand.toLocaleString()}
              </span>
            </Flex>
            <Progress
              percent={Math.min(100, Math.round(ratio))}
              size="small"
              strokeColor={color}
              showInfo={false}
            />
          </div>
        );
      },
    },
    {
      title: 'Reserved',
      dataIndex: 'quantity_reserved',
      key: 'quantity_reserved',
      render: (qty: number) => <span>{qty.toLocaleString()}</span>,
    },
    {
      title: 'Reorder Point',
      dataIndex: 'reorder_point',
      key: 'reorder_point',
      render: (pt: number) => <span style={{ color: '#64748B' }}>{pt.toLocaleString()}</span>,
    },
    {
      title: 'Unit Cost',
      dataIndex: 'unit_cost',
      key: 'unit_cost',
      render: (cost: number) => <span>${cost.toFixed(2)}</span>,
      sorter: (a: InventoryItem, b: InventoryItem) => a.unit_cost - b.unit_cost,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: InventoryItem) => (
        <Popconfirm
          title="Delete inventory SKU?"
          description="Removes item from current organization warehouse balance."
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
        title="Inventory Balances"
        subtitle="Monitor multi-facility stock levels, reserved quantities, reorder thresholds, and stockout risks."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Inventory' }]}
        provenance={provenance}
        sourceNote={sourceNote}
        onRefresh={fetchInventory}
        refreshing={loading}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
            Restock / Add SKU
          </Button>
        }
      />

      <div style={{ padding: '0 24px' }}>
        {/* Filter Controls */}
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

        {/* Inventory Data Table */}
        <div style={{ backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
          <Table
            dataSource={filteredItems}
            columns={columns}
            rowKey="id"
            loading={loading}
            locale={{
              emptyText: <EmptyState title="No Inventory Records" description="No inventory items found. Add items to stock catalog." onAction={handleOpenCreate} actionText="Add Stock SKU" />,
            }}
            pagination={{ pageSize: 8, showSizeChanger: true }}
          />
        </div>
      </div>

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
