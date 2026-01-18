import type { ReactNode } from 'react';

interface MetricsDisplayProps {
    metrics: any;
}

interface MetricDefinition {
    key: string;
    label: string;
    isTime?: boolean;
    isPercent?: boolean;
    isScore?: boolean;
}

interface MetricGroupDef {
    id: string;
    title: string;
    icon: ReactNode;
    metrics: MetricDefinition[];
}

export const MetricsDisplay = ({ metrics }: MetricsDisplayProps) => {
    if (!metrics) return null;

    const metricGroups: MetricGroupDef[] = [
        {
            id: 'laning_phase',
            title: 'Laning Phase (0-10m)',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
            metrics: [
                { key: 'lh_at_10', label: 'Last Hits @ 10m' },
                { key: 'gold_at_10', label: 'Gold @ 10m' },
                { key: 'xp_at_10', label: 'XP @ 10m' },
                { key: 'deaths_in_lane', label: 'Lane Deaths' },
            ],
        },
        {
            id: 'basic_stats',
            title: 'Farming & Economy',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
            metrics: [
                { key: 'gpm', label: 'GPM' },
                { key: 'xpm', label: 'XPM' },
                { key: 'lh', label: 'Total Last Hits' },
                { key: 'kd_ratio', label: 'K/D Ratio' },
            ],
        },
        {
            id: 'fight_effectiveness',
            title: 'Combat Effectiveness',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
            metrics: [
                { key: 'damage_efficiency', label: 'Damage Efficiency', isScore: true },
                { key: 'kill_securing', label: 'Kill Securing Rate', isPercent: true },
                { key: 'stun_follow_up', label: 'Crowd Control Value', isScore: true },
                { key: 'ultimate_value', label: 'Ult Strategy Rating', isScore: true },
            ],
        },
        {
            id: 'positioning_risk',
            title: 'Strategic Positioning',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L16 4m0 13V4m-6 3L16 4" /></svg>,
            metrics: [
                { key: 'lane_safety', label: 'Lane Navigation', isScore: true },
                { key: 'gank_vulnerability', label: 'Threat Awareness', isScore: true },
                { key: 'fight_position', label: 'Fight Spacing', isScore: true },
                { key: 'rotation_timing', label: 'Map Presence', isScore: true },
            ],
        },
        {
            id: 'vision',
            title: 'Vision & Map Control',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>,
            metrics: [
                { key: 'obs_placed', label: 'Observers Placed' },
                { key: 'sen_placed', label: 'Sentries Placed' },
                { key: 'vision_score', label: 'Vision Power Score', isScore: true },
                { key: 'deward_count', label: 'Deward Prowess' },
            ],
        },
        {
            id: 'decision_quality',
            title: 'Tactical Intelligence',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>,
            metrics: [
                { key: 'item_efficiency', label: 'Gold Value Util.', isPercent: true },
                { key: 'timing_vs_avg', label: 'Power Spike Timing', isScore: true },
                { key: 'objective_focus', label: 'Objective Priority', isScore: true },
                { key: 'recovery_prowess', label: 'Comeback Potential', isScore: true },
            ],
        },
        {
            id: 'threat_prediction',
            title: 'Prediction & Defense',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>,
            metrics: [
                { key: 'gank_survival', label: 'Gank Resilience', isPercent: true },
                { key: 'smoke_detection', label: 'Anti-Smoke Awareness', isScore: true },
                { key: 'enemy_cd_tracking', label: 'CD Tracking Skill', isScore: true },
                { key: 'rosh_awareness', label: 'Roshan Control', isScore: true },
            ],
        },
        {
            id: 'psychological_profile',
            title: 'Psychological Analysis',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M12 12h.01M12 12h-.01M12 12h.01M12 12h-.01" /></svg>,
            metrics: [
                { key: 'tilt_resistance', label: 'Tactical Stability', isScore: true },
                { key: 'consistency_score', label: 'Perf. Consistency', isScore: true },
                { key: 'pressure_performance', label: 'Clutch Power', isScore: true },
                { key: 'game_discipline', label: 'Strategic Focus', isScore: true },
            ],
        },
        {
            id: 'stat_correlations',
            title: 'Efficiency Correlations',
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>,
            metrics: [
                { key: 'farm_damage_link', label: 'Gold-to-Damage', isScore: true },
                { key: 'death_impact_cost', label: 'Death Impact Penalty', isScore: true },
                { key: 'vision_farm_efficiency', label: 'Vision-Value Ratio', isPercent: true },
                { key: 'gold_win_probability', label: 'Win Conversion', isPercent: true },
            ],
        }
    ];

    const formatValue = (value: any, definition: MetricDefinition): string => {
        if (value === undefined || value === null) return '-';
        let val = typeof value === 'object' ? value.score : value;
        if (typeof val !== 'number') return String(val);

        if (val === 0 && (definition.key.includes('timing') || definition.key.includes('blink'))) return '-';

        if (definition.isTime) {
            const mins = Math.floor(val / 60);
            const secs = Math.floor(val % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }
        if (definition.isPercent) {
            return `${(val * 100).toFixed(0)}%`;
        }
        if (definition.isScore) {
            return `${val.toFixed(0)}/100`;
        }
        return val.toLocaleString(undefined, { maximumFractionDigits: (val < 10) ? 2 : 1 });
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {metricGroups.map((group) => {
                const groupData = metrics[group.id];
                if (!groupData) return null;

                const visibleMetrics = group.metrics.filter(m => {
                    const val = groupData[m.key];
                    if (m.key.includes('timing') && (val === 0 || !val)) return false;
                    return true;
                });

                if (visibleMetrics.length === 0) return null;

                return (
                    <div key={group.id} className="bg-gray-800 border border-gray-700/50 rounded-2xl p-6 hover:bg-gray-800/80 transition-all hover:border-gray-600 shadow-xl group/card">
                        <div className="flex items-center gap-3 mb-6 border-b border-gray-700/50 pb-4">
                            <div className="w-10 h-10 bg-teal-500/10 rounded-xl flex items-center justify-center text-teal-400 border border-teal-500/20 group-hover/card:scale-110 transition-transform">
                                {group.icon}
                            </div>
                            <h3 className="text-lg font-bold text-white tracking-tight">{group.title}</h3>
                        </div>
                        <div className="space-y-6">
                            {visibleMetrics.map((metric) => {
                                const val = groupData[metric.key];
                                return (
                                    <div key={metric.key} className="flex flex-col gap-2">
                                        <div className="flex items-center justify-between">
                                            <p className="text-gray-400 text-[10px] font-bold uppercase tracking-widest">{metric.label}</p>
                                            <p className={`text-xl font-black ${typeof val === 'number' && val >= 0 ? 'text-teal-400' : 'text-gray-500'}`}>
                                                {formatValue(val, metric)}
                                            </p>
                                        </div>
                                        {metric.isScore && typeof val === 'number' && (
                                            <div className="w-full h-1 bg-gray-900/50 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full ${val > 75 ? 'bg-teal-400 shadow-[0_0_8px_teal]' : val > 50 ? 'bg-yellow-400' : 'bg-red-500'} transition-all duration-1000`}
                                                    style={{ width: `${val}%` }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default MetricsDisplay;
