import React from 'react';
import { motion } from 'framer-motion';
import { LayoutDashboard, ShieldCheck, Compass, TerminalSquare, UploadCloud } from 'lucide-react';

export type TabType = 'dashboard' | 'health' | 'facts' | 'sql' | 'upload';

interface TabsProps {
  activeTab: TabType;
  onChangeTab: (tab: TabType) => void;
  hasDataset: boolean;
  healthScore?: number;
}

export const Tabs: React.FC<TabsProps> = ({ activeTab, onChangeTab, hasDataset, healthScore }) => {
  const tabs = [
    { id: 'dashboard', label: 'Auto-Dashboard', icon: LayoutDashboard, disabled: !hasDataset },
    {
      id: 'health',
      label: 'Data Health & Fixes',
      icon: ShieldCheck,
      badge: healthScore !== undefined ? `${healthScore}%` : undefined,
      badgeColor: healthScore && healthScore >= 80 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300',
      disabled: !hasDataset,
    },
    { id: 'facts', label: 'Relationships & Facts', icon: Compass, disabled: !hasDataset },
    { id: 'sql', label: 'NL → SQLite Studio', icon: TerminalSquare, disabled: !hasDataset },
    { id: 'upload', label: 'Upload Data', icon: UploadCloud, disabled: false },
  ];

  return (
    <div className="border-b border-dark-border bg-dark-bg/60 backdrop-blur-sm sticky top-16 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex space-x-1 sm:space-x-2 py-2 overflow-x-auto no-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                disabled={tab.disabled}
                onClick={() => onChangeTab(tab.id as TabType)}
                className={`relative flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all shrink-0 ${
                  tab.disabled
                    ? 'opacity-40 cursor-not-allowed text-slate-500'
                    : isActive
                    ? 'text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-dark-card/50'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTabBadge"
                    className="absolute inset-0 bg-primary-600/20 border border-primary-500/40 rounded-lg shadow-sm"
                    transition={{ type: 'spring', bounce: 0.2, duration: 0.5 }}
                  />
                )}
                <Icon className={`w-4 h-4 relative z-10 ${isActive ? 'text-primary-400' : 'text-slate-400'}`} />
                <span className="relative z-10">{tab.label}</span>
                {tab.badge && (
                  <span className={`relative z-10 text-[10px] font-bold px-1.5 py-0.2 rounded-full ${tab.badgeColor}`}>
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
};
