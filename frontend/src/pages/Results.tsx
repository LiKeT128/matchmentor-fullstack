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
    hero: string;
    hero_name?: string; // Alternative from backend
    selected_hero_name?: string | null;
    duration: number;
    result?: 'win' | 'loss';
    metrics: Record<string, number>;
    advice: Advice[];
    created_at: string;
    parsed_data?: {
        heroes?: string[] | null;
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

// Utility to safely clean hero names
const cleanHeroName = (heroStr: string | null | undefined): string => {
    if (!heroStr || typeof heroStr !== 'string') return 'Unknown Hero';
    return heroStr.replace('npc_dota_hero_', '').replace(/_/g, ' ');
};

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
            console.log('Match data received:', data);
            console.log('selected_hero_name:', data.selected_hero_name);
            console.log('heroes in match:', data.parsed_data?.heroes);

            setMatch(data);
            // If no hero is selected yet, show the selector
            if (!data.selected_hero_name) {
                setShowSelector(true);
            }
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to load match');
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (matchId) {
            fetchMatch(matchId);
        }
    }, [matchId]);

    const handleSelectHero = async (heroName: string) => {
        if (!matchId) return;
        setSelecting(true);
        try {
            console.log('Selecting hero:', heroName);
            const { data } = await api.post(`/api/matches/${matchId}/select-hero`, {
                selected_hero_name: heroName
            });
            console.log('Selection response:', data);
            setMatch(data);
            setShowSelector(false);
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to select hero');
            alert(message);
        } finally {
            setSelecting(false);
        }
    };

    const handleExportPDF = () => {
        window.print();
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-900 flex items-center justify-center pt-16">
                <div className="text-center">
                    <LoadingSpinner size="lg" className="mb-4" />
                    <p className="text-gray-400 text-lg">Analyzing your match...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-900 flex items-center justify-center pt-16 px-4">
                <div className="text-center max-w-md">
                    <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                        <svg className="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-3">Failed to Load Analysis</h2>
                    <p className="text-gray-400 mb-8">{error}</p>
                    <Link to="/upload" className="btn-primary inline-block">
                        Upload Another Replay
                    </Link>
                </div>
            </div>
        );
    }

    if (!match) {
        return (
            <div className="min-h-screen bg-gray-900 flex items-center justify-center pt-16 px-4">
                <div className="text-center max-w-md">
                    <div className="w-20 h-20 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-6">
                        <svg className="w-10 h-10 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 12h.01M12 12h-.01" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-3">Match Not Found</h2>
                    <p className="text-gray-400 mb-8">The match you're looking for doesn't exist or has been removed.</p>
                    <Link to="/upload" className="btn-primary inline-block">
                        Upload a Replay
                    </Link>
                </div>
            </div>
        );
    }

    const isWin = match.result === 'win';
    const durationMinutes = Math.floor(match.duration / 60);
    const durationSeconds = match.duration % 60;

    // Defensive hero extraction
    const allHeroes = [
        match.hero_name || match.hero,
        ...(match.parsed_data?.heroes || [])
    ].filter((h): h is string => typeof h === 'string' && h.trim().length > 0)
        .filter((h, i, arr) => arr.indexOf(h) === i);

    const currentHero = match.selected_hero_name || match.hero_name || match.hero;

    return (
        <div className="min-h-screen bg-gray-900 pt-24 pb-12 px-4">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-10">
                    <div>
                        <div className="flex items-center gap-4 mb-3">
                            <div className="flex flex-col">
                                <span className="text-teal-400 text-xs font-bold uppercase tracking-wider mb-1">Analyzing Hero</span>
                                <h1 className="text-4xl font-bold text-white">
                                    {cleanHeroName(currentHero)}
                                </h1>
                            </div>
                            {match.result && (
                                <span className={`px-4 py-2 rounded-lg font-bold text-sm h-fit self-end mb-1 ${isWin
                                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                                    }`}>
                                    {isWin ? 'VICTORY' : 'DEFEAT'}
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-4 text-gray-400">
                            <span className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {durationMinutes}:{durationSeconds.toString().padStart(2, '0')}
                            </span>
                            <span className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                {new Date(match.created_at).toLocaleDateString()}
                            </span>
                            <button
                                onClick={() => setShowSelector(!showSelector)}
                                className="text-teal-400 hover:text-teal-300 text-sm font-semibold underline decoration-2 underline-offset-4 ml-2"
                            >
                                {showSelector ? 'Close Selector' : 'Change Hero'}
                            </button>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                        <button
                            onClick={handleExportPDF}
                            className="btn-secondary flex items-center gap-2"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Export PDF
                        </button>
                        <Link to="/upload" className="btn-primary flex items-center gap-2">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            New Analysis
                        </Link>
                    </div>
                </div>

                {/* Hero Selector */}
                {showSelector && (
                    <div className="mb-10 p-6 bg-gray-800/50 border border-gray-700 rounded-2xl relative">
                        <h3 className="text-xl font-bold text-white mb-6">Select Hero to Analyze</h3>
                        <div className="grid grid-cols-2 sm:grid-cols-5 md:grid-cols-10 gap-3">
                            {allHeroes.map(hero => {
                                const heroShortName = hero.replace('npc_dota_hero_', '');
                                return (
                                    <button
                                        key={hero}
                                        onClick={() => handleSelectHero(hero)}
                                        disabled={selecting}
                                        className={`
                                            group relative flex flex-col items-center gap-2 p-2 rounded-xl border-2 transition-all
                                            ${currentHero === hero
                                                ? 'border-teal-500 bg-teal-500/10'
                                                : 'border-transparent hover:border-gray-600 bg-gray-900/50'
                                            }
                                        `}
                                    >
                                        <div className="relative w-full aspect-[128/72] overflow-hidden rounded-lg">
                                            <img
                                                src={`https://api.opendota.com/apps/dota2/images/heroes/${heroShortName}_full.png`}
                                                alt={heroShortName}
                                                className="w-full h-full object-cover transition-transform group-hover:scale-110"
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).src = 'https://via.placeholder.com/128x72?text=Hero';
                                                }}
                                            />
                                            {currentHero === hero && (
                                                <div className="absolute inset-0 bg-teal-500/20 flex items-center justify-center">
                                                    <svg className="w-8 h-8 text-white drop-shadow-lg" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                                    </svg>
                                                </div>
                                            )}
                                        </div>
                                        <span className={`text-[10px] font-bold uppercase truncate w-full text-center ${currentHero === hero ? 'text-teal-400' : 'text-gray-400 group-hover:text-gray-200'}`}>
                                            {heroShortName.replace(/_/g, ' ')}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                        {selecting && (
                            <div className="absolute inset-0 bg-gray-900/60 backdrop-blur-[2px] rounded-2xl flex flex-col items-center justify-center gap-4 z-10 transition-opacity">
                                <LoadingSpinner size="md" />
                                <span className="text-white font-semibold">Updating Analysis...</span>
                            </div>
                        )}
                    </div>
                )}

                {/* Metrics Display */}
                <MetricsDisplay metrics={match.metrics} />

                {/* Charts */}
                <Charts metrics={match.metrics} />

                {/* Advice List */}
                <AdviceList advice={match.advice} />

                {/* Bottom Actions */}
                <div className="flex flex-col sm:flex-row gap-4 mt-12 pt-8 border-t border-gray-800">
                    <Link to="/upload" className="btn-primary text-center flex-1 py-4">
                        Analyze Another Match
                    </Link>
                    <Link to="/coaches" className="btn-secondary text-center flex-1 py-4">
                        Find a Coach
                    </Link>
                </div>
            </div>
        </div>
    );
};

function extractErrorMessage(err: unknown, fallback: string): string {
    if (err && typeof err === 'object' && 'response' in err) {
        const response = (err as { response?: { data?: { detail?: string } } }).response;
        if (response?.data?.detail) {
            return response.data.detail;
        }
    }
    return fallback;
}

export default Results;
