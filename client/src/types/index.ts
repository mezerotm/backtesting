// User types
export interface User {
  id: string
  email: string
  created_at: string
  updated_at: string
}

// Portfolio types

/**
 * Position interface for frontend display.
 * Note: Some field names differ from backend for historical/display reasons:
 * Frontend    | Backend
 * ------------|------------
 * amount      | quantity
 * avg_buy_price| buy_price
 * created_at  | pulled_at
 */
export interface Position {
    id: string
    symbol: string
    amount: number            // Maps to backend "quantity"
    avg_buy_price: number     // Maps to backend "buy_price"
    market_value: number
    current_price?: number
    percent_of_portfolio: number
    todays_return: number
    total_return: number
    total_return_percent: number
    beta: number
    delta: number
    notes?: string
    is_crypto: boolean
    badges?: string[]
    created_at: string       // Maps to backend "pulled_at"
    updated_at: string
    is_cash?: boolean        // Special flag for CASH styling
    is_btc?: boolean         // Special flag for BTC styling
}

// Validation types for Position fields
export const PositionValidation = {
    symbol: {
        maxLength: 10,
        pattern: /^[A-Z0-9.-]+$/
    },
    amount: {
        min: 0.00000001,
        max: 1_000_000_000,
        decimals: 8  // 8 decimals for crypto
    },
    avg_buy_price: {
        min: 0.00000001,
        max: 1_000_000,
        decimals: 8  // 8 decimals for crypto
    },
    market_value: {
        min: 0,
        max: 1_000_000,
        decimals: 2
    },
    percent_of_portfolio: {
        min: -100_000,
        max: 100_000,
        decimals: 4
    },
    beta: {
        min: -10,
        max: 10,
        decimals: 4
    },
    delta: {
        min: -10,
        max: 10,
        decimals: 4
    },
    notes: {
        maxLength: 1000
    }
} as const;

export type PositionSource = 'manual' | 'robinhood' | 'api';

// Portfolio settings types
export interface PortfolioSettings {
    total_portfolio_cash: number
    total_portfolio_btc: number
    btc_avg_buy_price: number
    robinhood_enabled?: boolean
    robinhood_username?: string
    robinhood_password?: string
    robinhood_mfa?: string
}

export interface PortfolioSummary {
    positions: Position[]
    total_value: number
    total_cash: number
    total_btc: number
    btc_avg_price: number
}

// Market data types
export interface RateLimitStats {
  requests_in_last_minute: number
  requests_in_last_hour: number
  last_request_time: string
  rate_limit_exceeded: boolean
}

export interface MarketDataResponse {
  success: boolean
  data?: any
  error?: string
}

// Workflow types
export interface WorkflowResponse {
  success: boolean
  message: string
  data?: any
  error?: string
}

// Toast types
export interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  timestamp: Date
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// Form types
export interface LoginForm {
  email: string
  password: string
}

export interface RegisterForm extends LoginForm {
  confirmPassword: string
}

export interface PortfolioSettingsForm {
  cash: number
  btcDollar: number
  btcAvgBuyPrice: number
}

// Component props types
export interface WidgetProps {
  title?: string
  loading?: boolean
  error?: string
}

// Event types
export interface SortEvent {
  column: string
  direction: 'asc' | 'desc' | 'none'
}



// Utility types
export type SortDirection = 'asc' | 'desc' | 'none'
export type ToastType = 'success' | 'error' | 'warning' | 'info'
export type BadgeType = 'crypto' | 'robinhood' | 'stock' 