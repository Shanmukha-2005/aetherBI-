import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, CheckCircle, Wrench, AlertTriangle, Table, Search, Sparkles, Filter, FileText, Download, Loader2 } from 'lucide-react';
import { api, DatasetDetail, RemediationLog, downloadExecutivePDF } from '../api/client';

interface DataHealthPageProps {
  datasetId: number;
  datasetName?: string;
}

export const DataHealthPage: React.FC<DataHealthPageProps> = ({ datasetId, datasetName }) => {
  const [detail, setDetail] = useState<DatasetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadDetail();
  }, [datasetId]);

  const loadDetail = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/datasets/${datasetId}`);
      setDetail(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      await downloadExecutivePDF(datasetId, detail?.name || datasetName || 'Dataset');
    } catch (err) {
      console.error('Failed to download executive PDF report:', err);
    } finally {
      setDownloadingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <div className="w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-slate-400">Loading data health audit & remediation logs...</p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-slate-400 text-sm">
        Dataset details could not be found.
      </div>
    );
  }

  const logs = detail.remediation_logs || [];
  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.column_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.issue_description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.resolution_strategy.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (filterType === 'ALL') return matchesSearch;
    if (filterType === 'IMPUTATION') return matchesSearch && log.resolution_strategy.includes('IMPUTATION');
    if (filterType === 'SCHEMA') return matchesSearch && (log.resolution_strategy.includes('NORMALIZATION') || log.resolution_strategy.includes('DROPPED'));
    if (filterType === 'DATES') return matchesSearch && log.issue_type.includes('DATE');
    return matchesSearch;
  });

  const healthColor =
    detail.health_score >= 85
      ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
      : detail.health_score >= 65
      ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
      : 'text-rose-400 border-rose-500/30 bg-rose-500/10';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Hero Health Banner */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-dark-card border border-dark-border rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 w-80 h-80 bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-xs font-semibold mb-3">
              <ShieldCheck className="w-3.5 h-3.5" />
              Automated Data Health & Remediation Engine
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {detail.name}
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
              The dataset has been parsed, audited for anomalies, and automatically repaired using statistical best practices. All changes are permanently preserved in SQLite table <code className="text-primary-300 bg-dark-surface px-1.5 py-0.5 rounded text-xs">{detail.physical_table_name}</code>.
            </p>
          </div>

          {/* Health Index Meter & Download PDF */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            <div className="flex items-center gap-4 bg-dark-surface/60 border border-dark-border p-4 rounded-xl">
              <div className={`w-16 h-16 rounded-2xl border-2 flex flex-col items-center justify-center font-bold text-xl ${healthColor}`}>
                <span>{detail.health_score.toFixed(0)}%</span>
                <span className="text-[9px] uppercase font-semibold">Health</span>
              </div>
              <div>
                <p className="text-xs font-semibold text-white">Quality Index</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {logs.length} automated fixes applied
                </p>
                <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-medium mt-1">
                  <CheckCircle className="w-3 h-3" /> SQLite Query Ready
                </span>
              </div>
            </div>

            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-500 hover:to-indigo-500 text-white font-medium text-xs tracking-wide shadow-lg shadow-indigo-600/20 transition-all border border-indigo-400/20 disabled:opacity-50 cursor-pointer"
            >
              {downloadingPdf ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span>Generating PDF...</span>
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 text-white" />
                  <span>Download PDF Dossier</span>
                  <Download className="w-3.5 h-3.5 text-indigo-200" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-dark-border">
          <div className="p-3 bg-dark-surface/40 rounded-xl border border-dark-border/60">
            <p className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">Cleaned Rows</p>
            <p className="text-lg font-bold text-white mt-0.5">{detail.row_count.toLocaleString()}</p>
          </div>
          <div className="p-3 bg-dark-surface/40 rounded-xl border border-dark-border/60">
            <p className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">Active Columns</p>
            <p className="text-lg font-bold text-white mt-0.5">{detail.column_count}</p>
          </div>
          <div className="p-3 bg-dark-surface/40 rounded-xl border border-dark-border/60">
            <p className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">Repairs Applied</p>
            <p className="text-lg font-bold text-accent-emerald mt-0.5">{logs.length}</p>
          </div>
          <div className="p-3 bg-dark-surface/40 rounded-xl border border-dark-border/60">
            <p className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">Source File</p>
            <p className="text-xs font-medium text-slate-300 mt-1 truncate">{detail.original_filename}</p>
          </div>
        </div>
      </motion.div>

      {/* Remediation Audit Logs (Requirement 1) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Wrench className="w-4 h-4 text-primary-400" />
              Transparent Remediation Audit Log
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Exact issues detected and the automated strategy applied to solve each one.
            </p>
          </div>

          {/* Filters & Search */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search audit fixes..."
                className="bg-dark-card border border-dark-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="flex rounded-lg bg-dark-card border border-dark-border p-1 text-xs">
              {(['ALL', 'IMPUTATION', 'SCHEMA', 'DATES'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t)}
                  className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                    filterType === t ? 'bg-primary-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Audit Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredLogs.length === 0 ? (
            <div className="col-span-2 p-8 text-center bg-dark-card border border-dark-border rounded-xl text-xs text-slate-400">
              No remediation logs match your current filter.
            </div>
          ) : (
            filteredLogs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-dark-card border border-dark-border hover:border-slate-700 rounded-xl p-5 shadow-sm transition-all"
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-primary-500/15 text-primary-300 border border-primary-500/25">
                      {log.column_name}
                    </span>
                    <span className="text-[10px] uppercase font-semibold text-slate-400">
                      {log.issue_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    {log.resolution_strategy.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="text-xs text-slate-300 flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <span><strong className="text-slate-200">Anomaly Found:</strong> {log.issue_description}</span>
                  </div>
                  <div className="text-xs text-slate-300 flex items-start gap-2 bg-dark-surface/60 p-2.5 rounded-lg border border-dark-border/80">
                    <Sparkles className="w-3.5 h-3.5 text-accent-cyan shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-accent-cyan text-[11px]">How it was solved:</p>
                      <p className="text-slate-300 mt-0.5 leading-relaxed text-[11px]">{log.resolution_details}</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* Cleaned Dataset Preview */}
      <div className="bg-dark-card border border-dark-border rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Table className="w-4 h-4 text-primary-400" />
              Cleaned Dataset Preview (First 10 Rows from SQLite)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Reflects all standardized headers, imputed values, and ISO formatted dates.
            </p>
          </div>
        </div>

        {detail.sample_data && detail.sample_data.length > 0 ? (
          <div className="overflow-x-auto border border-dark-border rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-dark-surface border-b border-dark-border text-slate-300">
                  {Object.keys(detail.sample_data[0]).map((key) => (
                    <th key={key} className="px-4 py-3 font-semibold text-slate-300 whitespace-nowrap">
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border text-slate-300">
                {detail.sample_data.map((row, idx) => (
                  <tr key={idx} className="hover:bg-dark-surface/50 transition-colors">
                    {Object.values(row).map((val: any, cIdx) => (
                      <td key={cIdx} className="px-4 py-2.5 whitespace-nowrap font-mono text-[11px] text-slate-300">
                        {val === null || val === undefined ? (
                          <span className="text-slate-500 italic">null</span>
                        ) : typeof val === 'number' ? (
                          val.toLocaleString()
                        ) : (
                          String(val)
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-500">
            No sample records available.
          </div>
        )}
      </div>

    </div>
  );
};
