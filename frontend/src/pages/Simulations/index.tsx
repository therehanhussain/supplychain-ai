/**
 * AI Multi-Agent Simulation Orchestrator View.
 *
 * Dispatches and monitors asynchronous multi-firm economic simulations.
 * Real-time polling across QUEUED, RUNNING, COMPLETED, and CANCELLED states.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Row,
  Col,
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Tag,
  Progress,
  Typography,
  Flex,
  Alert,
  Space,
  Statistic,
  Divider,
  message,
} from 'antd';
import {
  ThunderboltOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import PageHeader from '../../components/common/PageHeader';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import controlTowerApi, { SimulationTask } from '../../services/controlTowerApi';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

export const SimulationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [runningTask, setRunningTask] = useState<SimulationTask | null>(null);
  const [launching, setLaunching] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [form] = Form.useForm();
  const pollingRef = useRef<any>(null);

  // Poll active task status
  useEffect(() => {
    if (!runningTask || runningTask.status === 'COMPLETED' || runningTask.status === 'CANCELLED' || runningTask.status === 'FAILED') {
      if (pollingRef.current) clearInterval(pollingRef.current);
      return;
    }

    pollingRef.current = setInterval(async () => {
      try {
        const updated = await controlTowerApi.getSimulationStatus(runningTask.experiment_id);
        setRunningTask(updated);
        if (updated.status === 'COMPLETED' || updated.status === 'CANCELLED' || updated.status === 'FAILED') {
          clearInterval(pollingRef.current);
        }
      } catch {
        // Ignore transient poll error
      }
    }, 1500);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [runningTask]);

  const handleLaunchSimulation = async (values: any) => {
    setLaunching(true);
    try {
      const res = await controlTowerApi.dispatchSimulation({
        name: values.name || 'Enterprise Disruption Simulation',
        num_days: values.num_days || 4,
        num_firms: values.num_firms || 16,
      });

      message.success(`Simulation dispatched (Task ${res.task_id})`);

      // Set initial tracking state
      setRunningTask({
        task_id: res.task_id,
        experiment_id: res.experiment_id,
        name: values.name || 'Supply Chain Simulation Run',
        status: 'QUEUED',
        num_days: values.num_days || 4,
        current_day: 0,
        progress_pct: 0,
        num_firms: values.num_firms || 16,
        created_at: new Date().toISOString(),
        input_tokens: 0,
        output_tokens: 0,
        is_mock: true,
      });
    } catch {
      message.error('Failed to dispatch simulation to worker');
    } finally {
      setLaunching(false);
    }
  };

  const handleCancelSimulation = async () => {
    if (!runningTask) return;
    setCancelling(true);
    try {
      await controlTowerApi.cancelSimulation(runningTask.experiment_id);
      message.warning('Simulation execution cancelled');
      setRunningTask({ ...runningTask, status: 'CANCELLED' });
    } catch {
      message.error('Failed to cancel simulation');
    } finally {
      setCancelling(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'QUEUED':
        return <Tag color="gold" icon={<ClockCircleOutlined />}>QUEUED</Tag>;
      case 'RUNNING':
        return <Tag color="processing" icon={<ReloadOutlined spin />}>RUNNING</Tag>;
      case 'COMPLETED':
        return <Tag color="success" icon={<CheckCircleOutlined />}>COMPLETED</Tag>;
      case 'CANCELLED':
        return <Tag color="default" icon={<StopOutlined />}>CANCELLED</Tag>;
      default:
        return <Tag color="red">FAILED</Tag>;
    }
  };

  return (
    <div>
      <PageHeader
        title="Multi-Agent Simulation Engine"
        subtitle="Orchestrate Ray-based macroeconomic simulations across autonomous supplier and firm agents."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'AI Simulations' }]}
        provenance="SIMULATED"
        sourceNote="AgentSociety / Ray economic model. Results represent simulated scenarios, not guaranteed outcomes."
      />

      <div style={{ padding: '0 24px' }}>
        <Alert
          type="info"
          showIcon
          message="Multi-Agent Simulation Scope"
          description="Autonomous enterprise agents model supplier procurement, pricing dynamics, and production decisions under macroeconomic conditions. Dispatching enqueues background worker execution."
          style={{ marginBottom: 20 }}
        />

        <Row gutter={[20, 20]}>
          {/* Dispatch Configuration Form */}
          <Col xs={24} lg={10}>
            <Card
              title={
                <Flex align="center" gap={8}>
                  <ThunderboltOutlined style={{ color: '#1E40AF' }} />
                  <span>Configure New Simulation Experiment</span>
                </Flex>
              }
              style={{ borderRadius: 8, border: '1px solid #E2E8F0' }}
            >
              <Form
                form={form}
                layout="vertical"
                onFinish={handleLaunchSimulation}
                initialValues={{
                  name: 'Macro Disruption Stress Test',
                  disruption_type: 'PORT_CONGESTION',
                  num_days: 4,
                  num_firms: 16,
                  severity: 'HIGH',
                }}
              >
                <Form.Item name="name" label="Experiment Run Title" rules={[{ required: true }]}>
                  <Input placeholder="e.g. Semiconductor Bottleneck Stress Test" />
                </Form.Item>

                <Form.Item name="disruption_type" label="Primary Shock Scenario">
                  <Select>
                    <Option value="PORT_CONGESTION">Global Maritime Port Congestion (+7 Days Lead Time)</Option>
                    <Option value="RAW_MATERIAL_EMBARGO">Raw Silicon Export Quota Outage</Option>
                    <Option value="ENERGY_SPIKE">Regional Grid Energy Curtailment (+30% Cost)</Option>
                    <Option value="BASELINE_STABLE">Baseline Equilibrium (Zero Disruption)</Option>
                  </Select>
                </Form.Item>

                <Flex gap="middle">
                  <Form.Item name="num_days" label="Simulation Days" style={{ flex: 1 }} rules={[{ required: true }]}>
                    <InputNumber min={1} max={30} style={{ width: '100%' }} />
                  </Form.Item>

                  <Form.Item name="num_firms" label="Active Firm Agents" style={{ flex: 1 }} rules={[{ required: true }]}>
                    <InputNumber min={4} max={64} style={{ width: '100%' }} />
                  </Form.Item>
                </Flex>

                <Form.Item name="severity" label="Stress Severity">
                  <Select>
                    <Option value="LOW">Low (Mild variance)</Option>
                    <Option value="MODERATE">Moderate (Partial supply friction)</Option>
                    <Option value="HIGH">High (Severe production bottleneck)</Option>
                  </Select>
                </Form.Item>

                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  block
                  icon={<PlayCircleOutlined />}
                  loading={launching}
                  disabled={runningTask?.status === 'RUNNING' || runningTask?.status === 'QUEUED'}
                >
                  Dispatch Asynchronous Simulation
                </Button>
              </Form>
            </Card>
          </Col>

          {/* Active Simulation Monitor */}
          <Col xs={24} lg={14}>
            <Card
              title={
                <Flex justify="space-between" align="center">
                  <span>Simulation Telemetry & Execution State</span>
                  {runningTask && getStatusBadge(runningTask.status)}
                </Flex>
              }
              style={{ borderRadius: 8, border: '1px solid #E2E8F0', height: '100%' }}
            >
              {!runningTask ? (
                <div style={{ padding: '60px 20px', textAlign: 'center' }}>
                  <ThunderboltOutlined style={{ fontSize: 44, color: '#94A3B8', marginBottom: 12 }} />
                  <div style={{ fontWeight: 600, fontSize: 16, color: '#334155' }}>
                    No Active Simulation Enqueued
                  </div>
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    Configure parameters on the left and click "Dispatch Asynchronous Simulation" to initiate worker execution.
                  </Text>
                </div>
              ) : (
                <div>
                  <Flex justify="space-between" align="flex-start">
                    <div>
                      <Title level={4} style={{ margin: 0, color: '#0F172A' }}>
                        {runningTask.name}
                      </Title>
                      <Text type="secondary" style={{ fontSize: 12, fontFamily: 'monospace' }}>
                        EXP: {runningTask.experiment_id} | TASK: {runningTask.task_id}
                      </Text>
                    </div>

                    {runningTask.status === 'RUNNING' && (
                      <Button
                        danger
                        icon={<StopOutlined />}
                        onClick={handleCancelSimulation}
                        loading={cancelling}
                      >
                        Cancel Run
                      </Button>
                    )}
                  </Flex>

                  <div style={{ marginTop: 24 }}>
                    <Flex justify="space-between" style={{ marginBottom: 6 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>Simulation Round Progression:</span>
                      <span style={{ fontWeight: 700, color: '#1E40AF' }}>
                        Day {runningTask.current_day} of {runningTask.num_days} ({runningTask.progress_pct}%)
                      </span>
                    </Flex>
                    <Progress
                      percent={runningTask.progress_pct}
                      status={runningTask.status === 'RUNNING' ? 'active' : (runningTask.status === 'CANCELLED' ? 'exception' : 'normal')}
                      strokeColor={runningTask.status === 'CANCELLED' ? '#DC2626' : '#1E40AF'}
                    />
                  </div>

                  <Divider style={{ margin: '20px 0' }} />

                  <Row gutter={[16, 16]}>
                    <Col span={8}>
                      <Statistic
                        title="Simulated Firm Agents"
                        value={runningTask.num_firms}
                        valueStyle={{ fontSize: 20, fontWeight: 700 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="AI Tokens Consumed"
                        value={(runningTask.input_tokens + runningTask.output_tokens).toLocaleString()}
                        valueStyle={{ fontSize: 20, fontWeight: 700 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="Started At"
                        value={new Date(runningTask.created_at).toLocaleTimeString()}
                        valueStyle={{ fontSize: 20, fontWeight: 700 }}
                      />
                    </Col>
                  </Row>

                  {/* Actions on completion */}
                  {runningTask.status === 'COMPLETED' && (
                    <div style={{ marginTop: 28, padding: 16, backgroundColor: '#F0FDF4', borderRadius: 6, border: '1px solid #BBF7D0' }}>
                      <Flex justify="space-between" align="center">
                        <div>
                          <div style={{ fontWeight: 700, color: '#166534', fontSize: 14 }}>
                            Simulation Completed Successfully
                          </div>
                          <div style={{ fontSize: 12, color: '#15803D' }}>
                            Full step trajectory and agent reflections are ready for inspection in the replay player.
                          </div>
                        </div>

                        <Button
                          type="primary"
                          icon={<EyeOutlined />}
                          onClick={() => navigate(`/exp/${runningTask.experiment_id}`)}
                          style={{ backgroundColor: '#059669', borderColor: '#059669' }}
                        >
                          Open in Spatial Replay Player
                        </Button>
                      </Flex>
                    </div>
                  )}

                  {runningTask.status === 'CANCELLED' && (
                    <Alert
                      type="warning"
                      showIcon
                      message="Simulation Aborted"
                      description="The simulation execution was cancelled by operator request. Background workers cleanly terminated remaining rounds."
                      style={{ marginTop: 24 }}
                    />
                  )}
                </div>
              )}
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default SimulationsPage;
