import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { HeroSelectionModal } from '../components/HeroSelectionModal';

export const Upload = () => {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);

    // Hero Selection State
    const [showHeroModal, setShowHeroModal] = useState(false);
    const [pendingMatchId, setPendingMatchId] = useState("");
    const [matchHeroes, setMatchHeroes] = useState<any[]>([]);

    const navigate = useNavigate();

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const validateFile = (f: File): boolean => {
        if (!f.name.endsWith('.dem')) {
            setError('Please upload a .dem file');
            return false;
        }
        // Max 200MB
        if (f.size > 200 * 1024 * 1024) {
            setError('File size must be less than 200MB');
            return false;
        }
        return true;
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        const files = e.dataTransfer.files;
        if (files && files[0]) {
            const f = files[0];
            if (validateFile(f)) {
                setFile(f);
                setError(null);
            }
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            const f = e.target.files[0];
            if (validateFile(f)) {
                setFile(f);
                setError(null);
            }
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);
        setUploadProgress(0);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const { data } = await api.post('/api/matches/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                onUploadProgress: (progressEvent) => {
                    if (progressEvent.total) {
                        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        setUploadProgress(progress);
                    }
                },
            });

            if (data.status === "awaiting_hero_selection") {
                setPendingMatchId(data.match_id);
                setMatchHeroes(data.heroes_in_match);
                setShowHeroModal(true);
                return;
            }

            navigate(`/results/${data.match_id}`);
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Upload failed');
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleRemoveFile = () => {
        setFile(null);
        setError(null);
        setUploadProgress(0);
    };

    const handleHeroSelected = (heroData: any) => {
        setShowHeroModal(false);
        // data.match_id might be needed if the response structure changes, but reusing pendingMatchId is safe if response doesn't have it
        navigate(`/results/${heroData.match_id || pendingMatchId}`);
    };

    return (
        <div className="min-h-screen bg-gray-900 pt-24 pb-12">
            <div className="max-w-2xl mx-auto px-4">
                {/* Header */}
                <div className="text-center mb-10">
                    <h1 className="text-4xl font-bold mb-4 text-white">Upload Replay</h1>
                    <p className="text-xl text-gray-400">
                        Upload your Dota 2 replay file to get detailed analysis
                    </p>
                </div>

                {/* Drop Zone */}
                <div
                    className={`
            relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300
            ${dragActive
                            ? 'border-teal-500 bg-teal-500/10 scale-[1.02]'
                            : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
                        }
          `}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('file-input')?.click()}
                >
                    <input
                        id="file-input"
                        type="file"
                        accept=".dem"
                        onChange={handleFileSelect}
                        className="hidden"
                    />

                    {/* Upload Icon */}
                    <div className={`
            w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 transition-colors
            ${dragActive ? 'bg-teal-500/20' : 'bg-gray-700'}
          `}>
                        <svg
                            className={`w-10 h-10 transition-colors ${dragActive ? 'text-teal-400' : 'text-gray-400'}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                            />
                        </svg>
                    </div>

                    {file ? (
                        <div className="space-y-2">
                            <p className="text-lg font-semibold text-teal-400">{file.name}</p>
                            <p className="text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleRemoveFile();
                                }}
                                className="text-red-400 hover:text-red-300 text-sm underline mt-2"
                            >
                                Remove file
                            </button>
                        </div>
                    ) : (
                        <div>
                            <p className="text-lg text-gray-300 mb-2">
                                {dragActive ? 'Drop your file here' : 'Drag and drop your .dem file here'}
                            </p>
                            <p className="text-gray-500">or click to browse</p>
                        </div>
                    )}
                </div>

                {/* Error Message */}
                {error && (
                    <div className="mt-6 bg-red-500/20 border border-red-500/50 text-red-400 p-4 rounded-lg flex items-center gap-3">
                        <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>{error}</span>
                    </div>
                )}

                {/* Upload Progress */}
                {loading && (
                    <div className="mt-6">
                        <div className="flex items-center justify-between text-sm text-gray-400 mb-2">
                            <span>Uploading...</span>
                            <span>{uploadProgress}%</span>
                        </div>
                        <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-teal-500 to-teal-400 transition-all duration-300"
                                style={{ width: `${uploadProgress}%` }}
                            />
                        </div>
                    </div>
                )}

                {/* Upload Button */}
                <button
                    onClick={handleUpload}
                    disabled={!file || loading}
                    className={`
            mt-8 w-full py-4 rounded-lg font-semibold text-lg transition-all duration-300 flex items-center justify-center gap-3
            ${!file || loading
                            ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                            : 'bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white shadow-lg shadow-teal-500/25'
                        }
          `}
                >
                    {loading ? (
                        <>
                            <LoadingSpinner size="sm" />
                            <span>Analyzing...</span>
                        </>
                    ) : (
                        <>
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                            <span>Analyze Replay</span>
                        </>
                    )}
                </button>

                {/* Info Cards */}
                <div className="grid grid-cols-2 gap-4 mt-10">
                    <div className="card">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-8 h-8 bg-teal-500/20 rounded-lg flex items-center justify-center">
                                <svg className="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </div>
                            <h3 className="font-semibold text-white">Supported Format</h3>
                        </div>
                        <p className="text-gray-400 text-sm">.dem files from Dota 2</p>
                    </div>
                    <div className="card">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-8 h-8 bg-teal-500/20 rounded-lg flex items-center justify-center">
                                <svg className="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                                </svg>
                            </div>
                            <h3 className="font-semibold text-white">Max File Size</h3>
                        </div>
                        <p className="text-gray-400 text-sm">Up to 200MB per replay</p>
                    </div>
                </div>
            </div>

            {showHeroModal && (
                <HeroSelectionModal
                    match_id={pendingMatchId}
                    heroes={matchHeroes}
                    onHeroSelected={handleHeroSelected}
                    loading={false}
                />
            )}
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
