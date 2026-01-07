import type { Coach } from '../types';

interface CoachCardProps {
    coach: Coach;
    onBookClick: (coach: Coach) => void;
}

export const CoachCard = ({ coach, onBookClick }: CoachCardProps) => {
    const renderStars = (rating: number) => {
        const stars = [];
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;

        for (let i = 0; i < 5; i++) {
            if (i < fullStars) {
                stars.push(
                    <svg key={i} className="w-4 h-4 text-yellow-400 fill-current" viewBox="0 0 20 20">
                        <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                    </svg>
                );
            } else if (i === fullStars && hasHalfStar) {
                stars.push(
                    <svg key={i} className="w-4 h-4 text-yellow-400" viewBox="0 0 20 20">
                        <defs>
                            <linearGradient id={`half-${coach.id}`}>
                                <stop offset="50%" stopColor="currentColor" />
                                <stop offset="50%" stopColor="#374151" />
                            </linearGradient>
                        </defs>
                        <path fill={`url(#half-${coach.id})`} d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                    </svg>
                );
            } else {
                stars.push(
                    <svg key={i} className="w-4 h-4 text-gray-600 fill-current" viewBox="0 0 20 20">
                        <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                    </svg>
                );
            }
        }
        return stars;
    };

    return (
        <div className="bg-gray-800 rounded-xl overflow-hidden hover:ring-2 hover:ring-teal-500/50 transition-all duration-300 group">
            {/* Header with Avatar */}
            <div className="relative h-32 bg-gradient-to-br from-teal-600 to-teal-800">
                <div className="absolute -bottom-10 left-6">
                    <img
                        src={coach.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(coach.name)}&background=14b8a6&color=fff&size=80`}
                        alt={coach.name}
                        className="w-20 h-20 rounded-xl border-4 border-gray-800 object-cover bg-gray-700"
                    />
                </div>
                {coach.available && (
                    <div className="absolute top-4 right-4 px-3 py-1 bg-green-500/90 text-white text-xs font-semibold rounded-full flex items-center gap-1">
                        <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                        Available Now
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="pt-14 px-6 pb-6">
                <h3 className="text-xl font-bold text-white mb-1">{coach.name}</h3>

                {/* Rating */}
                <div className="flex items-center gap-2 mb-3">
                    <div className="flex">{renderStars(coach.rating)}</div>
                    <span className="text-sm text-gray-400">
                        {coach.rating.toFixed(1)} ({coach.reviews_count} reviews)
                    </span>
                </div>

                {/* Bio */}
                <p className="text-gray-400 text-sm mb-4 line-clamp-2">{coach.bio}</p>

                {/* Specializations */}
                <div className="flex flex-wrap gap-2 mb-4">
                    {coach.specialization.slice(0, 3).map((spec) => (
                        <span
                            key={spec}
                            className="px-2 py-1 bg-teal-500/20 text-teal-400 rounded-md text-xs font-medium"
                        >
                            {spec}
                        </span>
                    ))}
                    {coach.specialization.length > 3 && (
                        <span className="px-2 py-1 bg-gray-700 text-gray-400 rounded-md text-xs font-medium">
                            +{coach.specialization.length - 3} more
                        </span>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-4 border-t border-gray-700">
                    <div>
                        <span className="text-2xl font-bold text-white">${coach.hourly_rate}</span>
                        <span className="text-gray-500 text-sm">/hour</span>
                    </div>
                    <button
                        onClick={() => onBookClick(coach)}
                        className="btn-primary group-hover:shadow-lg group-hover:shadow-teal-500/25 transition-shadow"
                    >
                        Book Session
                    </button>
                </div>
            </div>
        </div>
    );
};

export default CoachCard;
