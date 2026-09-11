import React from 'react';
import { Breadcrumb, Typography, Flex, Space, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import ProvenanceBadge from './ProvenanceBadge';
import { DataProvenance } from '../../services/controlTowerApi';

const { Text } = Typography;

interface BreadcrumbItem {
  title: string;
  path?: string;
}

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  provenance?: DataProvenance | 'SIMULATED';
  sourceNote?: string;
  extra?: React.ReactNode;
  onRefresh?: () => void;
  refreshing?: boolean;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  breadcrumbs = [{ title: 'Control Tower', path: '/' }],
  provenance,
  sourceNote,
  extra,
  onRefresh,
  refreshing = false,
}) => {
  return (
    <div
      style={{
        padding: '14px 24px',
        backgroundColor: '#FFFFFF',
        borderBottom: '1px solid #E2E8F0',
        marginBottom: 16,
      }}
    >
      {breadcrumbs.length > 1 && (
        <Breadcrumb
          style={{ marginBottom: 4, fontSize: 11 }}
          items={breadcrumbs.map((b, idx) => ({
            title:
              b.path && idx < breadcrumbs.length - 1 ? (
                <Link to={b.path} style={{ color: '#64748B' }}>
                  {b.title}
                </Link>
              ) : (
                <span style={{ color: '#0F172A', fontWeight: 600 }}>{b.title}</span>
              ),
          }))}
        />
      )}

      <Flex justify="space-between" align="center" wrap="wrap" gap="middle">
        <div style={{ flex: '1 1 300px' }}>
          <Flex align="center" gap={10} wrap="wrap">
            <h1
              style={{
                margin: 0,
                fontSize: 20,
                fontWeight: 700,
                letterSpacing: '-0.02em',
                color: '#0F172A',
                lineHeight: 1.25,
              }}
            >
              {title}
            </h1>
            {provenance && (
              <ProvenanceBadge provenance={provenance} sourceNote={sourceNote} size="small" />
            )}
          </Flex>
          {subtitle && (
            <Text
              style={{
                fontSize: 13,
                color: '#64748B',
                marginTop: 2,
                display: 'block',
                lineHeight: 1.35,
              }}
            >
              {subtitle}
            </Text>
          )}
        </div>

        <Space size="small" wrap style={{ flexShrink: 0 }}>
          {onRefresh && (
            <Button
              icon={<ReloadOutlined spin={refreshing} />}
              onClick={onRefresh}
              loading={refreshing}
              style={{ height: 36, fontWeight: 500, fontSize: 13 }}
            >
              Refresh
            </Button>
          )}
          {extra}
        </Space>
      </Flex>
    </div>
  );
};

export default PageHeader;
