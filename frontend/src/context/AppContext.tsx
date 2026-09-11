/**
 * Global Application Context & State Provider.
 *
 * Provides reactive authentication state, active organization/tenant context,
 * system health beacon, and user-toggleable Demo Mode.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient, { UserProfile } from '../services/apiClient';
import controlTowerApi from '../services/controlTowerApi';

export interface OrganizationContext {
  id: string;
  name: string;
  slug: string;
  tier: string;
}

export interface SystemStatus {
  backendOnline: boolean;
  databaseStatus: 'healthy' | 'degraded' | 'unavailable';
  neo4jMode: 'LIVE' | 'FALLBACK' | 'DEGRADED' | 'UNAVAILABLE' | 'CHECKING';
  version: string;
}

interface AppContextType {
  user: UserProfile | null;
  organization: OrganizationContext;
  isDemoMode: boolean;
  setDemoMode: (enabled: boolean) => void;
  systemStatus: SystemStatus;
  authModalVisible: boolean;
  setAuthModalVisible: (visible: boolean) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { organization_name: string; email: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const DEFAULT_DEMO_USER: UserProfile = {
  id: "usr_demo_01",
  organization_id: "org_demo_apex",
  email: "executive@apex-logistics.com",
  full_name: "Sarah Jenkins (Director of Supply Chain)",
  role: "ADMIN",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

const DEFAULT_ORG: OrganizationContext = {
  id: "org_demo_apex",
  name: "Apex Global Logistics Inc.",
  slug: "apex-logistics",
  tier: "Enterprise Production",
};

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    // If token exists, we'll try to fetch me, otherwise default to demo user
    const token = apiClient.getAccessToken();
    return token ? null : DEFAULT_DEMO_USER;
  });

  const [organization, setOrganization] = useState<OrganizationContext>(DEFAULT_ORG);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [authModalVisible, setAuthModalVisible] = useState<boolean>(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    backendOnline: false,
    databaseStatus: 'degraded',
    neo4jMode: 'CHECKING',
    version: '0.1.0',
  });

  const checkHealth = useCallback(async () => {
    const status = await controlTowerApi.getSystemStatus();
    setSystemStatus(status);
  }, []);

  const refreshUser = useCallback(async () => {
    const token = apiClient.getAccessToken();
    if (!token) {
      if (!user) setUser(DEFAULT_DEMO_USER);
      return;
    }
    try {
      const me = await apiClient.getMe();
      setUser(me);
      setOrganization({
        id: me.organization_id,
        name: `Organization (${me.organization_id.substring(0, 8)})`,
        slug: me.organization_id,
        tier: "Enterprise Tier",
      });
    } catch {
      // If token expired or server offline
      setUser(DEFAULT_DEMO_USER);
    }
  }, [user]);

  useEffect(() => {
    checkHealth();
    refreshUser();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth, refreshUser]);

  const login = async (email: string, password: string) => {
    await apiClient.login(email, password);
    await refreshUser();
    setAuthModalVisible(false);
  };

  const register = async (data: { organization_name: string; email: string; password: string; full_name?: string }) => {
    await apiClient.register(data);
    await apiClient.login(data.email, data.password);
    await refreshUser();
    setAuthModalVisible(false);
  };

  const logout = () => {
    apiClient.logout();
    setUser(DEFAULT_DEMO_USER);
    setOrganization(DEFAULT_ORG);
  };

  return (
    <AppContext.Provider
      value={{
        user,
        organization,
        isDemoMode,
        setDemoMode: setIsDemoMode,
        systemStatus,
        authModalVisible,
        setAuthModalVisible,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default AppContext;
