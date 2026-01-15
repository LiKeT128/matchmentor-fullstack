import React, { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import { LoadingSpinner } from './LoadingSpinner';

interface DemoUploadProps {
    onUploadComplete: (matchId: string) => void;
}

export const DemoUpload: React.FC<DemoUploadProps> = ({ onUploadComplete }) => {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [parsing, setParsing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [dragActive, setDragActive] = useState(false);

    // Polling state
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };
    }, []);

    const validateFile = (f: File): boolean => {
        if (!f.name.endsWith('.dem')) {
            setError('Please upload a .dem file');
            return false;
        }
        if (f.size > 500 * 1024 * 1024) {
            setError('File size must be less than 500MB');
            return false;
        }
        return true;
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const f = e.dataTransfer.files[0];
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

    const pollStatus = async (id: number) => {
        try {
            const { data } = await api.get(`/api/matches/${id}/status`);

            if (data.status === 'completed') {
                setParsing(false);
                // Use real_match_id if available, otherwise internal id
                const finalId = data.real_match_id || data.match_id;
                onUploadComplete(String(finalId));
            } else if (data.status === 'failed') {
                setParsing(false);
                setError(`Parsing failed: ${data.message || 'Unknown error'}`);
            } else {
                // Keep polling
                timeoutRef.current = setTimeout(() => pollStatus(id), 2000);
            }
        } catch (err) {
            console.error("Polling error:", err);
            // Retry a few times? For now just keep polling if it's a network blip, 
            // or fail if it's 404 (which shouldn't happen unless deleted)
            timeoutRef.current = setTimeout(() => pollStatus(id), 3000);
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
        setParsing(false);
        setError(null);
        setUploadProgress(0);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const { data } = await api.post('/api/matches/upload-demo', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                onUploadProgress: (progressEvent) => {
                    if (progressEvent.total) {
                        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        setUploadProgress(progress);
                    }
                },
            });

            setUploading(false);
            setParsing(true);

            // Start polling
            pollStatus(data.match_id);

        } catch (err: any) {
            setUploading(false);
            const msg = err.response?.data?.detail || 'Upload failed';
            setError(msg);
        }
    };

    return (
        <>
            <div
                className={`
                    relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300
                    ${dragActive
                        ? 'border-teal-500 bg-teal-500/10 scale-[1.02]'
                        : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
                    }
                    ${(uploading || parsing) ? 'opacity-50 pointer-events-none' : ''}
                `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !uploading && !parsing && document.getElementById('file-input')?.click()}
            >
                <input
                    id="file-input"
                    type="file"
                    accept=".dem"
                    onChange={handleFileSelect}
                    className="hidden"
                    disabled={uploading || parsing}
                />

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
                        {!uploading && !parsing && (
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setFile(null);
                                    setError(null);
                                }}
                                className="text-red-400 hover:text-red-300 text-sm underline mt-2"
                            >
                                Remove file
                            </button>
                        )}
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

            {/* Info Cards (Upload) */}
            <div className="grid grid-cols-2 gap-4 mt-6">
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
                    <p className="text-gray-400 text-sm">Up to 500MB per replay</p>
                </div>
            </div>

            {/* Upload Button */}
            <button
                onClick={handleUpload}
                disabled={!file || uploading || parsing}
                className={`
                    mt-8 w-full py-4 rounded-lg font-semibold text-lg transition-all duration-300 flex items-center justify-center gap-3
                    ${!file || uploading || parsing
                        ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                        : 'bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white shadow-lg shadow-teal-500/25'
                    }
                `}
            >
                {uploading ? (
                    <>
                        <LoadingSpinner size="sm" />
                        <span>Uploading... {uploadProgress}%</span>
                    </>
                ) : parsing ? (
                    <>
                        <LoadingSpinner size="sm" />
                        <span>Parsing Replay (this may take a minute)...</span>
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

            {/* Error Message */}
            {error && (
                <div className="mt-6 bg-red-500/20 border border-red-500/50 text-red-400 p-4 rounded-lg">
                    <div className="flex items-start gap-3">
                        <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="flex-1">
                            {/* Handle multiline errors from backend */}
                            {error.split('\n').map((line, idx) => (
                                <p key={idx} className={`${idx > 0 ? 'mt-2' : ''} ${line.startsWith('- ') ? 'ml-4' : ''}`}>
                                    {line}
                                </p>
                            ))}
                            {error.toLowerCase().includes('parsing failed') && (
                                <div className="mt-3 pt-3 border-t border-red-500/30 text-sm">
                                    <p className="font-semibold mb-1">💡 Troubleshooting Tips:</p>
                                    <ul className="list-disc list-inside space-y-1 text-red-300">
                                        <li>Check the Railway logs for detailed debugging information</li>
                                        <li>Verify the replay file opens correctly in Dota 2</li>
                                        <li>Try a different replay file to rule out file corruption</li>
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Parsing Progress Indicator */}
            {parsing && (
                <div className="mt-4 text-center">
                    <p className="text-gray-400 text-sm animate-pulse">
                        Our Clarity parser is analyzing every frame of your game...
                    </p>
                </div>
            )}
        </>
    );
};
