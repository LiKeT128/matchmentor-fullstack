import type { Review } from '../types';

interface ReviewListProps {
    reviews: Review[];
}

export const ReviewList = ({ reviews }: ReviewListProps) => {
    if (!reviews || reviews.length === 0) {
        return (
            <div className="text-center py-8 text-gray-400">
                No reviews yet. Be the first to leave a review!
            </div>
        );
    }

    const renderStars = (rating: number) => {
        return (
            <div className="flex gap-0.5">
                {[1, 2, 3, 4, 5].map((star) => (
                    <svg
                        key={star}
                        className={`w-4 h-4 ${star <= rating ? 'text-yellow-400' : 'text-gray-600'}`}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                    >
                        <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                    </svg>
                ))}
            </div>
        );
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    return (
        <div className="space-y-4">
            {reviews.map((review) => (
                <div key={review.id} className="bg-gray-700/50 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-teal-500/20 rounded-full flex items-center justify-center">
                                <span className="text-teal-400 font-semibold">
                                    {review.user_email?.charAt(0).toUpperCase() || 'U'}
                                </span>
                            </div>
                            <div>
                                <p className="text-white font-medium">
                                    {review.user_email?.split('@')[0] || 'Anonymous'}
                                </p>
                                <p className="text-gray-500 text-xs">{formatDate(review.created_at)}</p>
                            </div>
                        </div>
                        {renderStars(review.rating)}
                    </div>
                    <p className="text-gray-300">{review.comment}</p>
                </div>
            ))}
        </div>
    );
};

export default ReviewList;
