import { useEffect, useState, useMemo } from 'react';
import { useCoaches } from '../hooks/useCoaches';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { CoachCard } from '../components/CoachCard';
import { BookingModal } from '../components/BookingModal';
import type { Coach } from '../types';

export const Coaches = () => {
    const { coaches, loading, error, fetchCoaches } = useCoaches();
    const [searchQuery, setSearchQuery] = useState('');
    const [specializationFilter, setSpecializationFilter] = useState<string>('');
    const [minRatingFilter, setMinRatingFilter] = useState<number>(0);
    const [maxPriceFilter, setMaxPriceFilter] = useState<number>(0);
    const [availableOnly, setAvailableOnly] = useState(false);
    const [sortBy, setSortBy] = useState<'rating' | 'price_low' | 'price_high' | 'reviews'>('rating');

    // Booking modal state
    const [selectedCoach, setSelectedCoach] = useState<Coach | null>(null);
    const [showBookingModal, setShowBookingModal] = useState(false);
    const [bookingSuccess, setBookingSuccess] = useState(false);

    useEffect(() => {
        fetchCoaches();
    }, [fetchCoaches]);

    // Get unique specializations from coaches
    const allSpecializations = useMemo(() => {
        const specs = new Set<string>();
        coaches.forEach((coach) => {
            coach.specialization.forEach((s) => specs.add(s));
        });
        return Array.from(specs).sort();
    }, [coaches]);

    // Filter and sort coaches
    const filteredCoaches = useMemo(() => {
        let result = [...coaches];

        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            result = result.filter(
                (coach) =>
                    coach.name.toLowerCase().includes(query) ||
                    coach.bio.toLowerCase().includes(query) ||
                    coach.specialization.some((s) => s.toLowerCase().includes(query))
            );
        }

        // Specialization filter
        if (specializationFilter) {
            result = result.filter((coach) =>
                coach.specialization.includes(specializationFilter)
            );
        }

        // Min rating filter
        if (minRatingFilter > 0) {
            result = result.filter((coach) => coach.rating >= minRatingFilter);
        }

        // Max price filter
        if (maxPriceFilter > 0) {
            result = result.filter((coach) => coach.hourly_rate <= maxPriceFilter);
        }

        // Available only filter
        if (availableOnly) {
            result = result.filter((coach) => coach.available);
        }

        // Sort
        switch (sortBy) {
            case 'rating':
                result.sort((a, b) => b.rating - a.rating);
                break;
            case 'price_low':
                result.sort((a, b) => a.hourly_rate - b.hourly_rate);
                break;
            case 'price_high':
                result.sort((a, b) => b.hourly_rate - a.hourly_rate);
                break;
            case 'reviews':
                result.sort((a, b) => b.reviews_count - a.reviews_count);
                break;
        }

        return result;
    }, [coaches, searchQuery, specializationFilter, minRatingFilter, maxPriceFilter, availableOnly, sortBy]);

    const handleBookClick = (coach: Coach) => {
        setSelectedCoach(coach);
        setShowBookingModal(true);
        setBookingSuccess(false);
    };

    const handleBookingSuccess = () => {
        setBookingSuccess(true);
        setShowBookingModal(false);
    };

    const clearFilters = () => {
        setSearchQuery('');
        setSpecializationFilter('');
        setMinRatingFilter(0);
        setMaxPriceFilter(0);
        setAvailableOnly(false);
        setSortBy('rating');
    };

    const hasActiveFilters = searchQuery || specializationFilter || minRatingFilter > 0 || maxPriceFilter > 0 || availableOnly;

    return (
        <div className="min-h-screen bg-gray-900 pt-24 pb-12 px-4">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="text-center mb-10">
                    <h1 className="text-4xl font-bold text-white mb-4">Find Your Coach</h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                        Connect with experienced Dota 2 coaches to accelerate your improvement and reach your goals
                    </p>
                </div>

                {/* Success Message */}
                {bookingSuccess && (
                    <div className="mb-6 bg-green-500/20 border border-green-500/50 text-green-400 p-4 rounded-lg flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            <span>Booking confirmed! Check your email for session details.</span>
                        </div>
                        <button onClick={() => setBookingSuccess(false)} className="text-green-400 hover:text-green-300">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                )}

                {/* Search and Filters */}
                <div className="bg-gray-800 rounded-xl p-6 mb-8">
                    {/* Search Bar */}
                    <div className="relative mb-6">
                        <svg
                            className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search coaches by name, specialty, or keyword..."
                            className="w-full pl-12 pr-4 py-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                        />
                    </div>

                    {/* Filters Row */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                        {/* Specialization */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">Specialization</label>
                            <select
                                value={specializationFilter}
                                onChange={(e) => setSpecializationFilter(e.target.value)}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-teal-500 focus:outline-none"
                            >
                                <option value="">All</option>
                                {allSpecializations.map((spec) => (
                                    <option key={spec} value={spec}>{spec}</option>
                                ))}
                            </select>
                        </div>

                        {/* Min Rating */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">Min Rating</label>
                            <select
                                value={minRatingFilter}
                                onChange={(e) => setMinRatingFilter(Number(e.target.value))}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-teal-500 focus:outline-none"
                            >
                                <option value={0}>Any</option>
                                <option value={4.5}>4.5+ ⭐</option>
                                <option value={4}>4+ ⭐</option>
                                <option value={3.5}>3.5+ ⭐</option>
                            </select>
                        </div>

                        {/* Max Price */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">Max Price</label>
                            <select
                                value={maxPriceFilter}
                                onChange={(e) => setMaxPriceFilter(Number(e.target.value))}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-teal-500 focus:outline-none"
                            >
                                <option value={0}>Any</option>
                                <option value={25}>Under $25/hr</option>
                                <option value={50}>Under $50/hr</option>
                                <option value={75}>Under $75/hr</option>
                                <option value={100}>Under $100/hr</option>
                            </select>
                        </div>

                        {/* Sort By */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">Sort By</label>
                            <select
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-teal-500 focus:outline-none"
                            >
                                <option value="rating">Highest Rated</option>
                                <option value="reviews">Most Reviews</option>
                                <option value="price_low">Price: Low to High</option>
                                <option value="price_high">Price: High to Low</option>
                            </select>
                        </div>

                        {/* Available Toggle */}
                        <div className="flex items-end">
                            <label className="flex items-center gap-3 cursor-pointer w-full px-3 py-2 bg-gray-700 rounded-lg border border-gray-600">
                                <input
                                    type="checkbox"
                                    checked={availableOnly}
                                    onChange={(e) => setAvailableOnly(e.target.checked)}
                                    className="w-5 h-5 rounded bg-gray-600 border-gray-500 text-teal-500 focus:ring-teal-500"
                                />
                                <span className="text-gray-300 text-sm">Available now</span>
                            </label>
                        </div>
                    </div>

                    {/* Clear Filters */}
                    {hasActiveFilters && (
                        <div className="mt-4 flex items-center justify-between">
                            <p className="text-gray-400 text-sm">
                                Showing {filteredCoaches.length} of {coaches.length} coaches
                            </p>
                            <button
                                onClick={clearFilters}
                                className="text-teal-400 hover:text-teal-300 text-sm font-medium flex items-center gap-1"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                                Clear all filters
                            </button>
                        </div>
                    )}
                </div>

                {/* Error State */}
                {error && (
                    <div className="bg-red-500/20 border border-red-500/50 text-red-400 p-4 rounded-lg mb-6 flex items-center gap-3">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {error}
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div className="flex flex-col items-center justify-center py-16">
                        <LoadingSpinner size="lg" className="mb-4" />
                        <p className="text-gray-400">Loading coaches...</p>
                    </div>
                )}

                {/* Empty State */}
                {!loading && filteredCoaches.length === 0 && (
                    <div className="text-center py-16">
                        <div className="w-20 h-20 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-6">
                            <svg className="w-10 h-10 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </div>
                        <h3 className="text-xl font-semibold text-white mb-2">No coaches found</h3>
                        <p className="text-gray-400 mb-6">Try adjusting your filters or search query</p>
                        {hasActiveFilters && (
                            <button onClick={clearFilters} className="btn-primary">
                                Clear Filters
                            </button>
                        )}
                    </div>
                )}

                {/* Coach Grid */}
                {!loading && filteredCoaches.length > 0 && (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredCoaches.map((coach) => (
                            <CoachCard
                                key={coach.id}
                                coach={coach}
                                onBookClick={handleBookClick}
                            />
                        ))}
                    </div>
                )}

                {/* Booking Modal */}
                {selectedCoach && (
                    <BookingModal
                        coach={selectedCoach}
                        isOpen={showBookingModal}
                        onClose={() => setShowBookingModal(false)}
                        onSuccess={handleBookingSuccess}
                    />
                )}
            </div>
        </div>
    );
};

export default Coaches;
