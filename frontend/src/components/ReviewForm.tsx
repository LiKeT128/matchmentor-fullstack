import { useState } from 'react';
import { api } from '../services/api';
import { LoadingSpinner } from './LoadingSpinner';

interface ReviewFormProps {
    coachId: string;
    bookingId?: string;
    onSuccess: () => void;
    onCancel: () => void;
}

export const ReviewForm = ({ coachId, bookingId, onSuccess, onCancel }: ReviewFormProps) => {
    const [rating, setRating] = useState(0);
    const [hoverRating, setHoverRating] = useState(0);
    const [comment, setComment] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (rating === 0) {
            setError('Please select a rating');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            await api.post('/api/reviews', {
                coach_id: coachId,
                booking_id: bookingId,
                rating,
                comment,
            });
            onSuccess();
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to submit review');
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const displayRating = hoverRating || rating;

    return (
        <form onSubmit={handleSubmit} className="bg-gray-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-6">Leave a Review</h3>

            {error && (
                <div className="mb-4 bg-red-500/20 border border-red-500/50 text-red-400 p-3 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {/* Star Rating */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-3">
                    Your Rating
                </label>
                <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                        <button
                            key={star}
                            type="button"
                            onClick={() => setRating(star)}
                            onMouseEnter={() => setHoverRating(star)}
                            onMouseLeave={() => setHoverRating(0)}
                            className="p-1 transition-transform hover:scale-110"
                        >
                            <svg
                                className={`w-8 h-8 transition-colors ${star <= displayRating ? 'text-yellow-400' : 'text-gray-600'
                                    }`}
                                fill="currentColor"
                                viewBox="0 0 20 20"
                            >
                                <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                            </svg>
                        </button>
                    ))}
                </div>
                <p className="text-sm text-gray-400 mt-2">
                    {displayRating === 1 && 'Poor'}
                    {displayRating === 2 && 'Fair'}
                    {displayRating === 3 && 'Good'}
                    {displayRating === 4 && 'Very Good'}
                    {displayRating === 5 && 'Excellent'}
                </p>
            </div>

            {/* Comment */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-3">
                    Your Review
                </label>
                <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Share your experience with this coach..."
                    rows={4}
                    className="w-full px-4 py-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20 resize-none"
                />
            </div>

            {/* Actions */}
            <div className="flex gap-3">
                <button
                    type="button"
                    onClick={onCancel}
                    className="flex-1 btn-secondary"
                    disabled={loading}
                >
                    Cancel
                </button>
                <button
                    type="submit"
                    className="flex-1 btn-primary flex items-center justify-center gap-2"
                    disabled={loading || rating === 0}
                >
                    {loading ? (
                        <>
                            <LoadingSpinner size="sm" />
                            Submitting...
                        </>
                    ) : (
                        'Submit Review'
                    )}
                </button>
            </div>
        </form>
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

export default ReviewForm;
