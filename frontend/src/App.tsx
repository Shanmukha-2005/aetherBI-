import React, { useState, useEffect } from 'react';
import { api, User, DatasetSummary } from './api/client';
import { Navbar } from './components/layout/Navbar';
import { Tabs, TabType } from './components/layout/Tabs';
import { AuthPage } from './pages/AuthPage';
import { UploadPage } from './pages/UploadPage';
import { DataHealthPage } from './pages/DataHealthPage';
import { FactsPage } from './pages/FactsPage';
import { DashboardPage } from './pages/DashboardPage';
import { SqlStudioPage } from './pages/SqlStudioPage';

export const App: React.FC = () => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('bi_token'));
  const [user, setUser] = useState<User | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetSummary | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('upload');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      initApp();
    } else {
      setLoading(false);
    }
  }, [token]);

  const initApp = async () => {
    setLoading(true);
    try {
      const [userRes, dsRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/datasets'),
      ]);
      setUser(userRes.data);
      setDatasets(dsRes.data);
      if (dsRes.data.length > 0) {
        setSelectedDataset(dsRes.data[0]);
        setActiveTab('health');
      } else {
        setActiveTab('upload');
      }
    } catch (err) {
      console.error('Session expired or invalid', err);
      handleLogout();
    } finally {
      setLoading(false);
    }
  };

  const handleAuthSuccess = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    initApp();
  };

  const handleLogout = () => {
    localStorage.removeItem('bi_token');
    setToken(null);
    setUser(null);
    setDatasets([]);
    setSelectedDataset(null);
    setActiveTab('upload');
  };

  const handleDatasetUploaded = (newDs: DatasetSummary) => {
    setDatasets((prev) => [newDs, ...prev.filter((d) => d.id !== newDs.id)]);
    setSelectedDataset(newDs);
    setActiveTab('health'); // Immediately highlight Requirement 1 data health fixes!
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-xs text-slate-400">Initializing AetherBI Studio...</p>
        </div>
      </div>
    );
  }

  if (!token || !user) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="min-h-screen bg-dark-bg text-slate-100 flex flex-col">
      <Navbar
        user={user}
        datasets={datasets}
        selectedDataset={selectedDataset}
        onSelectDataset={(ds) => {
          setSelectedDataset(ds);
          if (activeTab === 'upload') setActiveTab('dashboard');
        }}
        onLogout={handleLogout}
        onOpenUpload={() => setActiveTab('upload')}
      />

      <Tabs
        activeTab={activeTab}
        onChangeTab={setActiveTab}
        hasDataset={!!selectedDataset}
        healthScore={selectedDataset?.health_score}
      />

      <main className="flex-1 pb-16">
        {activeTab === 'upload' && (
          <UploadPage onDatasetUploaded={handleDatasetUploaded} />
        )}

        {selectedDataset && activeTab === 'health' && (
          <DataHealthPage
            key={`health-${selectedDataset.id}`}
            datasetId={selectedDataset.id}
            datasetName={selectedDataset.name}
          />
        )}

        {selectedDataset && activeTab === 'facts' && (
          <FactsPage key={`facts-${selectedDataset.id}`} datasetId={selectedDataset.id} />
        )}

        {selectedDataset && activeTab === 'dashboard' && (
          <DashboardPage
            key={`dash-${selectedDataset.id}`}
            datasetId={selectedDataset.id}
            datasetName={selectedDataset.name}
          />
        )}

        {selectedDataset && activeTab === 'sql' && (
          <SqlStudioPage
            key={`sql-${selectedDataset.id}`}
            datasetId={selectedDataset.id}
            datasetName={selectedDataset.name}
          />
        )}
      </main>
    </div>
  );
};
export default App;
