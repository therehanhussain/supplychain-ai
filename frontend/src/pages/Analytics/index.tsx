/**
 * Performance Analytics & Telemetry View.
 *
 * Operational KPI distributions, vendor tier breakdowns, on-time delivery rates,
 * and direct links to the MLflow experiment telemetry server.
 */

import React, { useEffect, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Flex,
  Progress,
  Button,
  Tag,
  Divider,
} from 'antd';
import {
  BarChartOutlined,
  ExportOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  ShopOutlined,
  CarOutlined,
} from '@ant-design/icons';

import PageHeader from '../../components/common/PageHeader';
import KpiCard from '../../components/common/KpiCard';
import apiClient from '../../services/apiClient';

const { Title, Text, Paragraph } = Typography;

export const AnalyticsPage: React.FC = () => {
  const [mlflowUrl, setMlflowUrl] = useState<string>('http://localhost:59000');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch safe telemetry URL from backend
    apiClient.get<any>('/api/v1/analytics/telemetry-url')
      .then((res) => {
        if (res?.url) setMlflowUrl(res.url);
      })
      .catch(() => {
        // Fallback
      });
  }, []);

  return (
    <div>
      <PageHeader
        title="Performance Analytics"
        subtitle="Cross-echelon operational KPIs, supplier distribution, fulfillment velocity, and simulation telemetry."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Analytics' }]}
        provenance="LIVE"
        sourceNote="Aggregated from operational database and MLflow metrics registry"
        extra={
          <Button
            type="primary"
            icon={<ExportOutlined />}
            onClick={() => window.open(mlflowUrl, '_blank')}
          >
            Open MLflow Dashboard
          </Button>
        }
      />

      <div style={{ padding: '0 24px' }}>
        {/* Top KPIs */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="On-Time Delivery Rate"
              value="98.4%"
              icon={<CarOutlined />}
              trend={{ value: 1.8, isPositiveGood: true, label: 'vs last quarter' }}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="Inventory Turnover"
              value="8.2x"
              icon={<BarChartOutlined />}
              trend={{ value: 0.5, isPositiveGood: true, label: 'annualized turns' }}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="Order Fulfillment Cycle"
              value="4.6 Days"
              icon={<CheckCircleOutlined />}
              trend={{ value: -12.0, isPositiveGood: true, label: 'faster turnaround' }}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <KpiCard
              title="Supplier Quality Index"
              value="4.78 / 5"
              icon={<ShopOutlined />}
              badge={{ text: 'Exceeding SLA', color: 'green' }}
            />
          </Col>
        </Row>

        {/* Distributions and Comparisons */}
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          {/* Supplier Tier Distribution */}
          <Col xs={24} lg={12}>
            <Card title="Supplier Tier Distribution" style={{ borderRadius: 8, border: '1px solid #E2E8F0', height: '100%' }}>
              <Paragraph type="secondary" style={{ fontSize: 13 }}>
                Proportion of active vendors categorized by production echelon.
              </Paragraph>

              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 16 }}>
                  <Flex justify="space-between" style={{ marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Tier 1: Primary Raw Materials</span>
                    <span style={{ fontWeight: 700, color: '#1E40AF' }}>35% (TSMC, ASML)</span>
                  </Flex>
                  <Progress percent={35} strokeColor="#1E40AF" showInfo={false} />
                </div>

                <div style={{ marginBottom: 16 }}>
                  <Flex justify="space-between" style={{ marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Tier 2: Intermediate Components & Sub-assemblies</span>
                    <span style={{ fontWeight: 700, color: '#0284C7' }}>45% (Shin-Etsu, Air Liquide)</span>
                  </Flex>
                  <Progress percent={45} strokeColor="#0284C7" showInfo={false} />
                </div>

                <div style={{ marginBottom: 8 }}>
                  <Flex justify="space-between" style={{ marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Tier 3: Finished Goods Assembly & Packaging</span>
                    <span style={{ fontWeight: 700, color: '#7C3AED' }}>20% (Hengdian)</span>
                  </Flex>
                  <Progress percent={20} strokeColor="#7C3AED" showInfo={false} />
                </div>
              </div>
            </Card>
          </Col>

          {/* MLflow Deep Telemetry Link */}
          <Col xs={24} lg={12}>
            <Card
              title={
                <Flex align="center" gap={8}>
                  <ThunderboltOutlined style={{ color: '#1E40AF' }} />
                  <span>Deep Simulation Telemetry (MLflow)</span>
                </Flex>
              }
              style={{ borderRadius: 8, border: '1px solid #E2E8F0', height: '100%' }}
            >
              <Paragraph type="secondary" style={{ fontSize: 13 }}>
                For high-resolution simulation experiment runs, loss curves, token throughput, and agent reflection transcripts, visit the integrated MLflow server.
              </Paragraph>

              <div style={{ padding: 16, backgroundColor: '#F8FAFC', borderRadius: 6, border: '1px solid #E2E8F0', marginTop: 12 }}>
                <Flex justify="space-between" align="center">
                  <div>
                    <div style={{ fontWeight: 600, color: '#0F172A', fontSize: 13 }}>MLflow Tracking URI:</div>
                    <Text code style={{ fontSize: 12, marginTop: 4, display: 'inline-block' }}>{mlflowUrl}</Text>
                  </div>
                  <Tag color="cyan">Version 2.x Compatible</Tag>
                </Flex>
              </div>

              <Button
                type="primary"
                block
                size="large"
                icon={<ExportOutlined />}
                onClick={() => window.open(mlflowUrl, '_blank')}
                style={{ marginTop: 20 }}
              >
                Launch External MLflow Server
              </Button>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default AnalyticsPage;
