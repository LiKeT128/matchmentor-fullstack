import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useSubscription } from '../hooks/useSubscription';
import { LoadingSpinner } from '../components/LoadingSpinner';
import type { SubscriptionTier } from '../types';

const TIER_LABELS: Record<SubscriptionTier, string> = {
    free: 'Free',
    pro: 'Pro',
    premium: 'Premium',
};

const TIER_COLORS: Record<SubscriptionTier, string> = {
    free: 'bg-gray-500',
    pro: 'bg-teal-500',
    premium: 'bg-purple-500',
};

export const Account = () => {
    const {
        subscription,
        billingHistory,
        loading,
        error,
        fetchSubscription,
        fetchBillingHistory,
        cancelSubscription,
        resumeSubscription,
    } = useSubscription();

    const [showCancelModal, setShowCancelModal] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => {
        fetchSubscription();
        fetchBillingHistory();
    }, [fetchSubscription, fetchBillingHistory]);

    const handleCancelSubscription = async () => {
        setActionLoading(true);
        try {
            await cancelSubscription();
            setShowCancelModal(false);
        } catch {
            // Error handled by hook
        } finally {
            setActionLoading(false);
        }
    };

    const handleResumeSubscription = async () => {
        setActionLoading(true);
        try {
            await resumeSubscription();
        } catch {
            // Error handled by hook
        } finally {
            setActionLoading(false);
        }
    };

    if (loading && !subscription) {
        return (
            <div className="min-h-screen bg-gray-900 flex items-center justify-center pt-16">
                <div className="text-center">
                    <LoadingSpinner size="lg" className="mb-4" />
                    <p className="text-gray-400">Loading account...</p>
                </div>
            </div>
        );
    }

    const tier = subscription?.tier || 'free';
    const isActive = subscription?.status === 'active' || subscription?.status === 'trialing';
    const willCancel = subscription?.cancel_at_period_end;

    return (
        <div className="min-h-screen bg-gray-900 pt-24 pb-12 px-4">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-10">
                    <h1 className="text-3xl font-bold text-white mb-2">Account Settings</h1>
                    <p className="text-gray-400">Manage your subscription and billing</p>
                </div>

                {/* Error */}
                {error && (
                    <div className="mb-6 bg-red-500/20 border border-red-500/50 text-red-400 p-4 rounded-lg">
                        {error}
                    </div>
                )}

                {/* Current Plan */}
                <div className="bg-gray-800 rounded-xl p-6 mb-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <h2 className="text-xl font-semibold text-white">Current Plan</h2>
                                <span className={`px-3 py-1 rounded-full text-sm font-medium text-white ${TIER_COLORS[tier]}`}>
                                    {TIER_LABELS[tier]}
                                </span>
                                {isActive && !willCancel && (
                                    <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs font-medium">
                                        Active
                                    </span>
                                )}
                                {willCancel && (
                                    <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs font-medium">
                                        Canceling
                                    </span>
                                )}
                            </div>

                            {subscription && subscription.tier !== 'free' && (
                                <div className="text-gray-400 text-sm">
                                    {willCancel ? (
                                        <p>
                                            Your subscription will end on{' '}
                                            <span className="text-white">
                                                {new Date(subscription.current_period_end).toLocaleDateString()}
                                            </span>
                                        </p>
                                    ) : (
                                        <p>
                                            Renews on{' '}
                                            <span className="text-white">
                                                {new Date(subscription.current_period_end).toLocaleDateString()}
                                            </span>
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="flex gap-3">
                            {tier === 'free' && (
                                <Link to="/pricing" className="btn-primary">
                                    Upgrade Plan
                                </Link>
                            )}
                            {tier !== 'free' && !willCancel && (
                                <>
                                    <Link to="/pricing" className="btn-secondary">
                                        Change Plan
                                    </Link>
                                    <button
                                        onClick={() => setShowCancelModal(true)}
                                        className="px-4 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                                    >
                                        Cancel
                                    </button>
                                </>
                            )}
                            {willCancel && (
                                <button
                                    onClick={handleResumeSubscription}
                                    disabled={actionLoading}
                                    className="btn-primary flex items-center gap-2"
                                >
                                    {actionLoading ? <LoadingSpinner size="sm" /> : null}
                                    Resume Subscription
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Plan Features */}
                <div className="bg-gray-800 rounded-xl p-6 mb-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Your Plan Features</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <FeatureBox
                            icon={<AnalyticsIcon />}
                            label="Replay Analyses"
                            value={tier === 'free' ? '3/month' : 'Unlimited'}
                        />
                        <FeatureBox
                            icon={<InsightIcon />}
                            label="AI Insights"
                            value={tier === 'free' ? 'Basic' : 'Advanced'}
                        />
                        <FeatureBox
                            icon={<CoachIcon />}
                            label="Coaching Sessions"
                            value={tier === 'premium' ? '2/month' : tier === 'pro' ? 'Add-on' : '—'}
                        />
                        <FeatureBox
                            icon={<SupportIcon />}
                            label="Support"
                            value={tier === 'premium' ? 'Priority' : tier === 'pro' ? 'Email' : 'Community'}
                        />
                    </div>
                </div>

                {/* Billing History */}
                <div className="bg-gray-800 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Billing History</h2>
                    {billingHistory.length === 0 ? (
                        <p className="text-gray-400 text-center py-8">No billing history yet</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                                        <th className="pb-3 font-medium">Date</th>
                                        <th className="pb-3 font-medium">Description</th>
                                        <th className="pb-3 font-medium">Amount</th>
                                        <th className="pb-3 font-medium">Status</th>
                                        <th className="pb-3 font-medium"></th>
                                    </tr>
                                </thead>
                                <tbody className="text-sm">
                                    {billingHistory.map((item) => (
                                        <tr key={item.id} className="border-b border-gray-700/50">
                                            <td className="py-4 text-gray-300">
                                                {new Date(item.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="py-4 text-white">{item.description}</td>
                                            <td className="py-4 text-white">
                                                ${(item.amount / 100).toFixed(2)} {item.currency.toUpperCase()}
                                            </td>
                                            <td className="py-4">
                                                <span className={`px-2 py-1 rounded text-xs font-medium ${item.status === 'paid'
                                                    ? 'bg-green-500/20 text-green-400'
                                                    : item.status === 'pending'
                                                        ? 'bg-yellow-500/20 text-yellow-400'
                                                        : 'bg-red-500/20 text-red-400'
                                                    }`}>
                                                    {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                                                </span>
                                            </td>
                                            <td className="py-4">
                                                {item.invoice_url && (
                                                    <a
                                                        href={item.invoice_url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-teal-400 hover:text-teal-300"
                                                    >
                                                        View
                                                    </a>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* Cancel Modal */}
            {showCancelModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/70" onClick={() => setShowCancelModal(false)} />
                    <div className="relative bg-gray-800 rounded-xl p-6 max-w-md w-full">
                        <h3 className="text-xl font-bold text-white mb-4">Cancel Subscription?</h3>
                        <p className="text-gray-400 mb-6">
                            Are you sure you want to cancel? You'll lose access to premium features at the end of your billing period.
                        </p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowCancelModal(false)}
                                className="flex-1 btn-secondary"
                            >
                                Keep Plan
                            </button>
                            <button
                                onClick={handleCancelSubscription}
                                disabled={actionLoading}
                                className="flex-1 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                            >
                                {actionLoading ? <LoadingSpinner size="sm" /> : null}
                                Cancel Subscription
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

interface FeatureBoxProps {
    icon: ReactNode;
    label: string;
    value: string;
}

const FeatureBox = ({ icon, label, value }: FeatureBoxProps) => (
    <div className="bg-gray-700/50 rounded-lg p-4 text-center">
        <div className="w-10 h-10 bg-teal-500/20 rounded-lg flex items-center justify-center mx-auto mb-3 text-teal-400">
            {icon}
        </div>
        <p className="text-gray-400 text-xs mb-1">{label}</p>
        <p className="text-white font-semibold">{value}</p>
    </div>
);

const AnalyticsIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
);

const InsightIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
);

const CoachIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
);

const SupportIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
);

export default Account;
