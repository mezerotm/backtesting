# Security Guidelines

## Static File Serving

### ✅ SAFE TO SERVE
- `public/` directory - Contains only compiled/built assets safe for public access

### ❌ NEVER SERVE
- `server/` - Contains API source code, templates, configuration
- `utils/` - Contains utility modules, database clients
- `strategies/` - Contains trading strategy source code
- `workflows/` - Contains workflow source code
- `libs/` - Contains libraries, binaries, PocketBase
- `logs/` - Contains sensitive log files

## File Organization

### Source Code (Private)
```
server/          # API endpoints, templates, server logic
utils/           # Utility modules, database clients
strategies/      # Trading strategy implementations
workflows/       # Workflow definitions
libs/            # External libraries and binaries
logs/            # Application logs (sensitive)
```

### Public Assets (Safe to Serve)
```
public/          # Static files safe for public access
├── index.html   # Main dashboard
├── main.css     # Compiled styles
├── favicon.ico  # Site icon
├── js/          # Compiled JavaScript
├── data/        # Public data files
└── results/     # Public results
```

## Adding New Static Files

1. **Place files in `public/` directory**
2. **Reference as `/static/filename` in HTML/CSS/JS**
3. **Never reference source directories**

### Examples

✅ Correct:
```html
<link rel="stylesheet" href="/static/main.css">
<img src="/static/logo.png">
<script src="/static/js/app.js"></script>
```

❌ Incorrect:
```html
<link rel="stylesheet" href="/server/main.css">
<img src="/utils/logo.png">
<script src="/strategies/app.js"></script>
```

## FastAPI Configuration

The application uses this configuration in `server/api/main.py`:

```python
# ✅ CORRECT - Only serve public directory
app.mount("/static", StaticFiles(directory="public"), name="static")

# ❌ WRONG - Never do this
app.mount("/", StaticFiles(directory="server"), name="server")
app.mount("/utils", StaticFiles(directory="utils"), name="utils")
```

## Authentication & Session Security

### Session Management
- **Cookie-Based**: Uses secure HTTP-only cookies for session management
- **User Isolation**: All data operations are user-specific and properly isolated
- **Token Validation**: Robust token validation with PocketBase integration
- **Fresh Start Handling**: Graceful authentication failure handling during database resets

### Data Validation
- **Input Sanitization**: All incoming data is validated and sanitized
- **Symbol Validation**: Stock symbols are cleaned and validated
- **Data Range Checks**: Numerical values are validated for reasonable ranges
- **Malformed Data Handling**: Invalid records are logged and skipped, not causing failures

## Why This Matters

- **Source Code Exposure**: Serving source directories exposes business logic, API keys, and internal structure
- **Security Vulnerabilities**: Source code can reveal security weaknesses
- **Intellectual Property**: Trading strategies and algorithms should remain private
- **Configuration Exposure**: Database credentials and API keys could be exposed
- **Data Integrity**: User data must be properly isolated and validated
- **Session Security**: Authentication tokens must be handled securely

## Checklist for New Features

When adding new static assets:

- [ ] File placed in `public/` directory
- [ ] Referenced as `/static/filename`
- [ ] No source code directories referenced
- [ ] No sensitive information in public files
- [ ] Security review completed

When adding new API endpoints:

- [ ] User authentication required where appropriate
- [ ] Input validation and sanitization implemented
- [ ] User data isolation enforced
- [ ] Error handling includes proper logging
- [ ] Authentication failures logged as warnings (not errors) for expected cases

## Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** create a public issue
2. **DO** contact the maintainer privately
3. **DO** provide detailed reproduction steps
4. **DO** wait for acknowledgment before public disclosure 