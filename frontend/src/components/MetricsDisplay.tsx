import type { ReactNode } from 'react';

interface MetricsDisplayProps {
    metrics: Record<string, number | string | undefined>;
}

interface MetricGroup {
    title: string;
    icon: ReactNode;
    metrics: { key: string; label: string }[];
}

export const MetricsDisplay = ({ metrics }: MetricsDisplayProps) => {
    const metricGroups: MetricGroup[] = [
        {
            title: 'Farming',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
            metrics: [
                { key: 'gpm', label: 'GPM' },
                { key: 'xpm', label: 'XPM' },
                { key: 'last_hits', label: 'Last Hits' },
            ],
        },
        {
            title: 'Fighting',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
            ),
            metrics: [
                { key: 'kills', label: 'Kills' },
                { key: 'deaths', label: 'Deaths' },
                { key: 'assists', label: 'Assists' },
                { key: 'damage', label: 'Hero Damage' },
            ],
        },
        {
            title: 'Positioning',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
            ),
            metrics: [
                { key: 'position_safety', label: 'Position Safety' },
                { key: 'teamfight_participation', label: 'Teamfight %' },
            ],
        },
    ];

    const formatValue = (value: number | string | undefined): string => {
        if (value === undefined || value === null) return '-';
        if (typeof value === 'number') {
            return value.toLocaleString();
        }
        return String(value);
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {metricGroups.map((group) => (
                <div key={group.title} className="bg-gray-800 rounded-xl p-6 hover:bg-gray-800/80 transition-colors">
                    <div className="flex items-center gap-3 mb-5">
                        <div className="w-10 h-10 bg-teal-500/20 rounded-lg flex items-center justify-center text-teal-400">
                            {group.icon}
                        </div>
                        <h3 className="text-lg font-semibold text-white">{group.title}</h3>
                    </div>
                    <div className="space-y-4">
                        {group.metrics.map((metric) => (
                            <div key={metric.key} className="flex items-center justify-between">
                                <p className="text-gray-400 text-sm">{metric.label}</p>
                                <p className="text-xl font-bold text-teal-400">
                                    {formatValue(metrics[metric.key])}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default MetricsDisplay;
