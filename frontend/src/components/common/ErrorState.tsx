import React from 'react';
import { Result, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retrying?: boolean;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Failed to Load Data",
  message = "A network error or connection timeout occurred while communicating with the backend API.",
  onRetry,
  retrying = false,
}) => {
  return (
    <div style={{ padding: '36px 20px', backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #FECACA' }}>
      <Result
        status="error"
        title={<span style={{ fontSize: 18, fontWeight: 600 }}>{title}</span>}
        subTitle={<span style={{ fontSize: 13, color: '#64748B' }}>{message}</span>}
        extra={
          onRetry && (
            <Button
              type="primary"
              danger
              icon={<ReloadOutlined spin={retrying} />}
              onClick={onRetry}
              loading={retrying}
            >
              Retry Connection
            </Button>
          )
        }
      />
    </div>
  );
};

export default ErrorState;
