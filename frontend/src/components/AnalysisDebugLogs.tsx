import React from 'react';

interface LogEntry {
    timestamp: number;
    step: string;
    level: string;
    message: string;
    data: any;
}

interface AnalysisLogsProps {
    logs?: {
        total_duration: number;
        data_sources: Record<string, string>;
        trace: LogEntry[];
    };
}

const AnalysisDebugLogs: React.FC<AnalysisLogsProps> = ({ logs }) => {
    if (!logs) {
        return (
            <div className="p-8 text-center text-gray-400 bg-gray-900 rounded-xl border border-gray-800">
                <p>No analysis logs available for this match.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fadeIn">
            {/* Summary Header */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-gray-900 rounded-xl border border-gray-800">
                    <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Analysis Stats</h4>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-300">Total duration:</span>
                        <span className="text-indigo-400 font-mono">{(logs.total_duration || 0).toFixed(2)}s</span>
                    </div>
                </div>

                <div className="p-4 bg-gray-900 rounded-xl border border-gray-800">
                    <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Data Sources</h4>
                    <div className="space-y-1">
                        {Object.entries(logs.data_sources || {}).map(([comp, source]) => (
                            <div key={comp} className="flex justify-between items-center text-sm">
                                <span className="text-gray-400">{comp}:</span>
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${source.includes('clarity') ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'
                                    }`}>
                                    {source}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Trace Timeline */}
            <div className="bg-black/40 rounded-xl border border-gray-800 overflow-hidden">
                <div className="p-4 border-b border-gray-800 bg-gray-900/50 flex justify-between items-center">
                    <h3 className="font-semibold text-white">Analysis Trace</h3>
                    <span className="text-xs text-gray-500">{logs.trace?.length || 0} events</span>
                </div>

                <div className="divide-y divide-gray-800 overflow-y-auto max-h-[500px] scrollbar-thin scrollbar-thumb-gray-700">
                    {(logs.trace || []).map((entry, idx) => (
                        <div key={idx} className="p-3 hover:bg-gray-800/20 transition-colors">
                            <div className="flex items-start gap-4">
                                <div className="w-16 flex-shrink-0 text-[10px] font-mono text-gray-500 pt-1">
                                    +{entry.timestamp.toFixed(3)}s
                                </div>

                                <div className="flex-grow">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${entry.level === 'ERROR' ? 'bg-red-900/40 text-red-400' :
                                                entry.level === 'WARNING' ? 'bg-yellow-900/40 text-yellow-400' :
                                                    'bg-gray-700 text-gray-300'
                                            }`}>
                                            {entry.step}
                                        </span>
                                        <span className="text-sm text-gray-200">{entry.message}</span>
                                    </div>

                                    {entry.data && Object.keys(entry.data).length > 0 && (
                                        <pre className="mt-2 p-2 bg-black/60 rounded text-[11px] font-mono text-gray-400 overflow-x-auto border border-gray-700/50">
                                            {JSON.stringify(entry.data, null, 2)}
                                        </pre>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="p-4 bg-indigo-900/10 rounded-lg border border-indigo-900/20">
                <p className="text-xs text-indigo-300">
                    <span className="font-bold">Pro Tip:</span> This trace shows exactly how Antigravity processed your match. Look for "Clarity" data sources to ensure maximum precision from real replay data.
                </p>
            </div>
        </div>
    );
};

export default AnalysisDebugLogs;
