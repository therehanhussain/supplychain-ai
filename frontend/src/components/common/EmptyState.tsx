import React from 'react';
import { Empty, Button } from 'antd';
import { PlusOutlined, InboxOutlined } from '@ant-design/icons';

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No Records Found",
  description = "No items match your query or the catalog is empty for this organization.",
  actionText,
  onAction,
  icon,
}) => {
  return (
    <div style={{ padding: '48px 24px', textAlign: 'center', backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px dashed #CBD5E1' }}>
      <Empty
        image={icon || <InboxOutlined style={{ fontSize: 48, color: '#94A3B8' }} />}
        description={
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: '#334155', marginBottom: 4 }}>{title}</div>
            <div style={{ color: '#64748B', fontSize: 13, maxWidth: 400, margin: '0 auto' }}>{description}</div>
          </div>
        }
      >
        {actionText && onAction && (
          <Button type="primary" icon={<PlusOutlined />} onClick={onAction} style={{ marginTop: 12 }}>
            {actionText}
          </Button>
        )}
      </Empty>
    </div>
  );
};

export default EmptyState;
