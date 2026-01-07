import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
} from 'recharts';

interface ChartsProps {
    metrics: Record<string, number | undefined>;
}

export const Charts = ({ metrics }: ChartsProps) => {
    // Prepare data for bar charts
    const farmingData = [
        { name: 'GPM', value: metrics.gpm || 0, fill: '#14b8a6' },
        { name: 'XPM', value: metrics.xpm || 0, fill: '#2dd4bf' },
        { name: 'Last Hits', value: metrics.last_hits || 0, fill: '#5eead4' },
    ];

    const fightingData = [
        { name: 'Kills', value: metrics.kills || 0, fill: '#22c55e' },
        { name: 'Deaths', value: metrics.deaths || 0, fill: '#ef4444' },
        { name: 'Assists', value: metrics.assists || 0, fill: '#3b82f6' },
    ];

    // Prepare data for radar chart (normalized to 100)
    const radarData = [
        { subject: 'Farming', value: normalizeValue(metrics.gpm, 800), fullMark: 100 },
        { subject: 'Fighting', value: normalizeValue(metrics.kills, 15), fullMark: 100 },
        { subject: 'Survival', value: normalizeValue(10 - (metrics.deaths || 0), 10), fullMark: 100 },
        { subject: 'Support', value: normalizeValue(metrics.assists, 20), fullMark: 100 },
        { subject: 'Objective', value: normalizeValue(metrics.last_hits, 400), fullMark: 100 },
    ];

    const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 shadow-lg">
                    <p className="text-gray-300 font-medium">{label}</p>
                    <p className="text-teal-400 font-bold">{payload[0].value.toLocaleString()}</p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="space-y-8 mb-8">
            {/* Bar Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Farming Stats */}
                <div className="bg-gray-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-6 text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Farming Stats
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={farmingData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="name" tick={{ fill: '#9ca3af' }} axisLine={{ stroke: '#4b5563' }} />
                            <YAxis tick={{ fill: '#9ca3af' }} axisLine={{ stroke: '#4b5563' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="value" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Fighting Stats */}
                <div className="bg-gray-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-6 text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Fighting Stats
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={fightingData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="name" tick={{ fill: '#9ca3af' }} axisLine={{ stroke: '#4b5563' }} />
                            <YAxis tick={{ fill: '#9ca3af' }} axisLine={{ stroke: '#4b5563' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="value" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Radar Chart */}
            <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-6 text-white flex items-center gap-2">
                    <svg className="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    Performance Overview
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                    <RadarChart data={radarData}>
                        <PolarGrid stroke="#374151" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#6b7280' }} />
                        <Radar
                            name="Performance"
                            dataKey="value"
                            stroke="#14b8a6"
                            fill="#14b8a6"
                            fillOpacity={0.3}
                            strokeWidth={2}
                        />
                    </RadarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

// Helper function to normalize values to 0-100 scale
function normalizeValue(value: number | undefined, max: number): number {
    if (value === undefined) return 0;
    return Math.min(100, Math.round((value / max) * 100));
}

export default Charts;
