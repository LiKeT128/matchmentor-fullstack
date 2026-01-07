interface Advice {
    id?: string | number;
    category: string;
    title: string;
    description: string;
    priority?: string; // Made optional - backend may return invalid/missing values
    type?: 'tip' | 'improvement' | 'strength' | 'weakness';
}

interface AdviceListProps {
    advice: Advice[];
}

export const AdviceList = ({ advice }: AdviceListProps) => {
    if (!advice || advice.length === 0) {
        return (
            <div className="bg-gray-800 rounded-xl p-8 text-center">
                <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                </div>
                <p className="text-gray-400">No advice available for this match</p>
            </div>
        );
    }

    const priorityConfig = {
        high: {
            border: 'border-l-red-500',
            badge: 'bg-red-500/20 text-red-400',
            icon: '🔴',
        },
        medium: {
            border: 'border-l-yellow-500',
            badge: 'bg-yellow-500/20 text-yellow-400',
            icon: '🟡',
        },
        low: {
            border: 'border-l-green-500',
            badge: 'bg-green-500/20 text-green-400',
            icon: '🟢',
        },
    };

    const typeConfig = {
        tip: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'Tip' },
        improvement: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Improvement' },
        strength: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'Strength' },
        weakness: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Weakness' },
    };

    // Helper to get valid priority key
    const getValidPriority = (p: string | undefined): 'high' | 'medium' | 'low' => {
        if (p === 'high' || p === 'medium' || p === 'low') return p;
        return 'low'; // Default to low if invalid/missing
    };

    // Sort advice by priority (high first)
    const sortedAdvice = [...advice].sort((a, b) => {
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        return priorityOrder[getValidPriority(a.priority)] - priorityOrder[getValidPriority(b.priority)];
    });

    return (
        <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <svg className="w-6 h-6 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Insights & Recommendations
            </h2>
            <div className="space-y-4">
                {sortedAdvice.map((item, index) => {
                    const validPriority = getValidPriority(item.priority);
                    const priority = priorityConfig[validPriority];
                    const type = item.type ? typeConfig[item.type] : null;

                    return (
                        <div
                            key={item.id || index}
                            className={`bg-gray-800 rounded-xl p-5 border-l-4 ${priority.border} hover:bg-gray-800/80 transition-colors`}
                        >
                            <div className="flex flex-wrap items-start gap-3 mb-3">
                                {/* Category Badge */}
                                <span className="px-3 py-1 bg-gray-700 rounded-full text-sm text-gray-300 font-medium">
                                    {item.category}
                                </span>

                                {/* Type Badge (if present) */}
                                {type && (
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${type.bg} ${type.text}`}>
                                        {type.label}
                                    </span>
                                )}

                                {/* Priority Badge */}
                                <span className={`px-3 py-1 rounded-full text-sm font-medium ${priority.badge}`}>
                                    {priority.icon} {validPriority.charAt(0).toUpperCase() + validPriority.slice(1)} Priority
                                </span>
                            </div>

                            <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                            <p className="text-gray-400 leading-relaxed">{item.description}</p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default AdviceList;
