import React from 'react';
import { Sparkles, Database, LogOut, ChevronDown, Check } from 'lucide-react';
import { User, DatasetSummary } from '../../api/client';

interface NavbarProps {
  user: User | null;
  datasets: DatasetSummary[];
  selectedDataset: DatasetSummary | null;
  onSelectDataset: (ds: DatasetSummary) => void;
  onLogout: () => void;
  onOpenUpload: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  datasets,
  selectedDataset,
  onSelectDataset,
  onLogout,
  onOpenUpload,
}) => {
  const [dropdownOpen, setDropdownOpen] = React.useState(false);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-dark-border bg-dark-bg/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary-600 to-accent-emerald flex items-center justify-center shadow-lg shadow-primary-500/20">
            <Sparkles className="w-5 h-5 text-white animate-pulse-subtle" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                AetherBI
              </span>
              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-primary-500/10 text-primary-400 border border-primary-500/20">
                SQLite Edition
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Business Intelligence Agent</p>
          </div>
        </div>

        {/* Dataset Selector Dropdown */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-dark-border bg-dark-card hover:bg-dark-surface text-sm transition-all text-slate-200"
            >
              <Database className="w-4 h-4 text-primary-400" />
              <span className="font-medium max-w-[160px] truncate">
                {selectedDataset ? selectedDataset.name : 'Select Dataset'}
              </span>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl border border-dark-border bg-dark-card shadow-2xl p-1.5 z-50 animate-in fade-in zoom-in-95">
                <div className="px-3 py-2 text-xs font-semibold uppercase text-slate-400 tracking-wider">
                  Your Datasets ({datasets.length})
                </div>
                <div className="max-h-60 overflow-y-auto space-y-1">
                  {datasets.length === 0 ? (
                    <div className="p-3 text-xs text-slate-400 text-center">
                      No datasets yet. Upload one!
                    </div>
                  ) : (
                    datasets.map((ds) => (
                      <button
                        key={ds.id}
                        onClick={() => {
                          onSelectDataset(ds);
                          setDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-lg transition-colors ${
                          selectedDataset?.id === ds.id
                            ? 'bg-primary-500/15 text-primary-300 font-medium'
                            : 'text-slate-300 hover:bg-dark-surface'
                        }`}
                      >
                        <div className="truncate text-left">
                          <p className="truncate">{ds.name}</p>
                          <span className="text-[10px] text-slate-400">
                            {ds.row_count} rows • {ds.health_score}% health
                          </span>
                        </div>
                        {selectedDataset?.id === ds.id && (
                          <Check className="w-3.5 h-3.5 text-primary-400 ml-2 shrink-0" />
                        )}
                      </button>
                    ))
                  )}
                </div>
                <div className="pt-2 border-t border-dark-border mt-1">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onOpenUpload();
                    }}
                    className="w-full py-1.5 px-3 rounded-lg text-xs font-medium bg-primary-600 hover:bg-primary-500 text-white transition-all text-center flex items-center justify-center gap-1"
                  >
                    + Upload New Dataset
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* User Profile & Logout */}
          {user && (
            <div className="flex items-center gap-3 border-l border-dark-border pl-4">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-semibold text-slate-200">{user.name}</p>
                <p className="text-[10px] text-slate-400 truncate max-w-[120px]">{user.email}</p>
              </div>
              <button
                onClick={onLogout}
                title="Log Out"
                className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

      </div>
    </header>
  );
};
