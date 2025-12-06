# Antimatter - VS Code Extension

**Validate AI-generated code before you trust it.**

Antimatter is a VS Code extension that integrates with [Royale Code Court](https://github.com/mstanton/royale-code-court) to validate, execute, and security-scan Python code directly in your editor.

## Features

### Code Validation
- **Validate Selection** (`Ctrl+Shift+V` / `Cmd+Shift+V`) - Validate selected code
- **Validate File** - Validate entire Python file
- Multi-stage validation: syntax, patterns, security, execution

### Secure Execution
- **Execute in Sandbox** (`Ctrl+Shift+X` / `Cmd+Shift+X`) - Run code in isolated environment
- Timeout protection
- Memory limits
- Blocked dangerous patterns

### Security Scanning
- Detect SQL injection patterns
- Detect command injection
- Detect hardcoded secrets
- OWASP top 10 vulnerability patterns

### Visual Feedback
- Inline validation results
- Status bar integration
- Diagnostics (Problems panel)
- Tree view for results, history, and patterns

## Installation

### From VSIX (Local Install)
```bash
cd integrations/vscode-antimatter
npm install
npm run compile
npx vsce package
code --install-extension antimatter-0.1.0.vsix
```

### Prerequisites
1. **Python 3.11+** with Royale Code Court installed:
   ```bash
   pip install -e /path/to/royale-code-court
   ```

2. **WebSocket support** (for server mode):
   ```bash
   pip install websockets
   ```

## Configuration

Open VS Code settings and search for "Antimatter":

| Setting | Default | Description |
|---------|---------|-------------|
| `antimatter.pythonPath` | `python` | Path to Python interpreter |
| `antimatter.jesterPath` | (auto) | Path to Royale Code Court installation |
| `antimatter.serverPort` | `8765` | WebSocket server port |
| `antimatter.autoStart` | `true` | Auto-start validation server |
| `antimatter.validateOnSave` | `false` | Validate on file save |
| `antimatter.showInlineResults` | `true` | Show inline decorations |
| `antimatter.executionTimeout` | `5` | Timeout in seconds |
| `antimatter.securityLevel` | `strict` | Security enforcement level |

## Commands

| Command | Keybinding | Description |
|---------|------------|-------------|
| Validate Selection | `Ctrl+Shift+V` | Validate selected code |
| Validate File | - | Validate entire file |
| Execute in Sandbox | `Ctrl+Shift+X` | Execute code safely |
| Security Scan | - | Check for vulnerabilities |
| Show Stats | - | View execution statistics |
| Start Server | - | Start validation server |
| Stop Server | - | Stop validation server |

## Usage

### Basic Validation
1. Select Python code in the editor
2. Press `Ctrl+Shift+V` (or right-click and select "Antimatter: Validate Selection")
3. View results in:
   - Status bar (quick status)
   - Problems panel (issues)
   - Antimatter panel (detailed view)

### Execute Code
1. Select Python code
2. Press `Ctrl+Shift+X`
3. View output in the Output panel

### Security Scanning
1. Select code to scan
2. Right-click and select "Antimatter: Security Scan"
3. View security report in panel

## Architecture

```
+----------------+     +------------------+     +------------------+
|   VS Code      |     |  Antimatter Ext  |     |  Jester Server   |
|   Editor       |<--->|  (TypeScript)    |<--->|  (Python)        |
+----------------+     +------------------+     +------------------+
                              |                        |
                              v                        v
                       WebSocket/Subprocess      Code Executor
                                                  (Sandbox)
```

### Communication Modes

1. **WebSocket Mode** (preferred)
   - Faster (persistent connection)
   - Requires server to be running
   - Auto-started on extension activation

2. **Subprocess Mode** (fallback)
   - Slower (new process per request)
   - Always available
   - No server required

## Views

### Validation Results
Shows the last validation result with:
- Overall status (PASSED/FAILED)
- Syntax validity
- Execution status
- Complexity score
- Issues and suggestions

### Execution History
Lists recent code executions with:
- Success/failure status
- Execution time
- Code preview

### Detected Patterns
Shows patterns found in validated code:
- Function definitions
- Class definitions
- List comprehensions
- Decorators
- Async patterns

## Troubleshooting

### Extension not activating
- Check Python is installed: `python --version`
- Check Jester is importable: `python -c "import jester"`

### Validation fails to connect
1. Check if server is running (status bar shows "Antimatter")
2. Try "Antimatter: Start Server" command
3. Check port 8765 is available

### Slow validation
- WebSocket mode is faster than subprocess mode
- Ensure server is running for best performance
- Complex code takes longer to analyze

### Security scan shows false positives
- Some patterns are heuristic-based
- Adjust `securityLevel` setting
- Review context before dismissing

## Development

### Building
```bash
cd integrations/vscode-antimatter
npm install
npm run compile
```

### Testing
```bash
npm test
```

### Packaging
```bash
npm run package
```

### Publishing
```bash
npm run publish
```

## License

MIT License - See [LICENSE](../../LICENSE)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests
5. Submit a pull request

---

*Antimatter - Because AI-generated code needs validation before production.*
