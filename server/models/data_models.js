/**
 * Frontend Data Models and Schema Validation
 * 
 * This module defines the data structures and validation schemas for all collections
 * in the frontend application. It ensures consistency between frontend and backend
 * operations using AJV for JSON Schema validation.
 * 
 * Key Features:
 * - JSON Schema definitions that match backend Pydantic models
 * - Validation utilities for data integrity
 * - Type-safe data transformation
 * - Error handling for invalid data structures
 */

// Import AJV for JSON Schema validation
import Ajv from 'https://cdn.jsdelivr.net/npm/ajv@8/dist/ajv.min.mjs';

// Initialize AJV with custom options
const ajv = new Ajv({
    allErrors: true,
    verbose: true,
    strict: false,
    useDefaults: true
});

// Add custom formats if needed
ajv.addFormat('date', {
    type: 'string',
    validate: (date) => {
        return /^\d{4}-\d{2}-\d{2}$/.test(date) && !isNaN(Date.parse(date));
    }
});

// =============================================================================
// BASE SCHEMAS
// =============================================================================

const BaseRecordSchema = {
    type: 'object',
    properties: {
        id: { type: 'string' },
        created: { type: 'string' },
        updated: { type: 'string' }
    },
    additionalProperties: true
};

// =============================================================================
// PORTFOLIO SCHEMAS
// =============================================================================

const PortfolioSettingsSchema = {
    type: 'object',
    properties: {
        ...BaseRecordSchema.properties,
        user: { type: 'string' },
        total_portfolio_cash: { type: 'number', minimum: 0 },
        total_portfolio_btc: { type: 'number', minimum: 0 },
        btc_avg_buy_price: { type: 'number', minimum: 0 },
        robinhood_enabled: { type: 'boolean' },
        robinhood_display: { type: 'boolean' },
        robinhood_username: { type: 'string' },
        robinhood_password: { type: 'string' },
        robinhood_mfa: { type: 'string' },
        last_robinhood_pull: { type: 'string' },
        robinhood_last_successful_pull: { type: 'string' },
        robinhood_last_error: { type: 'string' }
    },
    required: ['user'],
    additionalProperties: true
};

const PositionSchema = {
    type: 'object',
    properties: {
        ...BaseRecordSchema.properties,
        user: { type: 'string' },
        symbol: { type: 'string', minLength: 1 },
        quantity: { type: 'number', minimum: 0 },
        buy_price: { type: 'number', minimum: 0 },
        notes: { type: 'string' },
        source: { type: 'string' },
        pulled_at: { type: 'string' },
        // Computed fields (not stored in DB)
        market_value: { type: 'number' },
        todays_return: { type: 'number' },
        total_return: { type: 'number' },
        beta: { type: 'number' },
        delta: { type: 'number' },
        percent_of_portfolio: { type: 'number' }
    },
    required: ['user', 'symbol', 'quantity', 'buy_price'],
    additionalProperties: true
};

// =============================================================================
// ORDER SCHEMAS
// =============================================================================

const OrderSchema = {
    type: 'object',
    properties: {
        ...BaseRecordSchema.properties,
        user: { type: 'string' },
        symbol: { type: 'string', minLength: 1 },
        type: { type: 'string', enum: ['buy', 'sell'] },
        quantity: { type: 'number', minimum: 0 },
        price: { type: 'number', minimum: 0 },
        date: { type: 'string', format: 'date' },
        fees: { type: 'number', minimum: 0, default: 0.0 },
        pl: { type: 'number' },
        source_id: { type: 'string' },
        notes: { type: 'string' },
        source: { type: 'string', default: 'manual' },
        pulled_at: { type: 'string' }
    },
    required: ['user', 'symbol', 'type', 'quantity', 'price', 'date'],
    additionalProperties: true
};

// =============================================================================
// DIVIDEND SCHEMAS
// =============================================================================

const DividendSchema = {
    type: 'object',
    properties: {
        ...BaseRecordSchema.properties,
        user: { type: 'string' },
        symbol: { type: 'string', minLength: 1 },
        amount: { type: 'number' },
        date: { type: 'string', format: 'date' },
        record_date: { type: 'string', format: 'date' },
        payable_date: { type: 'string', format: 'date' },
        state: { type: 'string', enum: ['paid', 'pending'] },
        source: { type: 'string', default: 'manual' },
        pulled_at: { type: 'string' }
    },
    required: ['user', 'symbol', 'amount', 'date'],
    additionalProperties: true
};

// =============================================================================
// SYMBOL CACHE SCHEMAS
// =============================================================================

const SymbolCacheSchema = {
    type: 'object',
    properties: {
        ...BaseRecordSchema.properties,
        symbol: { type: 'string', minLength: 1 },
        price: { type: 'number', minimum: 0 },
        date: { type: 'string', format: 'date' },
        beta: { type: 'number' },
        delta: { type: 'number' }
    },
    required: ['symbol', 'date'],
    additionalProperties: true
};

// =============================================================================
// PROFIT/LOSS SCHEMAS
// =============================================================================

const ProfitLossSchema = {
    type: 'object',
    properties: {
        ...BaseRecordSchema.properties,
        user: { type: 'string' },
        symbol: { type: 'string', minLength: 1 },
        type: { type: 'string', enum: ['Unrealized', 'Realized'] },
        amount: { type: 'number' },
        period: { type: 'string', enum: ['1W', '1M', '3M', 'YTD', 'MAX'] },
        date: { type: 'string', format: 'date' },
        calculated_at: { type: 'string' },
        source: { type: 'string', default: 'manual' }
    },
    required: ['user', 'symbol', 'type', 'amount'],
    additionalProperties: true
};

const ProfitLossCacheSchema = {
    type: 'object',
    properties: {
        ...BaseRecordSchema.properties,
        user: { type: 'string' },
        period: { type: 'string', enum: ['1W', '1M', '3M', 'YTD', 'MAX'] },
        total: { type: 'number' },
        unrealized: { type: 'number' },
        realized: { type: 'number' },
        calculated_at: { type: 'string' },
        last_updated: { type: 'string' }
    },
    required: ['user', 'period', 'total', 'unrealized', 'realized', 'calculated_at', 'last_updated'],
    additionalProperties: true
};

// =============================================================================
// FRONTEND DATA SCHEMAS
// =============================================================================

const PortfolioSummarySchema = {
    type: 'object',
    properties: {
        positions: {
            type: 'array',
            items: PositionSchema
        },
        total_value: { type: 'number', minimum: 0 },
        total_cash: { type: 'number', minimum: 0 },
        total_btc: { type: 'number', minimum: 0 },
        btc_avg_price: { type: 'number', minimum: 0 }
    },
    required: ['positions', 'total_value', 'total_cash', 'total_btc', 'btc_avg_price'],
    additionalProperties: true
};

const MarketDataSchema = {
    type: 'object',
    properties: {
        symbol: { type: 'string', minLength: 1 },
        last_price: { type: 'number', minimum: 0 },
        previous_close: { type: 'number', minimum: 0 },
        change: { type: 'number' },
        change_percent: { type: 'number' },
        volume: { type: 'number', minimum: 0 },
        beta: { type: 'number' },
        timestamp: { type: 'string' }
    },
    required: ['symbol'],
    additionalProperties: true
};

// =============================================================================
// API RESPONSE SCHEMAS
// =============================================================================

const OrdersResponseSchema = {
    type: 'object',
    properties: {
        orders: {
            type: 'array',
            items: OrderSchema
        }
    },
    required: ['orders'],
    additionalProperties: true
};

const DividendsResponseSchema = {
    type: 'array',
    items: DividendSchema
};

const ProfitLossSummarySchema = {
    type: 'object',
    properties: {
        total: { type: 'number' },
        unrealized: { type: 'number' },
        realized: { type: 'number' },
        calculated_at: { type: 'string' },
        period: { type: 'string', enum: ['1W', '1M', '3M', 'YTD', 'MAX'] }
    },
    required: ['total', 'unrealized', 'realized', 'calculated_at', 'period'],
    additionalProperties: true
};

const ProfitLossDetailsSchema = {
    type: 'array',
    items: {
        type: 'object',
        properties: {
            symbol: { type: 'string' },
            type: { type: 'string', enum: ['Unrealized', 'Realized'] },
            amount: { type: 'number' }
        },
        required: ['symbol', 'type', 'amount'],
        additionalProperties: true
    }
};

// =============================================================================
// SCHEMA REGISTRY
// =============================================================================

const SCHEMA_REGISTRY = {
    'portfolio': PortfolioSettingsSchema,
    'positions': PositionSchema,
    'orders': OrderSchema,
    'dividends': DividendSchema,
    'symbol_cache': SymbolCacheSchema,
    'profit_loss': ProfitLossSchema,
    'profit_loss_cache': ProfitLossCacheSchema,
    'portfolio_summary': PortfolioSummarySchema,
    'market_data': MarketDataSchema,
    'orders_response': OrdersResponseSchema,
    'dividends_response': DividendsResponseSchema,
    'profit_loss_summary': ProfitLossSummarySchema,
    'profit_loss_details': ProfitLossDetailsSchema
};

// =============================================================================
// VALIDATION UTILITIES
// =============================================================================

/**
 * Validate data against a schema
 * @param {string|object} schema - Schema name or schema object
 * @param {any} data - Data to validate
 * @returns {object} - Validation result with success, errors, and validated data
 */
function validateData(schema, data) {
    try {
        // Get schema by name if string provided
        const schemaObj = typeof schema === 'string' ? SCHEMA_REGISTRY[schema] : schema;
        
        if (!schemaObj) {
            return {
                success: false,
                errors: [`Schema '${schema}' not found`],
                data: null
            };
        }

        // Compile and validate
        const validate = ajv.compile(schemaObj);
        const isValid = validate(data);

        if (isValid) {
            return {
                success: true,
                errors: [],
                data: data
            };
        } else {
            return {
                success: false,
                errors: validate.errors.map(err => `${err.instancePath} ${err.message}`),
                data: null
            };
        }
    } catch (error) {
        return {
            success: false,
            errors: [`Validation error: ${error.message}`],
            data: null
        };
    }
}

/**
 * Validate and transform data to ensure it matches expected structure
 * @param {string|object} schema - Schema name or schema object
 * @param {any} data - Data to validate and transform
 * @returns {object} - Validation result with success, errors, and transformed data
 */
function validateAndTransform(schema, data) {
    const result = validateData(schema, data);
    
    if (result.success) {
        // Apply defaults and transformations
        const schemaObj = typeof schema === 'string' ? SCHEMA_REGISTRY[schema] : schema;
        const transformed = { ...data };
        
        // Apply defaults
        if (schemaObj.properties) {
            Object.keys(schemaObj.properties).forEach(key => {
                const prop = schemaObj.properties[key];
                if (prop.default !== undefined && transformed[key] === undefined) {
                    transformed[key] = prop.default;
                }
            });
        }
        
        return {
            success: true,
            errors: [],
            data: transformed
        };
    }
    
    return result;
}

/**
 * Safe data access with validation
 * @param {string|object} schema - Schema name or schema object
 * @param {any} data - Data to validate
 * @param {function} callback - Function to call with validated data
 * @param {function} errorCallback - Function to call on validation error
 */
function withValidatedData(schema, data, callback, errorCallback) {
    const result = validateData(schema, data);
    
    if (result.success) {
        return callback(result.data);
    } else {
        console.error('Data validation failed:', result.errors);
        if (errorCallback) {
            return errorCallback(result.errors);
        }
        return null;
    }
}

/**
 * Validate API response data
 * @param {string} endpoint - API endpoint name
 * @param {any} data - Response data to validate
 * @returns {object} - Validation result
 */
function validateApiResponse(endpoint, data) {
    const schemaMap = {
        '/api/portfolio/summary': 'portfolio_summary',
        '/api/orders': 'orders_response',
        '/api/dividends/received': 'dividends_response',
        '/api/profit-loss/summary': 'profit_loss_summary',
        '/api/profit-loss/details': 'profit_loss_details'
    };
    
    const schemaName = schemaMap[endpoint];
    if (!schemaName) {
        console.warn(`No validation schema found for endpoint: ${endpoint}`);
        return { success: true, errors: [], data: data };
    }
    
    return validateData(schemaName, data);
}

// =============================================================================
// ERROR HANDLING UTILITIES
// =============================================================================

/**
 * Create a user-friendly error message from validation errors
 * @param {Array} errors - Validation errors
 * @returns {string} - User-friendly error message
 */
function formatValidationErrors(errors) {
    if (!errors || errors.length === 0) {
        return 'Unknown validation error';
    }
    
    return errors.map(error => {
        // Clean up error messages for user display
        return error
            .replace(/^\./, '') // Remove leading dot
            .replace(/^/, '• ') // Add bullet point
            .replace(/^• \//, '• '); // Clean up path references
    }).join('\n');
}

/**
 * Handle validation errors gracefully
 * @param {Array} errors - Validation errors
 * @param {string} context - Context for error logging
 */
function handleValidationError(errors, context = 'Data validation') {
    const errorMessage = formatValidationErrors(errors);
    console.error(`${context} failed:`, errorMessage);
    
    // Show user notification if available
    if (window.Utils && window.Utils.showNotification) {
        window.Utils.showNotification(`Data validation failed: ${errorMessage}`, 'error');
    }
}

// =============================================================================
// EXPORTS
// =============================================================================

export {
    // Schemas
    PortfolioSettingsSchema,
    PositionSchema,
    OrderSchema,
    DividendSchema,
    SymbolCacheSchema,
    ProfitLossSchema,
    ProfitLossCacheSchema,
    PortfolioSummarySchema,
    MarketDataSchema,
    OrdersResponseSchema,
    DividendsResponseSchema,
    ProfitLossSummarySchema,
    ProfitLossDetailsSchema,
    
    // Registry
    SCHEMA_REGISTRY,
    
    // Utilities
    validateData,
    validateAndTransform,
    withValidatedData,
    validateApiResponse,
    formatValidationErrors,
    handleValidationError,
    
    // AJV instance for advanced usage
    ajv
};

// Also export for global use
if (typeof window !== 'undefined') {
    window.DataModels = {
        validateData,
        validateAndTransform,
        withValidatedData,
        validateApiResponse,
        formatValidationErrors,
        handleValidationError,
        SCHEMA_REGISTRY,
        ajv
    };
} 