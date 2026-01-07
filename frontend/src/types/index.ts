// Authentication types
export interface User {
    id: string;
    email: string;
    created_at: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user?: User;
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterCredentials {
    email: string;
    password: string;
}

// Match types
export interface Match {
    id: string;
    user_id: string;
    filename: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
}

export interface MatchAnalysis {
    match_id: string;
    hero: string;
    duration: number;
    result: 'win' | 'loss';
    kills: number;
    deaths: number;
    assists: number;
    gpm: number;
    xpm: number;
    last_hits: number;
    denies: number;
    insights: AnalysisInsight[];
    created_at: string;
}

export interface AnalysisInsight {
    type: 'tip' | 'improvement' | 'strength' | 'weakness';
    category: string;
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high';
}

export interface UploadResponse {
    match_id: string;
    status: string;
    message: string;
}

// Coach types
export interface Coach {
    id: string;
    name: string;
    avatar_url: string;
    specialization: string[];
    rating: number;
    reviews_count: number;
    hourly_rate: number;
    bio: string;
    available: boolean;
}

// Booking types
export interface Booking {
    id: string;
    coach_id: string;
    user_id: string;
    date: string;
    time: string;
    duration: number; // in minutes
    status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
    payment_status: 'pending' | 'paid' | 'refunded';
    total_amount: number;
    created_at: string;
}

export interface BookingRequest {
    coach_id: string;
    date: string;
    time: string;
    duration: number;
}

export interface TimeSlot {
    time: string;
    available: boolean;
}

export interface AvailabilityResponse {
    date: string;
    slots: TimeSlot[];
}

// Review types
export interface Review {
    id: string;
    coach_id: string;
    user_id: string;
    user_email?: string;
    rating: number;
    comment: string;
    created_at: string;
}

export interface ReviewRequest {
    coach_id: string;
    booking_id: string;
    rating: number;
    comment: string;
}

// Payment types
export interface PaymentIntent {
    client_secret: string;
    amount: number;
    currency: string;
}

// Subscription types
export type SubscriptionTier = 'free' | 'pro' | 'premium';

export interface Subscription {
    id: string;
    user_id: string;
    tier: SubscriptionTier;
    status: 'active' | 'canceled' | 'past_due' | 'trialing';
    current_period_start: string;
    current_period_end: string;
    cancel_at_period_end: boolean;
    stripe_customer_id?: string;
    stripe_subscription_id?: string;
}

export interface PricingPlan {
    id: string;
    name: string;
    tier: SubscriptionTier;
    price: number;
    interval: 'month' | 'year';
    features: string[];
    highlighted?: boolean;
    stripe_price_id: string;
}

export interface BillingHistory {
    id: string;
    amount: number;
    currency: string;
    status: 'paid' | 'pending' | 'failed';
    description: string;
    invoice_url?: string;
    created_at: string;
}

// API Error type
export interface ApiError {
    detail: string;
    status_code?: number;
}

