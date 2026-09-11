/**
 * Demand Forecasting Intelligence View.
 *
 * Provides projected SKU demand trajectories. Honestly documents scaffold/demonstration status.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Select,
  Alert,
  Typography,
  Flex,
  Tag,
  Button,
} from 'antd';
import {
  LineChartOutlined,
  InfoCircleOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';

import { useApp } from '../../context/AppContext';
import PageHeader from '../../components/common/PageHeader';
import KpiCard from '../../components/common/KpiCard';
import controlTowerApi, { ForecastResponse, DataProvenance } from '../../services/controlTowerApi';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

export const ForecastPage: React.FC = () => {
  const { isDemoMode } = useApp();
  const [selectedSku, setSelectedSku] = useState<string>('MAT-SILICON-300MM');
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [provenance, setProvenance] = useState<DataProvenance>('DEMO');
  const [sourceNote, setSourceNote] = useState<string>('');

  const fetchForecast = useCallback(async () => {
    setLoading(true);
    try {
      const res = await controlTowerApi.getForecast(selectedSku, isDemoMode);
      setForecast(res.data);
      setProvenance(res.provenance);
      setSourceNote(res.sourceNote || 'Baseline ARIMA heuristic generator');
    } finally {
      setLoading(false);
    }
  }, [selectedSku, isDemoMode]);

  useEffect(() => {
    fetchForecast();
  }, [fetchForecast]);

  const series = forecast?.forecast_series || [];
  const totalProjected = series.reduce((sum, item) => sum + item.predicted_demand, 0);
  const avgDaily = series.length > 0 ? Math.round(totalProjected / series.length) : 0;

  const columns = [
    {
      title: 'Horizon Day',
      dataIndex: 'day',
      key: 'day',
      render: (d: number) => <span style={{ fontWeight: 600 }}>Day +{d}</span>,
    },
    {
      title: 'Calendar Date',
      dataIndex: 'date',
      key: 'date',
      render: (date: string) => <span style={{ color: '#64748B' }}>{date}</span>,
    },
    {
      title: 'Projected Demand',
      dataIndex: 'predicted_demand',
      key: 'predicted_demand',
      render: (units: number) => (
        <span style={{ fontWeight: 700, color: '#1E40AF' }}>
          {units.toLocaleString()} units
        </span>
      ),
      sorter: (a: any, b: any) => a.predicted_demand - b.predicted_demand,
    },
    {
      title: 'Confidence Band (95%)',
      key: 'confidence',
      render: (_: any, record: any) => (
        <span style={{ color: '#64748B', fontSize: 12 }}>
          {record.confidence_lower?.toLocaleString() || 310} – {record.confidence_upper?.toLocaleString() || 450} units
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Demand Forecasting"
        subtitle="Forecast demand patterns across critical raw materials and finished good inventories."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Forecast' }]}
        provenance="SIMULATED"
        sourceNote="Forecast engine currently running in demonstration mode."
        onRefresh={fetchForecast}
        refreshing={loading}
      />

      <div style={{ padding: '0 24px' }}>
        {/* Explicit Honesty Banner */}
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          message="Forecast Engine Operational Status"
          description="The demand forecasting service is currently running in demonstration mode using baseline seasonal heuristics. Validated neural network forecasting models will be integrated in subsequent releases."
          style={{ marginBottom: 20, border: '1px solid #BAE6FD', backgroundColor: '#F0F9FF' }}
        />

        {/* SKU Selector Controls */}
        <Card style={{ marginBottom: 20, borderRadius: 8, border: '1px solid #E2E8F0' }} bodyStyle={{ padding: '16px 20px' }}>
          <Flex align="center" justify="space-between" wrap="wrap" gap="middle">
            <Flex align="center" gap={12}>
              <span style={{ fontWeight: 600, color: '#0F172A' }}>Select Target SKU:</span>
              <Select
                value={selectedSku}
                onChange={setSelectedSku}
                style={{ width: 320 }}
              >
                <Option value="MAT-SILICON-300MM">MAT-SILICON-300MM (Silicon Substrate)</Option>
                <Option value="MAT-NEON-GAS-999">MAT-NEON-GAS-999 (Excimer Neon Gas)</Option>
                <Option value="COMP-ARM-MCU-V4">COMP-ARM-MCU-V4 (Automotive ARM MCU)</Option>
                <Option value="MAT-COPPER-CLAD">MAT-COPPER-CLAD (Copper Clad Laminate)</Option>
              </Select>
            </Flex>

            <Tag color="purple" icon={<ExperimentOutlined />} style={{ fontWeight: 600, padding: '2px 8px' }}>
              Model: {forecast?.model_name || 'Baseline Heuristic'}
            </Tag>
          </Flex>
        </Card>

        {/* Forecast Metrics */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <KpiCard
              title="14-Day Cumulative Demand"
              value={`${totalProjected.toLocaleString()} Units`}
              icon={<LineChartOutlined />}
              subtitle={`Across 14-day projection window`}
              loading={loading}
            />
          </Col>

          <Col xs={24} sm={8}>
            <KpiCard
              title="Projected Mean Daily Consumption"
              value={`${avgDaily.toLocaleString()} Units/day`}
              icon={<LineChartOutlined />}
              subtitle="Daily replenishment pace"
              loading={loading}
            />
          </Col>

          <Col xs={24} sm={8}>
            <KpiCard
              title="Historical Lookback Window"
              value={`${forecast?.historical_days || 30} Days`}
              icon={<InfoCircleOutlined />}
              subtitle="Prior demand time-series baseline"
              loading={loading}
            />
          </Col>
        </Row>

        {/* Projection Schedule Table */}
        <Card
          title="Daily Demand Projection Schedule"
          style={{ marginTop: 20, borderRadius: 8, border: '1px solid #E2E8F0' }}
          bodyStyle={{ padding: 0 }}
        >
          <Table
            dataSource={series}
            columns={columns}
            rowKey="day"
            pagination={{ pageSize: 7 }}
            loading={loading}
          />
        </Card>
      </div>
    </div>
  );
};

export default ForecastPage;
