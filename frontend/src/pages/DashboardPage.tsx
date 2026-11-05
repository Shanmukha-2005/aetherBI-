import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { LayoutDashboard, Calendar, Layers, Activity, DollarSign, TrendingUp, FileText, Download, Loader2 } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { api, DashboardResponse, downloadExecutivePDF } from '../api/client';

interface DashboardPageProps {
  datasetId: number;
  datasetName?: string;
}

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6', '#ec4899', '#3b82f6'];

export const DashboardPage: React.FC<DashboardPageProps> = ({ datasetId, datasetName }) => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  useEffect(() => {
    loadDashboard();
  }, [datasetId]);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/dashboard/${datasetId}`);
      setData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      await downloadExecutivePDF(datasetId, datasetName || 'Dataset');
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
        <p className="text-xs text-slate-400">Pre-aggregating dashboard metrics & charts from SQLite...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-slate-400 text-sm">
        Dashboard data could not be computed.
      </div>
    );
  }

  const { kpis, charts } = data;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

      {/* Executive Header Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-dark-card border border-dark-border rounded-2xl p-5 shadow-lg">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5 text-primary-400" />
            Executive Analytics & Intelligence Hub
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time aggregates pre-computed from SQLite Write-Ahead Log table.
          </p>
        </div>

        <button
          onClick={handleDownloadPdf}
          disabled={downloadingPdf}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-500 hover:to-indigo-500 text-white font-medium text-xs tracking-wide shadow-lg shadow-indigo-600/20 transition-all border border-indigo-400/20 disabled:opacity-50 shrink-0 self-start sm:self-auto cursor-pointer"
        >
          {downloadingPdf ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              Generating Executive PDF...
            </>
          ) : (
            <>
              <FileText className="w-4 h-4 text-white" />
              Download Executive Dossier (PDF)
              <Download className="w-3.5 h-3.5 text-indigo-200" />
            </>
          )}
        </button>
      </div>
      
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-dark-card border border-dark-border rounded-2xl p-5 shadow-sm"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Records</span>
            <Layers className="w-4 h-4 text-primary-400" />
          </div>
          <p className="text-2xl font-bold text-white">{kpis.total_rows.toLocaleString()}</p>
          <p className="text-[11px] text-slate-400 mt-1">Ingested in SQLite</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-dark-card border border-dark-border rounded-2xl p-5 shadow-sm"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Data Health</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400">{kpis.health_score.toFixed(0)}%</p>
          <p className="text-[11px] text-slate-400 mt-1">Quality & Completeness</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-dark-card border border-dark-border rounded-2xl p-5 shadow-sm"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Attributes</span>
            <LayoutDashboard className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white">{kpis.total_cols}</p>
          <p className="text-[11px] text-slate-400 mt-1">Standardized Columns</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-dark-card border border-dark-border rounded-2xl p-5 shadow-sm"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Date Timeline</span>
            <Calendar className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-sm font-bold text-white truncate mt-1">
            {kpis.date_min && kpis.date_max ? `${kpis.date_min} → ${kpis.date_max}` : 'Static Tabular'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Detected Range</p>
        </motion.div>
      </div>

      {/* Numeric Aggregations Carousel/Cards */}
      {kpis.numeric_summaries && kpis.numeric_summaries.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.numeric_summaries.map((num, i) => (
            <div key={i} className="bg-dark-surface/50 border border-dark-border/80 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-300 truncate">{num.column}</p>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xs text-slate-400">Total Sum:</span>
                <span className="text-sm font-bold text-white font-mono">{num.sum_val.toLocaleString()}</span>
              </div>
              <div className="mt-1 flex items-baseline justify-between text-[11px] text-slate-400">
                <span>Avg: {num.avg_val.toLocaleString()}</span>
                <span>Max: {num.max_val.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {charts.map((chart) => (
          <motion.div
            key={chart.id}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-dark-card border border-dark-border rounded-2xl p-6 shadow-xl"
          >
            <h3 className="text-sm font-bold text-white mb-6 flex items-center justify-between">
              <span>{chart.title}</span>
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-dark-surface text-slate-400 border border-dark-border">
                {chart.chart_type}
              </span>
            </h3>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                {chart.chart_type === 'bar' || chart.chart_type === 'histogram' ? (
                  <BarChart data={chart.data} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey={chart.x_key} stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Bar dataKey={chart.y_key} fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                ) : chart.chart_type === 'line' ? (
                  <LineChart data={chart.data} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey={chart.x_key} stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Line type="monotone" dataKey={chart.y_key} stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                ) : chart.chart_type === 'pie' ? (
                  <PieChart>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Pie
                      data={chart.data}
                      dataKey={chart.y_key}
                      nameKey={chart.x_key}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={4}
                    >
                      {chart.data.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                ) : null}
              </ResponsiveContainer>
            </div>
          </motion.div>
        ))}
      </div>

    </div>
  );
};
