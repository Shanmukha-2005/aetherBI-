import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { UploadCloud, FileSpreadsheet, CheckCircle2, AlertCircle, Loader2, Sparkles, Database } from 'lucide-react';
import { api, DatasetSummary } from '../api/client';

interface UploadPageProps {
  onDatasetUploaded: (dataset: DatasetSummary) => void;
}

export const UploadPage: React.FC<UploadPageProps> = ({ onDatasetUploaded }) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      selectFile(e.dataTransfer.files[0]);
    }
  };

  const selectFile = (selected: File) => {
    setFile(selected);
    if (!datasetName) {
      const cleanName = selected.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
      setDatasetName(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setStage('Ingesting and parsing tabular records...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', datasetName);

    try {
      setTimeout(() => setStage('Scanning missing values, anomalies & skewed distributions...'), 800);
      setTimeout(() => setStage('Executing automated best-practice remediation & writing SQLite table...'), 1600);
      setTimeout(() => setStage('Uncovering variable correlations & unique dataset facts...'), 2400);

      const res = await api.post('/datasets/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setStage('Complete!');
      onDatasetUploaded(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please ensure file is a valid CSV or Excel document.');
    } finally {
      setLoading(false);
    }
  };

  const loadSampleDataset = async () => {
    // Generate sample business dataset directly in browser and upload
    const sampleCsv = `Order ID,Customer Name,Segment,Region,Category,Sales Amount,Profit,Discount Rate,Order Date,Sparse Notes
1001,TechCorp Solutions,Enterprise,West,Technology,14200.50,3200.00,0.05,2023-01-12,
1002,Acme Logistics,SMB,East,Office Supplies,850.00,120.50,0.10,01/14/2023,
1003,Global Dynamics,Enterprise,West,Technology,24500.00,5800.00,0.00,2023-01-15,Special client
1004,Urban Retail,Consumer,Central,Furniture,1200.00,,0.15,2023-01-18,
1005,Starlight Ventures,SMB,East,Technology,4300.00,890.00,,2023-01-20,
1006,Summit Analytics,Enterprise,West,Technology,18900.00,4100.00,0.05,01/22/2023,
1007,Pinnacle Group,Enterprise,West,Furniture,3100.00,-450.00,0.25,2023-01-25,
1008,Nexus Media,Consumer,South,Office Supplies,,35.00,0.00,2023-01-28,
1009,Delta Services,SMB,Central,Office Supplies,640.00,80.00,0.10,2023-02-02,
1010,Vanguard Health,Enterprise,East,Technology,32000.00,7400.00,0.00,02/05/2023,
1011,Horizon Labs,SMB,West,Technology,5600.00,1100.00,0.05,2023-02-08,
1012,Crestview Capital,Enterprise,West,Furniture,8900.00,-1200.00,0.30,2023-02-12,
1013,Apex Industrial,SMB,Central,Office Supplies,450.00,50.00,0.00,02/15/2023,
1014,Echo Software,Consumer,East,Technology,2900.00,600.00,0.05,2023-02-18,
1015,BriteWave Marketing,SMB,South,Office Supplies,,95.00,0.10,2023-02-21,
1016,Frontier Logistics,Enterprise,West,Technology,21000.00,4900.00,0.00,2023-02-24,
1017,Quantum Consulting,Enterprise,West,Furniture,4200.00,-300.00,0.20,2023-02-27,
1018,BluePeak Systems,SMB,East,Technology,7800.00,1650.00,0.05,03/02/2023,
1019,Silverline Goods,Consumer,Central,Office Supplies,320.00,40.00,0.00,2023-03-05,
1020,Omni Global,Enterprise,West,Technology,27500.00,6300.00,0.00,2023-03-08,
1020,Omni Global,Enterprise,West,Technology,27500.00,6300.00,0.00,2023-03-08,`;

    const blob = new Blob([sampleCsv], { type: 'text/csv' });
    const sampleFile = new File([blob], 'sample_enterprise_sales.csv', { type: 'text/csv' });
    selectFile(sampleFile);
    setDatasetName('Enterprise Multi-Region Sales (Dirty)');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          Autonomous Ingestion & Health Engine
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
          Import Business Dataset
        </h2>
        <p className="text-slate-400 text-sm max-w-xl mx-auto mt-2">
          Upload any CSV or Excel file. The AI agent will inspect nulls, resolve anomalies with transparent audit logs, uncover correlations, and persist into SQLite.
        </p>
      </motion.div>

      <div className="bg-dark-card border border-dark-border rounded-2xl p-6 sm:p-8 shadow-2xl">
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-400" />
            <div>
              <p className="font-semibold text-xs uppercase tracking-wider">Ingestion Error</p>
              <p className="text-xs mt-1">{error}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleUpload} className="space-y-6">
          {/* Dropzone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all ${
              dragActive
                ? 'border-primary-500 bg-primary-500/10'
                : file
                ? 'border-emerald-500/50 bg-emerald-500/5'
                : 'border-dark-border hover:border-slate-600 bg-dark-surface/50 hover:bg-dark-surface'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={(e) => e.target.files?.[0] && selectFile(e.target.files[0])}
              className="hidden"
            />

            <div className="flex flex-col items-center">
              {file ? (
                <>
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center mb-4">
                    <FileSpreadsheet className="w-8 h-8" />
                  </div>
                  <p className="text-sm font-semibold text-white">{file.name}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    {(file.size / 1024).toFixed(1)} KB • Ready for automated profiling
                  </p>
                  <span className="mt-3 text-xs text-primary-400 underline font-medium">
                    Click to choose a different file
                  </span>
                </>
              ) : (
                <>
                  <div className="w-14 h-14 rounded-2xl bg-primary-600/15 text-primary-400 flex items-center justify-center mb-4">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <p className="text-sm font-semibold text-white">
                    Drag and drop your dataset here, or <span className="text-primary-400 underline">browse</span>
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Supports CSV, Excel (.xlsx, .xls) up to 50MB
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Dataset Name Field */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Dataset Name
            </label>
            <input
              type="text"
              required
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g. Q3 Sales & Performance"
              className="w-full bg-dark-surface border border-dark-border rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors"
            />
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <button
              type="button"
              onClick={loadSampleDataset}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <Database className="w-3.5 h-3.5 text-accent-cyan" />
              Load Sample Dirty Dataset (With Outliers & Nulls)
            </button>

            <button
              type="submit"
              disabled={!file || loading}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-primary-600 to-accent-emerald hover:from-primary-500 hover:to-accent-emerald text-white font-semibold text-xs tracking-wide shadow-lg shadow-primary-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Profile & Ingest Dataset
                </>
              )}
            </button>
          </div>
        </form>

        {/* Live Ingestion Steps Progress */}
        {loading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-6 pt-6 border-t border-dark-border"
          >
            <div className="flex items-center gap-3 text-xs text-primary-300 font-medium">
              <Loader2 className="w-4 h-4 animate-spin text-primary-400 shrink-0" />
              <span>{stage}</span>
            </div>
            <div className="w-full bg-dark-surface rounded-full h-1.5 mt-3 overflow-hidden">
              <div className="bg-gradient-to-r from-primary-500 to-accent-emerald h-full w-full animate-pulse" />
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};
