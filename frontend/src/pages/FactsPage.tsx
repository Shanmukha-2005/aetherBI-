import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Compass, Sparkles, TrendingUp, PieChart, AlertCircle, Zap, CheckCircle2 } from 'lucide-react';
import { api, DatasetFact } from '../api/client';

interface FactsPageProps {
  datasetId: number;
}

export const FactsPage: React.FC<FactsPageProps> = ({ datasetId }) => {
  const [facts, setFacts] = useState<DatasetFact[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFacts();
  }, [datasetId]);

  const loadFacts = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/datasets/${datasetId}/facts`);
      setFacts(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <div className="w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-slate-400">Analyzing variable correlations and uncovering unique facts...</p>
      </div>
    );
  }

  const getFactIcon = (type: string) => {
    switch (type) {
      case 'CORRELATION':
        return <TrendingUp className="w-4 h-4 text-emerald-400" />;
      case 'PARETO_80_20':
        return <PieChart className="w-4 h-4 text-amber-400" />;
      case 'DOMINANCE':
        return <Zap className="w-4 h-4 text-accent-cyan" />;
      case 'QUIRK':
      default:
        return <Sparkles className="w-4 h-4 text-violet-400" />;
    }
  };

  const getBadgeStyle = (type: string) => {
    switch (type) {
      case 'CORRELATION':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'PARETO_80_20':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'DOMINANCE':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'QUIRK':
      default:
        return 'bg-violet-500/15 text-violet-300 border-violet-500/30';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Hero Header */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-dark-card border border-dark-border rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden"
      >
        <div className="absolute -top-10 -right-10 w-72 h-72 bg-accent-violet/10 rounded-full blur-3xl pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-violet/15 border border-accent-violet/30 text-accent-violet text-xs font-semibold mb-3">
          <Compass className="w-3.5 h-3.5" />
          Statistical Profiling & Plain-English Discovery
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Related Variables & Unique Dataset Facts
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
          The statistical engine has analyzed the covariance matrix, checked for power-law distributions (Pareto 80/20), and highlighted the defining patterns in this dataset so you don't have to hunt for them.
        </p>
      </motion.div>

      {/* Facts Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {facts.length === 0 ? (
          <div className="col-span-full p-12 text-center bg-dark-card border border-dark-border rounded-2xl text-xs text-slate-400">
            No specific facts generated yet. Upload a larger dataset to uncover deep relationships!
          </div>
        ) : (
          facts.map((fact, index) => (
            <motion.div
              key={fact.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-dark-card border border-dark-border hover:border-slate-700 rounded-2xl p-6 shadow-md transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between gap-3 mb-4">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-dark-surface border border-dark-border group-hover:border-slate-600 transition-colors">
                      {getFactIcon(fact.fact_type)}
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      {fact.fact_type.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {fact.metric_value && (
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold border ${getBadgeStyle(fact.fact_type)}`}>
                      {fact.metric_value}
                    </span>
                  )}
                </div>

                <h3 className="text-sm sm:text-base font-bold text-white group-hover:text-primary-300 transition-colors">
                  {fact.title}
                </h3>
                <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                  {fact.description}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t border-dark-border/60 flex items-center gap-1.5 text-[11px] text-slate-400 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                Verified Statistical Finding
              </div>
            </motion.div>
          ))
        )}
      </div>

    </div>
  );
};
