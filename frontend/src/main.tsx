import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';
import { ConfigProvider, ThemeConfig } from 'antd';
import enUS from 'antd/locale/en_US';

import { AppProvider } from './context/AppContext';
import AppShell from './components/layout/AppShell';

// Control Tower Pages
import Dashboard from './pages/Dashboard';
import NetworkPage from './pages/Network';
import SuppliersPage from './pages/Suppliers';
import InventoryPage from './pages/Inventory';
import OrdersPage from './pages/Orders';
import ShipmentsPage from './pages/Shipments';
import RiskPage from './pages/Risk';
import ForecastPage from './pages/Forecast';
import SimulationsPage from './pages/Simulations';
import AnalyticsPage from './pages/Analytics';

// Employee Operations Portal (Phase 13.2)
import EmployeeDashboard from './pages/Employee/EmployeeDashboard';
import MyWorkOrders from './pages/Employee/MyWorkOrders';
import WorkOrderDetail from './pages/Employee/WorkOrderDetail';
import MyActivity from './pages/Employee/MyActivity';

// Preserved Research & Simulation Pages
import Console from './pages/Console/index';
import Replay from './pages/Replay/index';
import Survey from './pages/Survey/index';
import LLMList from './pages/Experiment/LLMList';
import AgentList from './pages/Experiment/AgentList';
import WorkflowList from './pages/Experiment/WorkflowList';
import CreateExperiment from './pages/Experiment/CreateExperiment';
import storageService from './services/storageService';

const router = createBrowserRouter([
  // Core Control Tower
  {
    path: "/",
    element: <AppShell><Dashboard /></AppShell>,
  },
  {
    path: "/overview",
    element: <AppShell><Dashboard /></AppShell>,
  },
  {
    path: "/network",
    element: <AppShell><NetworkPage /></AppShell>,
  },
  {
    path: "/industry",
    element: <AppShell><NetworkPage /></AppShell>,
  },

  // Operations
  {
    path: "/suppliers",
    element: <AppShell><SuppliersPage /></AppShell>,
  },
  {
    path: "/inventory",
    element: <AppShell><InventoryPage /></AppShell>,
  },
  {
    path: "/orders",
    element: <AppShell><OrdersPage /></AppShell>,
  },
  {
    path: "/shipments",
    element: <AppShell><ShipmentsPage /></AppShell>,
  },

  // Employee Operations Portal (Phase 13.2)
  {
    path: "/employee",
    element: <AppShell><EmployeeDashboard /></AppShell>,
  },
  {
    path: "/employee/work-orders",
    element: <AppShell><MyWorkOrders /></AppShell>,
  },
  {
    path: "/employee/work-orders/:id",
    element: <AppShell><WorkOrderDetail /></AppShell>,
  },
  {
    path: "/employee/activity",
    element: <AppShell><MyActivity /></AppShell>,
  },

  // Intelligence & AI
  {
    path: "/risk",
    element: <AppShell><RiskPage /></AppShell>,
  },
  {
    path: "/forecast",
    element: <AppShell><ForecastPage /></AppShell>,
  },
  {
    path: "/simulations",
    element: <AppShell><SimulationsPage /></AppShell>,
  },

  // Analytics
  {
    path: "/analytics",
    element: <AppShell><AnalyticsPage /></AppShell>,
  },

  // Preserved Simulation History & Tools
  {
    path: "/console",
    element: <AppShell><Console /></AppShell>,
  },
  {
    path: "/exp/:id",
    element: <AppShell><Replay /></AppShell>,
  },
  {
    path: "/replay/:id",
    element: <AppShell><Replay /></AppShell>,
  },
  {
    path: "/survey",
    element: <AppShell><Survey /></AppShell>,
  },
  {
    path: "/create-experiment",
    element: <AppShell><CreateExperiment /></AppShell>,
  },
  {
    path: "/llms",
    element: <AppShell><LLMList /></AppShell>,
  },
  {
    path: "/agents",
    element: <AppShell><AgentList /></AppShell>,
  },
  {
    path: "/workflows",
    element: <AppShell><WorkflowList /></AppShell>,
  },
  {
    path: "*",
    element: <Navigate to="/" />,
  },
]);

const theme: ThemeConfig = {
  token: {
    colorPrimary: "#1E40AF", // Enterprise Blue 800
    colorInfo: "#0284C7", // Sky 600
    colorSuccess: "#059669", // Emerald 600
    colorWarning: "#D97706", // Amber 600
    colorError: "#DC2626", // Red 600
    borderRadius: 6,
    colorBgLayout: "#F8FAFC", // Slate 50
    colorBgContainer: "#FFFFFF",
    colorBorder: "#E2E8F0",
    colorText: "#0F172A",
    colorTextSecondary: "#64748B",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Layout: {
      headerBg: "#FFFFFF",
      bodyBg: "#F8FAFC",
      siderBg: "#0F172A",
    },
    Card: {
      borderRadiusLG: 8,
    },
    Button: {
      borderRadius: 6,
      controlHeight: 36,
      fontWeight: 500,
    },
    Table: {
      borderRadius: 8,
      headerBg: "#F8FAFC",
      headerColor: "#475569",
    },
  },
};

// Initialize fallback storage
storageService.initializeExampleData().catch(error => {
  console.error('Failed to initialize example data:', error);
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ConfigProvider theme={theme} locale={enUS}>
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  </ConfigProvider>
);
