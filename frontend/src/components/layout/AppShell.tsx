/**
 * Enterprise Global App Shell for Supply Chain Control Tower.
 *
 * Implements a balanced collapsible sidebar, responsive top navigation header
 * with organization context, unified compact System Status popover, Demo Mode switch,
 * and responsive mobile drawer.
 */

import React, { useState, useEffect } from 'react';
import {
  Layout,
  Menu,
  Flex,
  Typography,
  Space,
  Switch,
  Dropdown,
  Avatar,
  Button,
  Drawer,
  Tooltip,
  Tag,
  Popover,
  Divider,
  type MenuProps,
} from 'antd';
import {
  DashboardOutlined,
  NodeIndexOutlined,
  ShopOutlined,
  AppstoreOutlined,
  ShoppingCartOutlined,
  CarOutlined,
  AlertOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  ExperimentOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  BankOutlined,
  LogoutOutlined,
  LoginOutlined,
  SettingOutlined,
  ToolOutlined,
  FileTextOutlined,
  HistoryOutlined,
  CheckCircleFilled,
  ExclamationCircleFilled,
  CloseCircleFilled,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import AuthModal from '../common/AuthModal';
import { getAppEnvironment } from '../../utils/env';

const { Header, Sider, Content } = Layout;

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    user,
    organization,
    isDemoMode,
    setDemoMode,
    systemStatus,
    setAuthModalVisible,
    logout,
  } = useApp();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setWindowWidth(width);
      if (width < 992) setCollapsed(true);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isMobile = windowWidth < 768;
  const isTablet = windowWidth >= 768 && windowWidth < 1024;

  // Menu items structured according to specifications
  const menuItems: MenuProps['items'] = [
    {
      type: 'group',
      label: (
        <span style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>
          CONTROL TOWER
        </span>
      ),
      children: [
        {
          key: '/',
          icon: <DashboardOutlined style={{ fontSize: 15 }} />,
          label: 'Overview',
        },
        {
          key: '/network',
          icon: <NodeIndexOutlined style={{ fontSize: 15 }} />,
          label: 'Network',
        },
        {
          key: '/suppliers',
          icon: <ShopOutlined style={{ fontSize: 15 }} />,
          label: 'Suppliers',
        },
        {
          key: '/inventory',
          icon: <AppstoreOutlined style={{ fontSize: 15 }} />,
          label: 'Inventory',
        },
        {
          key: '/orders',
          icon: <ShoppingCartOutlined style={{ fontSize: 15 }} />,
          label: 'Orders',
        },
        {
          key: '/shipments',
          icon: <CarOutlined style={{ fontSize: 15 }} />,
          label: 'Shipments',
        },
      ],
    },
    {
      type: 'group',
      label: (
        <span style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>
          EMPLOYEE OPERATIONS
        </span>
      ),
      children: [
        {
          key: '/employee',
          icon: <ToolOutlined style={{ fontSize: 15 }} />,
          label: 'Employee Hub',
        },
        {
          key: '/employee/work-orders',
          icon: <FileTextOutlined style={{ fontSize: 15 }} />,
          label: 'My Work Orders',
        },
        {
          key: '/employee/activity',
          icon: <HistoryOutlined style={{ fontSize: 15 }} />,
          label: 'My Activity',
        },
      ],
    },
    {
      type: 'group',
      label: (
        <span style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>
          INTELLIGENCE
        </span>
      ),
      children: [
        {
          key: '/risk',
          icon: <AlertOutlined style={{ fontSize: 15 }} />,
          label: 'Risk & Bottlenecks',
        },
        {
          key: '/forecast',
          icon: <LineChartOutlined style={{ fontSize: 15 }} />,
          label: 'Demand Forecast',
        },
        {
          key: '/analytics',
          icon: <BarChartOutlined style={{ fontSize: 15 }} />,
          label: 'Analytics & KPIs',
        },
      ],
    },
    {
      type: 'group',
      label: (
        <span style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>
          AI ENGINES
        </span>
      ),
      children: [
        {
          key: '/simulations',
          icon: <ThunderboltOutlined style={{ fontSize: 15 }} />,
          label: 'Simulations',
        },
      ],
    },
    {
      type: 'group',
      label: (
        <span style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>
          PLATFORM & TOOLS
        </span>
      ),
      children: [
        {
          key: '/console',
          icon: <ExperimentOutlined style={{ fontSize: 15 }} />,
          label: 'Simulation History',
        },
        {
          key: '/create-experiment',
          icon: <SettingOutlined style={{ fontSize: 15 }} />,
          label: 'Config Wizard',
        },
      ],
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
    if (windowWidth < 992) setMobileDrawerOpen(false);
  };

  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith('/suppliers')) return '/suppliers';
    if (path.startsWith('/inventory')) return '/inventory';
    if (path.startsWith('/orders')) return '/orders';
    if (path.startsWith('/shipments')) return '/shipments';
    if (path.startsWith('/risk')) return '/risk';
    if (path.startsWith('/forecast')) return '/forecast';
    if (path.startsWith('/simulations')) return '/simulations';
    if (path.startsWith('/analytics')) return '/analytics';
    if (path.startsWith('/network') || path.startsWith('/industry')) return '/network';
    if (path.startsWith('/console') || path.startsWith('/exp/') || path.startsWith('/replay/')) return '/console';
    if (path.startsWith('/create-experiment')) return '/create-experiment';
    return '/';
  };

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      label: (
        <div style={{ padding: '6px 4px' }}>
          <div style={{ fontWeight: 600, color: '#0F172A', fontSize: 13 }}>
            {user?.full_name || 'Sarah Jenkins'}
          </div>
          <div style={{ fontSize: 12, color: '#64748B' }}>
            {user?.email || 'sarah.jenkins@apex-logistics.com'}
          </div>
          <div style={{ marginTop: 6 }}>
            <Tag color="blue" style={{ fontSize: 10, fontWeight: 600, margin: 0 }}>
              {user?.role || 'ADMIN'}
            </Tag>
          </div>
        </div>
      ),
    },
    { type: 'divider' as const },
    {
      key: 'org',
      icon: <BankOutlined />,
      label: <span>{organization.name}</span>,
    },
    { type: 'divider' as const },
    {
      key: 'auth_action',
      icon: user?.id.startsWith('usr_demo') ? <LoginOutlined /> : <LogoutOutlined />,
      label: user?.id.startsWith('usr_demo') ? 'Sign In / Switch Tenant' : 'Sign Out',
      danger: !user?.id.startsWith('usr_demo'),
      onClick: () => {
        if (user?.id.startsWith('usr_demo')) {
          setAuthModalVisible(true);
        } else {
          logout();
        }
      },
    },
  ];

  // Coherent System status detail popover
  const systemStatusContent = (
    <div style={{ width: 270, padding: '4px 0' }}>
      <div style={{ fontWeight: 700, fontSize: 13, color: '#0F172A', marginBottom: 8 }}>
        SYSTEM TELEMETRY
      </div>
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Flex justify="space-between" align="center">
          <Flex align="center" gap={6}>
            {systemStatus.backendOnline ? (
              <CheckCircleFilled style={{ color: '#059669', fontSize: 13 }} />
            ) : (
              <CloseCircleFilled style={{ color: '#DC2626', fontSize: 13 }} />
            )}
            <span style={{ fontSize: 12, color: '#334155' }}>FastAPI Gateway</span>
          </Flex>
          <span style={{ fontSize: 12, fontWeight: 600, color: systemStatus.backendOnline ? '#059669' : '#DC2626' }}>
            {systemStatus.backendOnline ? 'OPERATIONAL' : 'OFFLINE'}
          </span>
        </Flex>

        <Flex justify="space-between" align="center">
          <Flex align="center" gap={6}>
            {systemStatus.databaseStatus === 'healthy' ? (
              <CheckCircleFilled style={{ color: '#059669', fontSize: 13 }} />
            ) : (
              <ExclamationCircleFilled style={{ color: '#D97706', fontSize: 13 }} />
            )}
            <span style={{ fontSize: 12, color: '#334155' }}>Database (PostgreSQL)</span>
          </Flex>
          <span style={{ fontSize: 12, fontWeight: 600, color: systemStatus.databaseStatus === 'healthy' ? '#059669' : '#D97706' }}>
            {systemStatus.databaseStatus === 'healthy' ? 'OPERATIONAL' : 'FALLBACK MODE'}
          </span>
        </Flex>

        <Flex justify="space-between" align="center">
          <Flex align="center" gap={6}>
            {systemStatus.neo4jMode === 'LIVE' ? (
              <CheckCircleFilled style={{ color: '#059669', fontSize: 13 }} />
            ) : (
              <ExclamationCircleFilled style={{ color: '#D97706', fontSize: 13 }} />
            )}
            <span style={{ fontSize: 12, color: '#334155' }}>Graph (Neo4j)</span>
          </Flex>
          <span style={{ fontSize: 12, fontWeight: 600, color: systemStatus.neo4jMode === 'LIVE' ? '#059669' : '#D97706' }}>
            {systemStatus.neo4jMode === 'LIVE' ? 'OPERATIONAL' : 'FALLBACK (CACHED)'}
          </span>
        </Flex>

        <Flex justify="space-between" align="center">
          <Flex align="center" gap={6}>
            <CheckCircleFilled style={{ color: '#2563EB', fontSize: 13 }} />
            <span style={{ fontSize: 12, color: '#334155' }}>AI Engine</span>
          </Flex>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#2563EB' }}>
            SIMULATION
          </span>
        </Flex>
      </Space>

      <Divider style={{ margin: '10px 0' }} />
      <div style={{ fontSize: 11, color: '#64748B', lineHeight: 1.4 }}>
        FastAPI live on port 8000. PostgreSQL offline on port 5432; certified in-memory fallback datasets active.
      </div>
    </div>
  );

  const sidebarContent = (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#0F172A',
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '16px 18px',
          borderBottom: '1px solid #1E293B',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 6,
            background: 'linear-gradient(135deg, #1E40AF, #3B82F6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FFFFFF',
            fontWeight: 800,
            fontSize: 15,
            boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
            flexShrink: 0,
          }}
        >
          SC
        </div>
        {!collapsed && (
          <div style={{ overflow: 'hidden' }}>
            <div
              style={{
                color: '#FFFFFF',
                fontWeight: 700,
                fontSize: 14,
                letterSpacing: '-0.01em',
                lineHeight: 1.2,
                whiteSpace: 'nowrap',
              }}
            >
              SupplyChainAgent
            </div>
            <div
              style={{
                color: '#94A3B8',
                fontSize: 11,
                fontWeight: 500,
                letterSpacing: '0.02em',
                whiteSpace: 'nowrap',
              }}
            >
              Control Tower SaaS
            </div>
          </div>
        )}
      </div>

      {/* Navigation Menu */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 0',
        }}
      >
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            backgroundColor: 'transparent',
            borderRight: 'none',
          }}
        />
      </div>

      {/* Bottom Sidebar Widget: Coherent Status & Collapse */}
      <div
        style={{
          padding: collapsed ? '12px 0' : '14px 16px',
          borderTop: '1px solid #1E293B',
          backgroundColor: '#0B1329',
          display: 'flex',
          flexDirection: 'column',
          alignItems: collapsed ? 'center' : 'stretch',
          gap: 10,
        }}
      >
        {!collapsed && (
          <div
            style={{
              padding: '10px 12px',
              backgroundColor: '#131E3A',
              borderRadius: 6,
              border: '1px solid #1E293B',
            }}
          >
            <Flex justify="space-between" align="center" style={{ marginBottom: 4 }}>
              <span style={{ color: '#94A3B8', fontSize: 11, fontWeight: 700, letterSpacing: '0.04em' }}>
                SYSTEM STATUS
              </span>
              <Tag
                color={isDemoMode ? 'purple' : systemStatus.databaseStatus === 'healthy' ? 'success' : 'warning'}
                style={{ fontSize: 9, margin: 0, lineHeight: '16px', padding: '0 4px', fontWeight: 700 }}
              >
                {isDemoMode ? 'DEMO' : systemStatus.databaseStatus === 'healthy' ? 'LIVE' : 'FALLBACK'}
              </Tag>
            </Flex>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
              <Flex align="center" gap={6}>
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: systemStatus.backendOnline ? '#10B981' : '#EF4444',
                  }}
                />
                <span style={{ color: '#CBD5E1', fontSize: 11 }}>
                  API: {systemStatus.backendOnline ? 'Operational' : 'Offline'}
                </span>
              </Flex>
              <Flex align="center" gap={6}>
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: systemStatus.databaseStatus === 'healthy' ? '#10B981' : '#F59E0B',
                  }}
                />
                <span style={{ color: '#CBD5E1', fontSize: 11 }}>
                  Database: {systemStatus.databaseStatus === 'healthy' ? 'Operational' : 'Fallback'}
                </span>
              </Flex>
              <Flex align="center" gap={6}>
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: systemStatus.neo4jMode === 'LIVE' ? '#10B981' : '#F59E0B',
                  }}
                />
                <span style={{ color: '#CBD5E1', fontSize: 11 }}>
                  Graph: {systemStatus.neo4jMode === 'LIVE' ? 'Operational' : 'Fallback'}
                </span>
              </Flex>
              <Flex align="center" gap={6}>
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: '#3B82F6',
                  }}
                />
                <span style={{ color: '#CBD5E1', fontSize: 11 }}>
                  AI: Simulation
                </span>
              </Flex>
            </div>
          </div>
        )}

        <Button
          type="text"
          block={!collapsed}
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => setCollapsed(!collapsed)}
          style={{
            color: '#94A3B8',
            fontSize: 14,
            height: 32,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {!collapsed && <span style={{ marginLeft: 8, fontSize: 12 }}>Collapse Sidebar</span>}
        </Button>
      </div>
    </div>
  );

  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#F8FAFC' }}>
      {/* Desktop Sider */}
      {windowWidth >= 992 && (
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          width={240}
          collapsedWidth={68}
          style={{
            backgroundColor: '#0F172A',
            borderRight: '1px solid #1E293B',
            position: 'sticky',
            top: 0,
            height: '100vh',
            zIndex: 100,
          }}
        >
          {sidebarContent}
        </Sider>
      )}

      {/* Mobile & Tablet Drawer */}
      {windowWidth < 992 && (
        <Drawer
          placement="left"
          open={mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
          styles={{ body: { padding: 0, backgroundColor: '#0F172A' } }}
          width={260}
        >
          {sidebarContent}
        </Drawer>
      )}

      <Layout style={{ backgroundColor: '#F8FAFC', minWidth: 0 }}>
        {/* Top Header Bar */}
        <Header
          style={{
            height: 56,
            padding: isMobile ? '0 12px' : '0 20px',
            backgroundColor: '#FFFFFF',
            borderBottom: '1px solid #E2E8F0',
            position: 'sticky',
            top: 0,
            zIndex: 90,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
            overflow: 'hidden',
          }}
        >
          {/* Left Controls: Drawer trigger & Organization Context */}
          <Flex align="center" gap={isMobile ? 6 : 10} style={{ minWidth: 0, flexShrink: 1 }}>
            {windowWidth < 992 && (
              <Button
                type="text"
                icon={<MenuUnfoldOutlined />}
                onClick={() => setMobileDrawerOpen(true)}
                style={{ fontSize: 16, color: '#475569', padding: '4px 6px' }}
              />
            )}

            <BankOutlined style={{ color: '#1E40AF', fontSize: 15, flexShrink: 0 }} />
            <div style={{ minWidth: 0, overflow: 'hidden' }}>
              <span
                style={{
                  fontWeight: 600,
                  fontSize: isMobile ? 12 : 13,
                  color: '#0F172A',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: 'inline-block',
                  maxWidth: isMobile ? 120 : isTablet ? 180 : 260,
                  verticalAlign: 'bottom',
                }}
              >
                {organization.name}
              </span>
              {!isMobile && (() => {
                const envConfig = getAppEnvironment(isDemoMode);
                return (
                  <Tag
                    color={envConfig.tagColor}
                    style={{
                      fontSize: 10,
                      marginLeft: 6,
                      padding: '0 5px',
                      lineHeight: '16px',
                      fontWeight: 700,
                      borderRadius: 4,
                      letterSpacing: '0.04em',
                    }}
                  >
                    {envConfig.label}
                  </Tag>
                );
              })()}
            </div>
          </Flex>

          {/* Right Controls: Unified Status, Demo Mode, Profile */}
          <Flex align="center" gap={isMobile ? 6 : 12} style={{ flexShrink: 0 }}>
            {/* Unified Compact System Status Indicator */}
            <Popover content={systemStatusContent} trigger="hover" placement="bottomRight">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: isMobile ? 4 : 8,
                  padding: isMobile ? '3px 6px' : '4px 8px',
                  backgroundColor: '#F8FAFC',
                  borderRadius: 6,
                  border: '1px solid #E2E8F0',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
              >
                <Flex align="center" gap={4}>
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      backgroundColor: systemStatus.backendOnline ? '#10B981' : '#EF4444',
                    }}
                  />
                  {!isMobile && (
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#334155' }}>
                      API
                    </span>
                  )}
                </Flex>
                <span style={{ color: '#CBD5E1', fontSize: 10 }}>|</span>
                <Flex align="center" gap={4}>
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      backgroundColor: '#F59E0B',
                    }}
                  />
                  {!isMobile && (
                    <span style={{ fontSize: 11, fontWeight: 500, color: '#64748B' }}>
                      Graph
                    </span>
                  )}
                </Flex>
              </div>
            </Popover>

            {/* Demo Mode Toggle */}
            <Tooltip title="Switch between live backend data and certified offline demonstration records.">
              <Flex
                align="center"
                gap={6}
                style={{
                  padding: isMobile ? '2px 6px' : '3px 8px',
                  backgroundColor: isDemoMode ? '#EFF6FF' : '#F1F5F9',
                  border: isDemoMode ? '1px solid #BFDBFE' : '1px solid #E2E8F0',
                  borderRadius: 6,
                }}
              >
                {!isMobile && (
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                      color: isDemoMode ? '#1D4ED8' : '#64748B',
                    }}
                  >
                    DEMO
                  </span>
                )}
                <Switch
                  size="small"
                  checked={isDemoMode}
                  onChange={setDemoMode}
                />
              </Flex>
            </Tooltip>

            {/* User Profile Menu */}
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  cursor: 'pointer',
                  padding: '2px 4px',
                  borderRadius: 6,
                }}
              >
                <Avatar
                  size={28}
                  style={{
                    backgroundColor: '#1E40AF',
                    color: '#FFFFFF',
                    fontWeight: 700,
                    fontSize: 11,
                  }}
                >
                  {user?.full_name ? user.full_name[0].toUpperCase() : 'S'}
                </Avatar>
                {!isMobile && (
                  <div style={{ textAlign: 'left', lineHeight: 1.1 }}>
                    <div style={{ fontWeight: 600, fontSize: 12, color: '#0F172A' }}>
                      {user?.full_name ? user.full_name.split(' ')[0] : 'Sarah'}
                    </div>
                    <div style={{ fontSize: 9, color: '#64748B', fontWeight: 600 }}>
                      {user?.role || 'ADMIN'}
                    </div>
                  </div>
                )}
              </div>
            </Dropdown>
          </Flex>
        </Header>

        {/* Primary Main Content */}
        <Content style={{ minHeight: 'calc(100vh - 56px)', paddingBottom: 24, minWidth: 0 }}>
          {children}
        </Content>
      </Layout>

      {/* Global Authentication Modal */}
      <AuthModal />
    </Layout>
  );
};

export default AppShell;
