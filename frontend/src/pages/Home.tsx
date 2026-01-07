import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export const Home = () => {
    const { isAuthenticated } = useAuth();

    return (
        <div className="min-h-screen bg-gray-900 text-white pt-16">
            {/* Hero Section */}
            <section className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-teal-500/10 to-purple-500/10" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-teal-500/20 rounded-full blur-3xl" />

                <div className="relative max-w-6xl mx-auto px-4 py-24 sm:py-32">
                    <div className="text-center">
                        <h1 className="text-5xl sm:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-teal-200 to-teal-400 bg-clip-text text-transparent">
                            Analyze Your Dota 2 Replays
                        </h1>
                        <p className="text-xl sm:text-2xl text-gray-300 mb-8 max-w-2xl mx-auto">
                            Get detailed analysis of your matches with AI-powered insights.
                            Improve your gameplay and climb the ranks.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            {isAuthenticated ? (
                                <Link to="/upload" className="btn-primary text-lg px-8 py-4">
                                    Upload Replay
                                </Link>
                            ) : (
                                <>
                                    <Link to="/register" className="btn-primary text-lg px-8 py-4">
                                        Get Started Free
                                    </Link>
                                    <Link to="/login" className="btn-secondary text-lg px-8 py-4">
                                        Sign In
                                    </Link>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-24 bg-gray-800/50">
                <div className="max-w-6xl mx-auto px-4">
                    <h2 className="text-3xl sm:text-4xl font-bold text-center mb-16">
                        Why Choose MatchMentor?
                    </h2>
                    <div className="grid md:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                            }
                            title="Detailed Statistics"
                            description="Get comprehensive stats including GPM, XPM, last hits, denies, and more for every match."
                        />
                        <FeatureCard
                            icon={
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            }
                            title="AI-Powered Insights"
                            description="Receive personalized tips and improvement suggestions based on your gameplay patterns."
                        />
                        <FeatureCard
                            icon={
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                                </svg>
                            }
                            title="Pro Coaching"
                            description="Connect with experienced coaches to take your skills to the next level."
                        />
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-24">
                <div className="max-w-4xl mx-auto px-4 text-center">
                    <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                        Ready to Improve Your Game?
                    </h2>
                    <p className="text-xl text-gray-300 mb-8">
                        Join thousands of players who have improved their Dota 2 skills with MatchMentor.
                    </p>
                    {!isAuthenticated && (
                        <Link to="/register" className="btn-primary text-lg px-8 py-4">
                            Start Analyzing for Free
                        </Link>
                    )}
                </div>
            </section>
        </div>
    );
};

interface FeatureCardProps {
    icon: ReactNode;
    title: string;
    description: string;
}

const FeatureCard = ({ icon, title, description }: FeatureCardProps) => (
    <div className="card text-center hover:scale-105 transition-transform duration-300">
        <div className="w-16 h-16 bg-teal-500/20 rounded-xl flex items-center justify-center mx-auto mb-6 text-teal-400">
            {icon}
        </div>
        <h3 className="text-xl font-semibold mb-3">{title}</h3>
        <p className="text-gray-400">{description}</p>
    </div>
);

export default Home;
