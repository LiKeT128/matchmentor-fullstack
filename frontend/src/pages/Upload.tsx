import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { HeroSelectionModal } from '../components/HeroSelectionModal';
import { DemoUpload } from '../components/DemoUpload';

export const Upload = () => {
    // Lookup State
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lookupMatchId, setLookupMatchId] = useState('');

    // Hero Selection State
    const [showHeroModal, setShowHeroModal] = useState(false);
    const [pendingMatchId, setPendingMatchId] = useState("");
    const [matchHeroes, setMatchHeroes] = useState<any[]>([]);

    // Tab State
    const [activeTab, setActiveTab] = useState<'upload' | 'lookup'>('upload');

    const navigate = useNavigate();

    const handleLookup = async () => {
        if (!lookupMatchId.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const { data } = await api.post(`/api/matches/lookup?match_id=${lookupMatchId}`);

            // Regardless of status (found / already_analyzed), we show hero selection
            // because even if analyzed, user might want to select a new hero or confirm
            setPendingMatchId(data.match_id);
            setMatchHeroes(data.heroes_in_match || []);
            setShowHeroModal(true);

        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Match lookup failed');
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleHeroSelected = (heroData: any) => {
        setShowHeroModal(false);
        navigate(`/results/${heroData.match_id || pendingMatchId}`);
    };

    const handleDemoUploadComplete = (matchId: string) => {
        navigate(`/results/${matchId}`);
    };

    return (
        <div className="min-h-screen bg-gray-900 pt-24 pb-12">
            <div className="max-w-2xl mx-auto px-4">
                {/* Header */}
                <div className="text-center mb-10">
                    <h1 className="text-4xl font-bold mb-4 text-white">Analyze Match</h1>
                    <p className="text-xl text-gray-400">
                        Upload a replay or search by Match ID
                    </p>
                </div>

                {/* Tabs */}
                <div className="flex bg-gray-800 p-1 rounded-xl mb-8">
                    <button
                        onClick={() => { setActiveTab('upload'); setError(null); }}
                        className={`flex-1 py-3 rounded-lg font-semibold text-sm transition-all ${activeTab === 'upload'
                            ? 'bg-gray-700 text-white shadow-lg'
                            : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Upload .dem File
                    </button>
                    <button
                        onClick={() => { setActiveTab('lookup'); setError(null); }}
                        className={`flex-1 py-3 rounded-lg font-semibold text-sm transition-all ${activeTab === 'lookup'
                            ? 'bg-gray-700 text-white shadow-lg'
                            : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Search Match ID
                    </button>
                </div>

                {activeTab === 'upload' ? (
                    <DemoUpload onUploadComplete={handleDemoUploadComplete} />
                ) : (
                    /* Lookup UI */
                    <div className="bg-gray-800/50 p-8 rounded-xl border border-gray-700">
                        <div className="mb-6">
                            <label className="block text-gray-400 text-sm font-bold mb-2">
                                Dota 2 Match ID
                            </label>
                            <input
                                type="text"
                                value={lookupMatchId}
                                onChange={(e) => setLookupMatchId(e.target.value.replace(/\D/g, ''))} // Numeric only
                                placeholder="e.g. 8627882837"
                                className="w-full bg-gray-900 border border-gray-600 rounded-lg p-4 text-white text-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all placeholder-gray-500"
                            />
                            <p className="text-xs text-gray-500 mt-2">
                                Provide a Match ID to analyze metrics without uploading a replay file.
                            </p>
                        </div>

                        <button
                            onClick={handleLookup}
                            disabled={!lookupMatchId || loading}
                            className={`
                                w-full py-4 rounded-lg font-semibold text-lg transition-all duration-300 flex items-center justify-center gap-3
                                ${!lookupMatchId || loading
                                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white shadow-lg shadow-teal-500/25'
                                }
                            `}
                        >
                            {loading ? (
                                <>
                                    <LoadingSpinner size="sm" />
                                    <span>Searching...</span>
                                </>
                            ) : (
                                <>
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                    <span>Find Match</span>
                                </>
                            )}
                        </button>
                    </div>
                )}

                {/* Error Message (for Lookup) */}
                {error && (
                    <div className="mt-6 bg-red-500/20 border border-red-500/50 text-red-400 p-4 rounded-lg flex items-center gap-3">
                        <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>{error}</span>
                    </div>
                )}

                {showHeroModal && (
                    <HeroSelectionModal
                        match_id={pendingMatchId}
                        heroes={matchHeroes}
                        onHeroSelected={handleHeroSelected}
                        loading={false}
                    />
                )}
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

export default Upload;
