import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useSubscription } from '../hooks/useSubscription';
import { LoadingSpinner } from '../components/LoadingSpinner';
import type { SubscriptionTier } from '../types';

interface PricingTier {
    id: string;
    name: string;
    tier: SubscriptionTier;
    price: number;
    interval: 'month';
    description: string;
    features: string[];
    highlighted?: boolean;
    stripePriceId: string;
}

const PRICING_TIERS: PricingTier[] = [
    {
        id: 'free',
        name: 'Free',
        tier: 'free',
        price: 0,
        interval: 'month',
        description: 'Get started with basic replay analysis',
        stripePriceId: '',
        features: [
            '3 replay analyses per month',
            'Basic statistics',
            'Performance summary',
            'Community support',
        ],
    },
    {
        id: 'pro',
        name: 'Pro',
        tier: 'pro',
        price: 9.99,
        interval: 'month',
        description: 'For dedicated players who want to improve',
        highlighted: true,
        stripePriceId: 'price_pro_monthly',
        features: [
            'Unlimited replay analyses',
            'Advanced statistics',
            'AI-powered insights',
            'Hero-specific tips',
            'Priority support',
            'Export to PDF',
        ],
    },
    {
        id: 'premium',
        name: 'Premium',
        tier: 'premium',
        price: 24.99,
        interval: 'month',
        description: 'The ultimate coaching experience',
        stripePriceId: 'price_premium_monthly',
        features: [
            'Everything in Pro',
            '2 coaching sessions/month',
            'Personalized training plan',
            'Direct coach messaging',
            'VOD reviews',
            'Priority queue',
            'Early access to features',
        ],
    },
];

export const Pricing = () => {
    const { isAuthenticated } = useAuth();
    const { createCheckoutSession, loading } = useSubscription();
    const navigate = useNavigate();
    const [processingTier, setProcessingTier] = useState<string | null>(null);

    const handleSelectPlan = async (tier: PricingTier) => {
        if (!isAuthenticated) {
            navigate('/register');
            return;
        }

        if (tier.tier === 'free') {
            navigate('/account');
            return;
        }

        setProcessingTier(tier.id);
        try {
            const checkoutUrl = await createCheckoutSession(tier.stripePriceId);
            window.location.href = checkoutUrl;
        } catch {
            // Error handled by hook
        } finally {
            setProcessingTier(null);
        }
    };

    return (
        <div className="min-h-screen bg-gray-900 pt-24 pb-16 px-4">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="text-center mb-16">
                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                        Choose Your Plan
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                        Unlock powerful analytics and coaching to take your Dota 2 gameplay to the next level
                    </p>
                </div>

                {/* Pricing Cards */}
                <div className="grid md:grid-cols-3 gap-8 mb-16">
                    {PRICING_TIERS.map((tier) => (
                        <div
                            key={tier.id}
                            className={`relative rounded-2xl p-8 transition-transform hover:scale-105 ${tier.highlighted
                                    ? 'bg-gradient-to-b from-teal-900/50 to-gray-800 ring-2 ring-teal-500'
                                    : 'bg-gray-800'
                                }`}
                        >
                            {tier.highlighted && (
                                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-teal-500 text-white text-sm font-semibold rounded-full">
                                    Most Popular
                                </div>
                            )}

                            <div className="mb-6">
                                <h3 className="text-2xl font-bold text-white mb-2">{tier.name}</h3>
                                <p className="text-gray-400 text-sm">{tier.description}</p>
                            </div>

                            <div className="mb-6">
                                <span className="text-4xl font-bold text-white">
                                    ${tier.price}
                                </span>
                                {tier.price > 0 && (
                                    <span className="text-gray-400">/{tier.interval}</span>
                                )}
                            </div>

                            <ul className="space-y-3 mb-8">
                                {tier.features.map((feature, index) => (
                                    <li key={index} className="flex items-start gap-3">
                                        <svg
                                            className="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                        >
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth={2}
                                                d="M5 13l4 4L19 7"
                                            />
                                        </svg>
                                        <span className="text-gray-300">{feature}</span>
                                    </li>
                                ))}
                            </ul>

                            <button
                                onClick={() => handleSelectPlan(tier)}
                                disabled={loading && processingTier === tier.id}
                                className={`w-full py-3 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${tier.highlighted
                                        ? 'bg-teal-500 hover:bg-teal-600 text-white'
                                        : 'bg-gray-700 hover:bg-gray-600 text-white'
                                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                {loading && processingTier === tier.id ? (
                                    <>
                                        <LoadingSpinner size="sm" />
                                        Processing...
                                    </>
                                ) : tier.price === 0 ? (
                                    'Get Started'
                                ) : (
                                    `Upgrade to ${tier.name}`
                                )}
                            </button>
                        </div>
                    ))}
                </div>

                {/* FAQ Section */}
                <div className="max-w-3xl mx-auto">
                    <h2 className="text-2xl font-bold text-white text-center mb-8">
                        Frequently Asked Questions
                    </h2>
                    <div className="space-y-4">
                        <FaqItem
                            question="Can I cancel my subscription anytime?"
                            answer="Yes! You can cancel your subscription at any time from your account page. You'll continue to have access until the end of your billing period."
                        />
                        <FaqItem
                            question="How do coaching sessions work with Premium?"
                            answer="Premium members get 2 one-hour coaching sessions per month. You can book these through our coaches marketplace with any available coach."
                        />
                        <FaqItem
                            question="Can I upgrade or downgrade my plan?"
                            answer="Absolutely! You can change your plan at any time. When upgrading, you'll be charged the prorated difference. When downgrading, changes take effect at your next billing cycle."
                        />
                        <FaqItem
                            question="Is there a free trial?"
                            answer="The Free tier lets you try our basic features. When you're ready for more, upgrade to Pro or Premium to unlock the full experience."
                        />
                    </div>
                </div>

                {/* CTA */}
                {!isAuthenticated && (
                    <div className="text-center mt-16">
                        <p className="text-gray-400 mb-4">
                            Already have an account?{' '}
                            <Link to="/login" className="text-teal-400 hover:text-teal-300 font-medium">
                                Sign in
                            </Link>
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

interface FaqItemProps {
    question: string;
    answer: string;
}

const FaqItem = ({ question, answer }: FaqItemProps) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-6 py-4 flex items-center justify-between text-left"
            >
                <span className="font-medium text-white">{question}</span>
                <svg
                    className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>
            {isOpen && (
                <div className="px-6 pb-4">
                    <p className="text-gray-400">{answer}</p>
                </div>
            )}
        </div>
    );
};

export default Pricing;
