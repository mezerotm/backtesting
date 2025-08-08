// Frontend logging service
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

export interface LogEntry {
  timestamp: string
  level: LogLevel
  category: string
  message: string
  data?: any
  userId?: string
  sessionId?: string
}

class Logger {
  private logs: LogEntry[] = []
  private maxLogs = 1000
  private currentLevel = LogLevel.INFO
  private sessionId = this.generateSessionId()
  private userId?: string

  private generateSessionId(): string {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
  }

  setUserId(userId: string) {
    this.userId = userId
  }

  setLevel(level: LogLevel) {
    this.currentLevel = level
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.currentLevel
  }

  private addLog(level: LogLevel, category: string, message: string, data?: any) {
    if (!this.shouldLog(level)) return

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      category,
      message,
      data,
      userId: this.userId,
      sessionId: this.sessionId
    }

    this.logs.push(entry)

    // Keep only the last maxLogs entries
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs)
    }

    // Also log to console for development
    if (import.meta.env.DEV) {
      const levelNames = ['DEBUG', 'INFO', 'WARN', 'ERROR']
      const consoleMethod = level === LogLevel.ERROR ? 'error' : 
                           level === LogLevel.WARN ? 'warn' : 
                           level === LogLevel.DEBUG ? 'debug' : 'log'
      
      console[consoleMethod](`[${levelNames[level]}] [${category}] ${message}`, data || '')
    }
  }

  debug(category: string, message: string, data?: any) {
    this.addLog(LogLevel.DEBUG, category, message, data)
  }

  info(category: string, message: string, data?: any) {
    this.addLog(LogLevel.INFO, category, message, data)
  }

  warn(category: string, message: string, data?: any) {
    this.addLog(LogLevel.WARN, category, message, data)
  }

  error(category: string, message: string, data?: any) {
    this.addLog(LogLevel.ERROR, category, message, data)
  }

  // API-specific logging
  apiRequest(method: string, url: string, data?: any) {
    this.info('API', `${method} ${url}`, data)
  }

  apiResponse(method: string, url: string, status: number, data?: any) {
    if (status >= 400) {
      this.error('API', `${method} ${url} - Status: ${status}`, data)
    } else {
      this.info('API', `${method} ${url} - Status: ${status}`, data)
    }
  }

  apiError(method: string, url: string, error: any) {
    this.error('API', `${method} ${url} - Error`, error)
  }

  // Widget-specific logging
  widgetAction(widget: string, action: string, data?: any) {
    this.info('Widget', `${widget}: ${action}`, data)
  }

  widgetError(widget: string, action: string, error: any) {
    this.error('Widget', `${widget}: ${action} - Error`, error)
  }

  // Auth-specific logging
  authAction(action: string, data?: any) {
    this.info('Auth', action, data)
  }

  authError(action: string, error: any) {
    this.error('Auth', `${action} - Error`, error)
  }

  // Get logs for debugging
  getLogs(): LogEntry[] {
    return [...this.logs]
  }

  // Get logs by level
  getLogsByLevel(level: LogLevel): LogEntry[] {
    return this.logs.filter(log => log.level === level)
  }

  // Get logs by category
  getLogsByCategory(category: string): LogEntry[] {
    return this.logs.filter(log => log.category === category)
  }

  // Clear logs
  clearLogs() {
    this.logs = []
  }

  // Export logs as JSON
  exportLogs(): string {
    return JSON.stringify({
      sessionId: this.sessionId,
      userId: this.userId,
      timestamp: new Date().toISOString(),
      logs: this.logs
    }, null, 2)
  }

  // Send logs to backend (for production debugging)
  async sendLogsToBackend() {
    try {
      const logsData = this.exportLogs()
      const response = await fetch('/api/logs/frontend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: logsData
      })
      
      if (response.ok) {
        this.info('Logger', 'Logs sent to backend successfully')
      } else {
        this.error('Logger', 'Failed to send logs to backend', { status: response.status })
      }
    } catch (error) {
      this.error('Logger', 'Error sending logs to backend', error)
    }
  }
}

// Create singleton instance
export const logger = new Logger()

// Export convenience functions
export const logDebug = (category: string, message: string, data?: any) => logger.debug(category, message, data)
export const logInfo = (category: string, message: string, data?: any) => logger.info(category, message, data)
export const logWarn = (category: string, message: string, data?: any) => logger.warn(category, message, data)
export const logError = (category: string, message: string, data?: any) => logger.error(category, message, data)

// Export API logging functions
export const logApiRequest = (method: string, url: string, data?: any) => logger.apiRequest(method, url, data)
export const logApiResponse = (method: string, url: string, status: number, data?: any) => logger.apiResponse(method, url, status, data)
export const logApiError = (method: string, url: string, error: any) => logger.apiError(method, url, error)

// Export widget logging functions
export const logWidgetAction = (widget: string, action: string, data?: any) => logger.widgetAction(widget, action, data)
export const logWidgetError = (widget: string, action: string, error: any) => logger.widgetError(widget, action, error)

// Export auth logging functions
export const logAuthAction = (action: string, data?: any) => logger.authAction(action, data)
export const logAuthError = (action: string, error: any) => logger.authError(action, error) 