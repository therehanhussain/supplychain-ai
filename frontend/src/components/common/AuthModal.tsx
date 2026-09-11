import React, { useState } from 'react';
import { Modal, Tabs, Form, Input, Button, Alert, Typography } from 'antd';
import { LockOutlined, MailOutlined, UserOutlined, BankOutlined } from '@ant-design/icons';
import { useApp } from '../../context/AppContext';

const { Text } = Typography;

export const AuthModal: React.FC = () => {
  const { authModalVisible, setAuthModalVisible, login, register } = useApp();
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();

  const handleLogin = async (values: any) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      await login(values.email, values.password);
      loginForm.resetFields();
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: any) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      await register({
        organization_name: values.organization_name,
        full_name: values.full_name,
        email: values.email,
        password: values.password,
      });
      registerForm.resetFields();
    } catch (err: any) {
      setErrorMessage(err.message || 'Registration failed. The email or organization name may already exist.');
    } finally {
      setLoading(false);
    }
  };

  const handleUseDemo = async () => {
    loginForm.setFieldsValue({
      email: 'admin@test.corp',
      password: 'Password123!',
    });
  };

  return (
    <Modal
      title={
        <div style={{ textAlign: 'center', paddingBottom: 8 }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#0F172A' }}>SupplyChainAgent Access</div>
          <Text type="secondary" style={{ fontSize: 13 }}>Production Control Tower & Multi-Agent Intelligence</Text>
        </div>
      }
      open={authModalVisible}
      onCancel={() => setAuthModalVisible(false)}
      footer={null}
      width={440}
      centered
      destroyOnClose
    >
      {errorMessage && (
        <Alert
          message={errorMessage}
          type="error"
          showIcon
          closable
          onClose={() => setErrorMessage(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={(k) => {
          setActiveTab(k as any);
          setErrorMessage(null);
        }}
        centered
        items={[
          {
            key: 'login',
            label: 'Sign In',
            children: (
              <Form form={loginForm} layout="vertical" onFinish={handleLogin} style={{ marginTop: 8 }}>
                <Form.Item
                  name="email"
                  label="Business Email"
                  rules={[{ required: true, message: 'Please enter your email' }, { type: 'email', message: 'Valid email required' }]}
                >
                  <Input prefix={<MailOutlined style={{ color: '#94A3B8' }} />} placeholder="operator@company.com" size="large" />
                </Form.Item>

                <Form.Item
                  name="password"
                  label="Password"
                  rules={[{ required: true, message: 'Please enter your password' }]}
                >
                  <Input.Password prefix={<LockOutlined style={{ color: '#94A3B8' }} />} placeholder="Enter password" size="large" />
                </Form.Item>

                <Button type="primary" htmlType="submit" size="large" block loading={loading} style={{ marginTop: 8 }}>
                  Sign In to Control Tower
                </Button>

                <div style={{ marginTop: 16, textAlign: 'center' }}>
                  <Button type="link" size="small" onClick={handleUseDemo}>
                    Fill Demo Credentials (admin@test.corp)
                  </Button>
                </div>
              </Form>
            ),
          },
          {
            key: 'register',
            label: 'Register Organization',
            children: (
              <Form form={registerForm} layout="vertical" onFinish={handleRegister} style={{ marginTop: 8 }}>
                <Form.Item
                  name="organization_name"
                  label="Organization / Company Name"
                  rules={[{ required: true, message: 'Organization name required' }]}
                >
                  <Input prefix={<BankOutlined style={{ color: '#94A3B8' }} />} placeholder="e.g. Apex Global Logistics" size="large" />
                </Form.Item>

                <Form.Item
                  name="full_name"
                  label="Administrator Name"
                  rules={[{ required: true, message: 'Full name required' }]}
                >
                  <Input prefix={<UserOutlined style={{ color: '#94A3B8' }} />} placeholder="e.g. Sarah Jenkins" size="large" />
                </Form.Item>

                <Form.Item
                  name="email"
                  label="Admin Email"
                  rules={[{ required: true, message: 'Email required' }, { type: 'email', message: 'Valid email required' }]}
                >
                  <Input prefix={<MailOutlined style={{ color: '#94A3B8' }} />} placeholder="admin@apex-logistics.com" size="large" />
                </Form.Item>

                <Form.Item
                  name="password"
                  label="Master Password (min 8 characters)"
                  rules={[{ required: true, min: 8, message: 'Minimum 8 characters required' }]}
                >
                  <Input.Password prefix={<LockOutlined style={{ color: '#94A3B8' }} />} placeholder="Create strong password" size="large" />
                </Form.Item>

                <Button type="primary" htmlType="submit" size="large" block loading={loading} style={{ marginTop: 8 }}>
                  Provision Organization Account
                </Button>
              </Form>
            ),
          },
        ]}
      />
    </Modal>
  );
};

export default AuthModal;
