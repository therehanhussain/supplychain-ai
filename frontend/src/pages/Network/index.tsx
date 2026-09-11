/**
 * Supply Network Graph Control Tower View.
 *
 * Wraps the AntV G6 multi-tier supply chain topological graph with
 * live/fallback data provenance tracking and control tower action headers.
 */

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Typography, Flex, Tag, Alert } from 'antd';
import { NodeIndexOutlined, InfoCircleOutlined } from '@ant-design/icons';

import PageHeader from '../../components/common/PageHeader';
import ProvenanceBadge from '../../components/common/ProvenanceBadge';
import IndustryGraph from '../maps/IndustryGraph';
import controlTowerApi, { DataProvenance } from '../../services/controlTowerApi';
import { useApp } from '../../context/AppContext';

const { Text } = Typography;

export const NetworkPage: React.FC = () => {
  const { systemStatus, isDemoMode } = useApp();
  const [provenance, setProvenance] = useState<DataProvenance>('FALLBACK');
  const [sourceNote, setSourceNote] = useState<string>('');

  useEffect(() => {
    if (isDemoMode) {
      setProvenance('DEMO');
      setSourceNote('Demonstration graph dataset loaded.');
    } else if (systemStatus.neo4jMode === 'LIVE') {
      setProvenance('LIVE');
      setSourceNote('Live Neo4j graph cluster bolt connection.');
    } else {
      setProvenance('FALLBACK');
      setSourceNote('Neo4j cluster offline. Certified fallback supply graph topology loaded.');
    }
  }, [systemStatus, isDemoMode]);

  return (
    <div>
      <PageHeader
        title="Multi-Tier Supply Network"
        subtitle="End-to-end topological visualization of material dependencies, tiered manufacturers, and supply relationships."
        breadcrumbs={[{ title: 'Control Tower', path: '/' }, { title: 'Supply Network' }]}
        provenance={provenance}
        sourceNote={sourceNote}
      />

      <div style={{ padding: '0 24px' }}>
        {provenance !== 'LIVE' && (
          <Alert
            type="info"
            showIcon
            message="Using Cached Network Topology [FALLBACK]"
            description="The live Neo4j cluster is unconfigured in this local environment. Displaying verified cached multi-tier supply network topology and component relationships."
            style={{ marginBottom: 16, borderRadius: 6, border: '1px solid #BAE6FD', backgroundColor: '#F0F9FF' }}
          />
        )}

        <div style={{ backgroundColor: '#FFFFFF', borderRadius: 8, border: '1px solid #E2E8F0', padding: 16 }}>
          <IndustryGraph />
        </div>
      </div>
    </div>
  );
};

export default NetworkPage;
