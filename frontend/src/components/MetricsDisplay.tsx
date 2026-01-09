import type { ReactNode } from 'react';

interface MetricsDisplayProps {
    metrics: Record<string, number | string | undefined>;
}

interface MetricGroup {
    title: string;
    icon: ReactNode;
    metrics: { key: string; label: string; proKey?: string; isTime?: boolean }[];
}

export const MetricsDisplay = ({ metrics }: MetricsDisplayProps) => {
    const metricGroups: MetricGroup[] = [
        {
            title: 'Laning Phase (0-10m)',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
            ),
            metrics: [
                { key: 'lh_at_10', label: 'Last Hits @ 10m', proKey: 'pro_avg_lh_10' },
                { key: 'gold_at_10', label: 'Gold @ 10m' },
                { key: 'xp_at_10', label: 'XP @ 10m' },
                { key: 'deaths_in_lane', label: 'Lane Deaths' },
            ],
        },
        {
            title: 'Farming & Economy',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
            metrics: [
                { key: 'gpm', label: 'GPM', proKey: 'pro_avg_gpm' },
                { key: 'xpm', label: 'XPM', proKey: 'pro_avg_xpm' },
                { key: 'last_hits', label: 'Total LH', proKey: 'pro_avg_lh' },
                { key: 'gold_efficiency', label: 'Spent Efficiency' },
            ],
        },
        {
            title: 'Positioning & Safety',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L16 4m0 13V4m-6 3L16 4" />
                </svg>
            ),
            metrics: [
                { key: 'position_safety_score', label: 'Safety Rating' },
                { key: 'danger_zone_pct', label: 'Danger Zone %' },
                { key: 'avg_distance_from_team', label: 'Team Spacing' },
                { key: 'respawn_sum', label: 'Time Dead (s)' },
            ],
        },
        {
            title: 'Combat & Impact',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
            ),
            metrics: [
                { key: 'teamfight_participation', label: 'TF Participation %' },
                { key: 'hero_damage', label: 'Hero Damage' },
                { key: 'stun_duration_total', label: 'Stun Duration (s)' },
                { key: 'kda', label: 'KDA Ratio' },
            ],
        },
        {
            title: 'Item Timings',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
            metrics: [
                { key: 'boots_timing', label: 'Boots Timing', isTime: true },
                { key: 'blink_timing', label: 'Blink Timing', isTime: true },
                { key: 'core_item_1_timing', label: 'Core Item 1', isTime: true },
                { key: 'first_item_timing', label: 'First Major Item', isTime: true },
            ],
        },
        {
            title: 'Vision & Support',
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
            ),
            metrics: [
                { key: 'vision_score', label: 'Vision Score', proKey: 'pro_avg_vision' },
                { key: 'camp_stacking', label: 'Camps Stacked' },
                { key: 'hero_healing', label: 'Hero Healing' },
                { key: 'tower_damage', label: 'Tower Damage' },
            ],
        },
    ];

    const formatValue = (value: number | string | undefined, isTime: boolean = false): string => {
        if (value === undefined || value === null || (typeof value === 'number' && value === 0)) return '-';
        if (typeof value === 'number') {
            if (isTime) {
                const mins = Math.floor(value / 60);
                const secs = Math.floor(value % 60);
                return `${mins}:${secs.toString().padStart(2, '0')}`;
            }
            return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
        }
        return String(value);
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {metricGroups.map((group) => (
                <div key={group.title} className="bg-gray-800 border border-gray-700/50 rounded-2xl p-6 hover:bg-gray-800/80 transition-all hover:border-gray-600 shadow-xl">
                    <div className="flex items-center gap-3 mb-6 border-b border-gray-700/50 pb-4">
                        <div className="w-10 h-10 bg-teal-500/10 rounded-xl flex items-center justify-center text-teal-400 border border-teal-500/20">
                            {group.icon}
                        </div>
                        <h3 className="text-lg font-bold text-white tracking-tight">{group.title}</h3>
                    </div>
                    <div className="space-y-6">
                        {group.metrics.map((metric) => {
                            const val = metrics[metric.key];
                            const proVal = metric.proKey ? metrics[metric.proKey] : undefined;
                            const hasBoth = typeof val === 'number' && typeof proVal === 'number' && proVal > 0;

                            return (
                                <div key={metric.key} className="flex flex-col gap-2">
                                    <div className="flex items-center justify-between">
                                        <p className="text-gray-400 text-xs font-bold uppercase tracking-widest">{metric.label}</p>
                                        <p className="text-xl font-black text-white">
                                            {formatValue(val, metric.isTime)}
                                        </p>
                                    </div>

                                    {hasBoth && (
                                        <div className="flex flex-col gap-1.5">
                                            <div className="flex items-center justify-between px-1">
                                                <span className="text-[9px] text-gray-500 font-black uppercase tracking-tighter">PRO TARGET</span>
                                                <span className="text-[10px] text-gray-400 font-mono font-bold">
                                                    {formatValue(proVal, metric.isTime)}
                                                </span>
                                            </div>
                                            <div className="w-full h-1.5 bg-gray-900/50 rounded-full overflow-hidden border border-gray-700/30">
                                                <div
                                                    className={`h-full rounded-full transition-all duration-1000 ${(val as number) >= (proVal as number)
                                                            ? 'bg-gradient-to-r from-green-600 to-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]'
                                                            : 'bg-gradient-to-r from-red-600 to-orange-400'
                                                        }`}
                                                    style={{ width: `${Math.min(((val as number) / (proVal as number)) * 100, 100)}%` }}
                                                />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default MetricsDisplay;
