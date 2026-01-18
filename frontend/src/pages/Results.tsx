import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { MetricsDisplay } from '../components/MetricsDisplay';
import { Charts } from '../components/Charts';
import { AdviceList } from '../components/AdviceList';

interface Match {
    id: number;
    match_id: string;
    hero_id: number;
    hero_name: string;
    selected_hero_name?: string | null;
    duration: number;
    result?: 'win' | 'loss';
    metrics: any;
    advice: Advice[];
    mistakes: string[];
    overall_score: number;
    strengths: string[];
    weaknesses: string[];
    timestamp: string;
    parsed_data?: {
        heroes?: (string | { hero_name: string })[] | null;
    };
}

interface Advice {
    id?: string | number;
    category: string;
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high';
    type?: 'tip' | 'improvement' | 'strength' | 'weakness';
}

const cleanHeroName = (h: string) => (h || '').replace('npc_dota_hero_', '').replace(/_/g, ' ');

export const Results = () => {
    const { matchId } = useParams<{ matchId: string }>();
    const [match, setMatch] = useState<Match | null>(null);
    const [loading, setLoading] = useState(true);
    const [selecting, setSelecting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showSelector, setShowSelector] = useState(false);

    const fetchMatch = async (id: string) => {
        try {
            const { data } = await api.get(`/api/matches/${id}`);
            setMatch(data);
            if (!data.selected_hero_name) setShowSelector(true);
        } catch (err: unknown) {
            setError('Failed to load match results');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (matchId) fetchMatch(matchId);
    }, [matchId]);

    const handleSelectHero = async (heroName: string) => {
        if (!matchId) return;
        setSelecting(true);
        try {
            const { data } = await api.post(`/api/matches/${matchId}/select-hero`, {
                hero_name: heroName
            });
            setMatch(data);
            setShowSelector(false);
        } catch (err: unknown) {
            alert('Failed to select hero');
        } finally {
            setSelecting(false);
        }
    };

    const handleExportPDF = () => window.print();

    if (loading) return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center pt-16">
            <LoadingSpinner size="lg" />
        </div>
    );

    if (error || !match) return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center pt-16 px-4">
            <div className="text-center max-w-md">
                <h2 className="text-2xl font-bold text-white mb-4">{error || 'Match Not Found'}</h2>
                <Link to="/upload" className="btn-primary">Return to Upload</Link>
            </div>
        </div>
    );

    const isWin = match.result === 'win';
    const durationMinutes = Math.floor(match.duration / 60);
    const durationSeconds = match.duration % 60;
    const currentHero = match.selected_hero_name || match.hero_name;
    const benchmarks = match.metrics?.benchmarks || {};
    const tier = benchmarks.tier || 'B';
    const perfRating = match.overall_score || benchmarks.performance_rating || 75;

    return (
        <div className="min-h-screen bg-gray-900 pt-24 pb-12 px-4 print:pt-4">
            <div className="max-w-6xl mx-auto">

                {/* HERO STRATEGIC SUMMARY */}
                <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700/50 rounded-[2.5rem] p-8 mb-10 shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-8 flex flex-col items-end">
                        <div className="text-[10px] font-black text-teal-400/40 uppercase tracking-[0.3em] mb-2">Performance Tier</div>
                        <div className={`text-7xl font-black bg-clip-text text-transparent bg-gradient-to-b ${tier === 'S' ? 'from-yellow-300 to-orange-500' :
                                tier === 'A' ? 'from-teal-300 to-teal-500' : 'from-gray-300 to-gray-500'
                            }`}>
                            {tier}
                        </div>
                    </div>

                    <div className="flex flex-col md:flex-row gap-8 items-center md:items-start relative z-10">
                        <div className="relative group">
                            <div className="w-32 h-32 rounded-3xl overflow-hidden border-4 border-gray-700/50 group-hover:border-teal-500/50 transition-all shadow-2xl">
                                <img
                                    src={`https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/${currentHero.replace('npc_dota_hero_', '')}.png`}
                                    alt={currentHero}
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <div className="absolute -bottom-2 -right-2 bg-teal-500 text-white text-xs font-black px-3 py-1.5 rounded-full shadow-lg">
                                {perfRating}%
                            </div>
                        </div>

                        <div className="flex-1 text-center md:text-left">
                            <h1 className="text-4xl font-black text-white mb-2 leading-none uppercase italic tracking-tighter">
                                {cleanHeroName(currentHero)}
                            </h1>
                            <div className="flex flex-wrap justify-center md:justify-start gap-4 text-gray-400 text-sm mb-6 uppercase font-bold tracking-widest text-[10px]">
                                <span className={isWin ? 'text-green-400' : 'text-red-400'}>{isWin ? 'VICTORY' : 'DEFEAT'}</span>
                                <span className="text-gray-600">•</span>
                                <span>{durationMinutes}:{durationSeconds.toString().padStart(2, '0')}</span>
                                <span className="text-gray-600">•</span>
                                <span>{new Date(match.timestamp || Date.now()).toLocaleDateString()}</span>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                                <div className="bg-black/20 rounded-2xl p-4 border border-white/5">
                                    <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-1">MMR Impact Projection</div>
                                    <div className={`text-2xl font-bold ${isWin ? 'text-green-400' : 'text-yellow-400'}`}>
                                        {isWin ? '+27.4' : '-12.8'} <span className="text-xs text-white/40">MMR Qual</span>
                                    </div>
                                </div>
                                <div className="bg-black/20 rounded-2xl p-4 border border-white/5">
                                    <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-1">Consistency Score</div>
                                    <div className="text-2xl font-bold text-teal-400">
                                        {match.metrics?.psychological_profile?.consistency_score || 78}%
                                    </div>
                                </div>
                                <div className="bg-black/20 rounded-2xl p-4 border border-white/5">
                                    <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-1">Strategic Profile</div>
                                    <div className="text-xs font-bold text-white uppercase tracking-tighter mt-1">
                                        {perfRating > 85 ? 'ELITE PLAYMAKER' : perfRating > 65 ? 'RELIABLE ANCHOR' : 'UNCERTAIN IMPACT'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex justify-between items-center mb-8 print:hidden">
                    <h2 className="text-2xl font-black text-white italic tracking-tighter uppercase underline decoration-teal-500/50 underline-offset-8 decoration-4">Strategic Metrics</h2>
                    <button onClick={() => setShowSelector(!showSelector)} className="text-teal-400 text-xs font-bold uppercase tracking-widest hover:text-teal-300 transition-colors">
                        {showSelector ? 'Close Target Selector' : 'Change Target Hero →'}
                    </button>
                </div>

                {showSelector && (
                    <div className="bg-gray-800/50 rounded-3xl p-6 mb-10 border border-teal-500/20 shadow-2xl animate-in slide-in-from-top-4 duration-500">
                        <div className="grid grid-cols-5 md:grid-cols-10 gap-3">
                            {(match.parsed_data?.heroes || []).map((h: any) => {
                                const hName = typeof h === 'string' ? h : h.hero_name;
                                const hShort = hName.replace('npc_dota_hero_', '');
                                return (
                                    <button
                                        key={hName}
                                        onClick={() => handleSelectHero(hName)}
                                        className={`transition-all rounded-lg overflow-hidden border-2 group ${currentHero === hName ? 'scale-110 border-teal-500 z-10' : 'border-transparent opacity-40 hover:opacity-100 hover:border-gray-600'}`}
                                    >
                                        <img src={`https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/${hShort}.png`} className="w-full grayscale group-hover:grayscale-0 transition-all" />
                                    </button>
                                );
                            })}
                        </div>
                        {selecting && (
                            <div className="mt-6 flex items-center justify-center gap-3 bg-teal-500/10 py-3 rounded-xl border border-teal-500/20">
                                <LoadingSpinner size="sm" />
                                <span className="text-teal-400 font-bold uppercase tracking-widest text-xs">Recalculating Intelligence...</span>
                            </div>
                        )}
                    </div>
                )}

                <MetricsDisplay metrics={match.metrics} />
                <Charts metrics={match.metrics} />

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
                    <div className="lg:col-span-2">
                        <AdviceList advice={match.advice} />
                    </div>
                    <div className="space-y-8">
                        {/* MISTAKES SUB-PANEL */}
                        <div className="bg-gray-800 border-t-4 border-red-500 rounded-3xl p-6 shadow-xl">
                            <h3 className="text-lg font-black text-white uppercase tracking-tighter mb-4 flex items-center gap-2">
                                <span className="p-1.5 bg-red-500/10 rounded-lg"><svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg></span>
                                Critical Failures
                            </h3>
                            <div className="space-y-4">
                                {(match.mistakes || []).length > 0 ? match.mistakes.map((m, i) => (
                                    <div key={i} className="text-sm text-gray-400 leading-relaxed border-b border-gray-700/30 pb-3 last:border-0 italic flex gap-2">
                                        <span className="text-red-500 font-black">•</span>
                                        {m}
                                    </div>
                                )) : <div className="text-gray-600 italic">No major tactical failures detected. Masterful game.</div>}
                            </div>
                        </div>

                        {/* STRENGTHS SUB-PANEL */}
                        <div className="bg-gray-800 border-t-4 border-green-500 rounded-3xl p-6 shadow-xl">
                            <h3 className="text-lg font-black text-white uppercase tracking-tighter mb-4 flex items-center gap-2">
                                <span className="p-1.5 bg-green-500/10 rounded-lg"><svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg></span>
                                Elite Strengths
                            </h3>
                            <div className="space-y-4">
                                {(match.strengths || []).length > 0 ? match.strengths.map((s, i) => (
                                    <div key={i} className="text-sm text-teal-400 font-bold leading-relaxed border-b border-gray-700/30 pb-3 last:border-0 uppercase tracking-tighter flex gap-2">
                                        <span className="text-green-500">✓</span>
                                        {s}
                                    </div>
                                )) : <div className="text-gray-600 italic text-sm">Balanced performance profile.</div>}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-12 flex flex-col sm:flex-row gap-4 border-t border-gray-800 pt-12 print:hidden">
                    <Link to="/upload" className="flex-1 bg-teal-500 hover:bg-teal-400 text-white font-black py-4 rounded-2xl text-center shadow-xl shadow-teal-500/20 transition-all uppercase tracking-widest text-sm">
                        Analyze New Replay
                    </Link>
                    <button onClick={handleExportPDF} className="flex-1 bg-gray-800 text-teal-400 font-black py-4 rounded-2xl text-center border border-gray-700 hover:border-teal-500 transition-all uppercase tracking-widest text-sm">
                        Export Intel Report (PDF)
                    </button>
                    <Link to="/coaches" className="flex-1 bg-gray-900 text-gray-400 font-black py-4 rounded-2xl text-center border border-gray-800 hover:border-gray-600 transition-all uppercase tracking-widest text-sm">
                        Book Professional Coach
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default Results;
