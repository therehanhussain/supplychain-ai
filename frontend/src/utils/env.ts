/**
 * Application Environment and Data Provenance Utility.
 *
 * Dynamically resolves environment tier and provides semantic badges
 * for LOCAL DEVELOPMENT, DEMO, STAGING, and PRODUCTION.
 */

export type AppEnvironment = 'development' | 'demo' | 'staging' | 'production';

export interface EnvironmentConfig {
  env: AppEnvironment;
  label: string;
  badgeColor: string;
  tagColor: string;
  isProduction: boolean;
}

/**
 * Resolves active environment from VITE_APP_ENV, import.meta.env.MODE, or Demo toggle.
 */
export function getAppEnvironment(isDemoMode: boolean = false): EnvironmentConfig {
  if (isDemoMode) {
    return {
      env: 'demo',
      label: 'DEMO SANDBOX',
      badgeColor: '#7C3AED',
      tagColor: 'purple',
      isProduction: false,
    };
  }

  // Priority: VITE_APP_ENV > import.meta.env.MODE > default 'development'
  const rawEnv = (
    (import.meta as any).env?.VITE_APP_ENV ||
    (import.meta as any).env?.MODE ||
    'development'
  ).toLowerCase().trim();

  if (rawEnv === 'production' || rawEnv === 'prod') {
    return {
      env: 'production',
      label: 'PRODUCTION',
      badgeColor: '#2563EB',
      tagColor: 'blue',
      isProduction: true,
    };
  }

  if (rawEnv === 'staging' || rawEnv === 'stage') {
    return {
      env: 'staging',
      label: 'STAGING',
      badgeColor: '#D97706',
      tagColor: 'orange',
      isProduction: false,
    };
  }

  if (rawEnv === 'demo') {
    return {
      env: 'demo',
      label: 'DEMO',
      badgeColor: '#7C3AED',
      tagColor: 'purple',
      isProduction: false,
    };
  }

  return {
    env: 'development',
    label: 'LOCAL DEVELOPMENT',
    badgeColor: '#0891B2',
    tagColor: 'cyan',
    isProduction: false,
  };
}

/**
 * Returns a compact label for data provenance.
 */
export function formatProvenanceLabel(
  provenance: 'LIVE' | 'DEMO' | 'FALLBACK' | 'SIMULATED' | 'MOCK'
): { label: string; color: string } {
  switch (provenance) {
    case 'LIVE':
      return { label: 'LIVE DATA', color: 'green' };
    case 'DEMO':
      return { label: 'DEMO DATA', color: 'purple' };
    case 'FALLBACK':
      return { label: 'FALLBACK DATA', color: 'orange' };
    case 'SIMULATED':
      return { label: 'SIMULATION DATA', color: 'blue' };
    case 'MOCK':
    default:
      return { label: 'MOCK DATA', color: 'default' };
  }
}
