import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { LoadingSpinner } from './LoadingSpinner';
import type { Coach, TimeSlot } from '../types';

interface BookingModalProps {
    coach: Coach;
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export const BookingModal = ({ coach, isOpen, onClose, onSuccess }: BookingModalProps) => {
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [selectedTime, setSelectedTime] = useState<string>('');
    const [duration, setDuration] = useState<number>(60);
    const [slots, setSlots] = useState<TimeSlot[]>([]);
    const [loading, setLoading] = useState(false);
    const [loadingSlots, setLoadingSlots] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [step, setStep] = useState<'select' | 'confirm' | 'payment'>('select');

    // Get available dates (next 14 days)
    const getAvailableDates = () => {
        const dates = [];
        const today = new Date();
        for (let i = 1; i <= 14; i++) {
            const date = new Date(today);
            date.setDate(today.getDate() + i);
            dates.push(date.toISOString().split('T')[0]);
        }
        return dates;
    };

    // Fetch available slots when date changes
    useEffect(() => {
        if (selectedDate) {
            fetchAvailableSlots();
        }
    }, [selectedDate]);

    const fetchAvailableSlots = async () => {
        setLoadingSlots(true);
        setSelectedTime('');
        try {
            const { data } = await api.get(`/api/coaches/${coach.id}/availability`, {
                params: { date: selectedDate },
            });
            setSlots(data.slots || []);
        } catch {
            // Default slots if API fails
            setSlots([
                { time: '09:00', available: true },
                { time: '10:00', available: true },
                { time: '11:00', available: true },
                { time: '14:00', available: true },
                { time: '15:00', available: true },
                { time: '16:00', available: true },
                { time: '17:00', available: true },
            ]);
        } finally {
            setLoadingSlots(false);
        }
    };

    const handleContinue = () => {
        if (step === 'select') {
            setStep('confirm');
        } else if (step === 'confirm') {
            setStep('payment');
            handleBooking();
        }
    };

    const handleBooking = async () => {
        setLoading(true);
        setError(null);

        try {
            await api.post('/api/bookings', {
                coach_id: coach.id,
                date: selectedDate,
                time: selectedTime,
                duration,
            });
            onSuccess();
            onClose();
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Booking failed. Please try again.');
            setError(message);
            setStep('confirm');
        } finally {
            setLoading(false);
        }
    };

    const totalAmount = (coach.hourly_rate * duration) / 60;

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-gray-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="sticky top-0 bg-gray-800 px-6 py-4 border-b border-gray-700 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Book a Session</h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Coach Info */}
                <div className="px-6 py-4 border-b border-gray-700">
                    <div className="flex items-center gap-4">
                        <img
                            src={coach.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(coach.name)}&background=14b8a6&color=fff`}
                            alt={coach.name}
                            className="w-14 h-14 rounded-xl object-cover bg-gray-700"
                        />
                        <div>
                            <h3 className="font-semibold text-white">{coach.name}</h3>
                            <p className="text-gray-400 text-sm">${coach.hourly_rate}/hour</p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="px-6 py-6">
                    {error && (
                        <div className="mb-4 bg-red-500/20 border border-red-500/50 text-red-400 p-3 rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    {step === 'select' && (
                        <div className="space-y-6">
                            {/* Date Selection */}
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-3">
                                    Select Date
                                </label>
                                <div className="grid grid-cols-4 gap-2">
                                    {getAvailableDates().slice(0, 8).map((date) => {
                                        const d = new Date(date);
                                        const dayName = d.toLocaleDateString('en-US', { weekday: 'short' });
                                        const dayNum = d.getDate();

                                        return (
                                            <button
                                                key={date}
                                                onClick={() => setSelectedDate(date)}
                                                className={`p-3 rounded-lg text-center transition-all ${selectedDate === date
                                                        ? 'bg-teal-500 text-white'
                                                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                                    }`}
                                            >
                                                <div className="text-xs opacity-75">{dayName}</div>
                                                <div className="text-lg font-bold">{dayNum}</div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Time Selection */}
                            {selectedDate && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-3">
                                        Select Time
                                    </label>
                                    {loadingSlots ? (
                                        <div className="flex justify-center py-4">
                                            <LoadingSpinner size="md" />
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-4 gap-2">
                                            {slots.map((slot) => (
                                                <button
                                                    key={slot.time}
                                                    onClick={() => slot.available && setSelectedTime(slot.time)}
                                                    disabled={!slot.available}
                                                    className={`p-3 rounded-lg text-center transition-all ${selectedTime === slot.time
                                                            ? 'bg-teal-500 text-white'
                                                            : slot.available
                                                                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                                                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
                                                        }`}
                                                >
                                                    {slot.time}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Duration Selection */}
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-3">
                                    Session Duration
                                </label>
                                <div className="grid grid-cols-3 gap-2">
                                    {[30, 60, 90].map((mins) => (
                                        <button
                                            key={mins}
                                            onClick={() => setDuration(mins)}
                                            className={`p-3 rounded-lg text-center transition-all ${duration === mins
                                                    ? 'bg-teal-500 text-white'
                                                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                                }`}
                                        >
                                            {mins} min
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 'confirm' && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white mb-4">Confirm Your Booking</h3>

                            <div className="bg-gray-700/50 rounded-lg p-4 space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Date</span>
                                    <span className="text-white font-medium">
                                        {new Date(selectedDate).toLocaleDateString('en-US', {
                                            weekday: 'long',
                                            month: 'short',
                                            day: 'numeric',
                                        })}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Time</span>
                                    <span className="text-white font-medium">{selectedTime}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Duration</span>
                                    <span className="text-white font-medium">{duration} minutes</span>
                                </div>
                                <div className="border-t border-gray-600 pt-3 flex justify-between">
                                    <span className="text-gray-400">Total</span>
                                    <span className="text-xl font-bold text-teal-400">${totalAmount.toFixed(2)}</span>
                                </div>
                            </div>

                            <p className="text-gray-400 text-sm">
                                You will receive a confirmation email with session details and a link to join.
                            </p>
                        </div>
                    )}

                    {step === 'payment' && (
                        <div className="flex flex-col items-center py-8">
                            <LoadingSpinner size="lg" className="mb-4" />
                            <p className="text-gray-300">Processing your booking...</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                {step !== 'payment' && (
                    <div className="px-6 py-4 border-t border-gray-700 flex gap-3">
                        {step === 'confirm' && (
                            <button
                                onClick={() => setStep('select')}
                                className="flex-1 btn-secondary"
                            >
                                Back
                            </button>
                        )}
                        <button
                            onClick={handleContinue}
                            disabled={!selectedDate || !selectedTime || loading}
                            className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {step === 'select' ? 'Continue' : `Pay $${totalAmount.toFixed(2)}`}
                        </button>
                    </div>
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

export default BookingModal;
