import React from 'react';
import { Card, Typography, Flex, Skeleton, Tag } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const { Text } = Typography;

export interface KpiCardProps {
  title: string;
  value: string | number;
  prefix?: React.ReactNode;
  suffix?: string;
  trend?: {
    value: number;
    isPositiveGood?: boolean;
    label?: string;
  };
  icon?: React.ReactNode;
  badge?: {
    text: string;
    color: string;
  };
  subtitle?: string;
  loading?: boolean;
  statusColor?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  prefix,
  suffix,
  trend,
  icon,
  badge,
  subtitle,
  loading = false,
  statusColor,
}) => {
  if (loading) {
    return (
      <Card
        style={{
          borderRadius: 8,
          border: '1px solid #E2E8F0',
          boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
          height: 142,
        }}
        bodyStyle={{ padding: '16px 20px' }}
      >
        <Skeleton active paragraph={{ rows: 2 }} title={{ width: '40%' }} />
      </Card>
    );
  }

  const isUp = trend ? trend.value > 0 : false;
  const isNeutral = trend ? trend.value === 0 : true;
  let trendColor = '#64748B';

  if (trend && !isNeutral) {
    const isGood = trend.isPositiveGood ?? true;
    trendColor = isUp
      ? (isGood ? '#059669' : '#DC2626')
      : (isGood ? '#DC2626' : '#059669');
  }

  return (
    <Card
      style={{
        borderRadius: 8,
        border: '1px solid #E2E8F0',
        backgroundColor: '#FFFFFF',
        boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
        borderTop: statusColor ? `3px solid ${statusColor}` : undefined,
        height: 142,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}
      bodyStyle={{
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%',
      }}
    >
      <div>
        <Flex justify="space-between" align="center">
          <Text
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: '#64748B',
            }}
          >
            {title}
          </Text>
          {icon && (
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 6,
                backgroundColor: '#F1F5F9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 16,
                color: '#1E40AF',
              }}
            >
              {icon}
            </div>
          )}
        </Flex>

        <div style={{ marginTop: 4, display: 'flex', alignItems: 'baseline', gap: 6 }}>
          {prefix && <span style={{ fontSize: 18, fontWeight: 600, color: '#0F172A' }}>{prefix}</span>}
          <span
            style={{
              fontSize: 26,
              fontWeight: 700,
              color: '#0F172A',
              letterSpacing: '-0.02em',
              lineHeight: 1.15,
            }}
          >
            {value}
          </span>
          {suffix && (
            <span style={{ fontSize: 13, fontWeight: 500, color: '#64748B', marginLeft: 2 }}>
              {suffix}
            </span>
          )}
        </div>
      </div>

      <Flex justify="space-between" align="center" style={{ marginTop: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {trend ? (
            <Flex align="center" gap={4}>
              {isUp ? (
                <ArrowUpOutlined style={{ color: trendColor, fontSize: 11 }} />
              ) : !isNeutral ? (
                <ArrowDownOutlined style={{ color: trendColor, fontSize: 11 }} />
              ) : null}
              <span style={{ color: trendColor, fontWeight: 600, fontSize: 12 }}>
                {Math.abs(trend.value)}%
              </span>
              <span
                style={{
                  color: '#64748B',
                  fontSize: 11,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {trend.label || 'vs prior period'}
              </span>
            </Flex>
          ) : subtitle ? (
            <span
              style={{
                fontSize: 12,
                color: '#64748B',
                fontWeight: 500,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: 'block',
              }}
            >
              {subtitle}
            </span>
          ) : null}
        </div>

        {badge && (
          <Tag
            color={badge.color}
            style={{
              fontSize: 10,
              fontWeight: 600,
              borderRadius: 4,
              padding: '0 6px',
              margin: 0,
              lineHeight: '18px',
              flexShrink: 0,
            }}
          >
            {badge.text}
          </Tag>
        )}
      </Flex>
    </Card>
  );
};

export default KpiCard;
