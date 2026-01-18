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
    metrics: any;
}

export const Charts = ({ metrics }: ChartsProps) => {
    if (!metrics) return null;

    const basic = metrics.basic_stats || {};
    const farming = metrics.laning_phase || {};

    // Prepare data for bar charts
    const farmingData = [
        { name: 'GPM', value: basic.gpm || 0, fill: '#14b8a6' },
        { name: 'XPM', value: basic.xpm || 0, fill: '#2dd4bf' },
        { name: 'Last Hits', value: basic.lh || 0, fill: '#5eead4' },
    ];

    const fightingData = [
        { name: 'Kills', value: basic.kills || 0, fill: '#22c55e' },
        { name: 'Deaths', value: basic.deaths || 0, fill: '#ef4444' },
        { name: 'Assists', value: basic.assists || 0, fill: '#3b82f6' },
    ];

    // RADAR CHART: Using MatchMentor Unique Scores
    const radarData = [
        { subject: 'Combat Efficiency', value: getScore(metrics.fight_effectiveness), fullMark: 100 },
        { subject: 'Strategy & Positioning', value: getScore(metrics.positioning_risk), fullMark: 100 },
        { subject: 'Decision Making', value: getScore(metrics.decision_quality), fullMark: 100 },
        { subject: 'Threat Prediction', value: getScore(metrics.threat_prediction), fullMark: 100 },
        { subject: 'Psychology & Tilt', value: getScore(metrics.psychological_profile), fullMark: 100 },
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
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700/30">
                    <h3 className="text-lg font-semibold mb-6 text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        Economic Intensity
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={farmingData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={{ stroke: '#4b5563' }} />
                            <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={{ stroke: '#4b5563' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="value" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700/30">
                    <h3 className="text-lg font-semibold mb-6 text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        Combat Participation
                    </h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={fightingData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={{ stroke: '#4b5563' }} />
                            <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={{ stroke: '#4b5563' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="value" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="bg-gray-800 rounded-xl p-8 border border-gray-700/30 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4">
                    <span className="text-[10px] font-black text-teal-400/30 uppercase tracking-[0.2em]">MatchMentor Strategic Radar v2.0</span>
                </div>
                <h3 className="text-xl font-bold mb-8 text-white flex items-center gap-3">
                    <svg className="w-6 h-6 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                    Strategic Performance Signature
                </h3>
                <ResponsiveContainer width="100%" height={400}>
                    <RadarChart data={radarData}>
                        <PolarGrid stroke="#374151" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 13, fontWeight: 'bold' }} />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar
                            name="Skill Rating"
                            dataKey="value"
                            stroke="#14b8a6"
                            fill="#14b8a6"
                            fillOpacity={0.4}
                            strokeWidth={3}
                            animationBegin={500}
                            animationDuration={1500}
                        />
                        <Tooltip content={<CustomTooltip />} />
                    </RadarChart>
                </ResponsiveContainer>
                <div className="mt-4 text-center">
                    <p className="text-gray-500 text-sm">Our proprietary radar analyzes 48 high-dimensional metrics to determine your true skill signature.</p>
                </div>
            </div>
        </div>
    );
};

function getScore(group: any): number {
    if (!group) return 0;
    // Calculate average of the group if it contains scores
    const values = Object.values(group).filter(v => typeof v === 'number');
    if (values.length === 0) return 0;
    // If it's a score group, just return the avg
    return Math.round(values.reduce((a: number, b: any) => a + b, 0) / values.length);
}

export default Charts;
