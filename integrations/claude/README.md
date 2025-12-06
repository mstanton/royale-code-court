# Claude Desktop Integration

This directory contains configuration for integrating Code Jester with Claude Desktop.

## Installation

1. **Install Code Jester with MCP support:**

   ```bash
   cd /path/to/royale-code-court
   pip install -e ".[mcp]"
   ```

2. **Locate your Claude Desktop config file:**

   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

3. **Add the Code Jester MCP server:**

   Open your Claude Desktop config and add (or merge) the following:

   ```json
   {
     "mcpServers": {
       "royale-code-court": {
         "command": "python",
         "args": ["-m", "jester.server.mcp"],
         "env": {
           "PYTHONPATH": "/path/to/royale-code-court"
         }
       }
     }
   }
   ```

   Replace `/path/to/royale-code-court` with the actual path to your installation.

4. **Restart Claude Desktop.**

## Verification

After restarting Claude Desktop, you should see the following tools available:

- `execute_code` - Execute Python code in a secure sandbox
- `validate_code` - Full code validation pipeline
- `analyze_error` - Analyze errors and suggest fixes
- `check_security` - Scan for security vulnerabilities
- `get_execution_stats` - View execution statistics

## Usage

Once configured, Claude will be able to:

1. **Validate code before presenting it to you:**
   - Ask Claude to write code
   - Claude uses `execute_code` to verify it works
   - You receive working, tested code

2. **Analyze errors:**
   - If code fails, Claude uses `analyze_error`
   - Gets specific fix suggestions
   - Applies fixes and retries

3. **Security checking:**
   - Uses `check_security` for sensitive code
   - Identifies SQL injection, command injection, etc.
   - Alerts you to potential vulnerabilities

## Example Prompts

Try these prompts in Claude Desktop:

- "Write a function to calculate fibonacci numbers, and verify it works"
- "Create a secure password validator and check it for security issues"
- "Write a sorting algorithm and benchmark its performance"

## Troubleshooting

### MCP server not connecting

1. Verify Python path is correct:
   ```bash
   which python
   ```

2. Verify jester is importable:
   ```bash
   python -c "from jester.server.mcp import main; print('OK')"
   ```

3. Check Claude Desktop logs for errors

### Tools not appearing

1. Ensure you restarted Claude Desktop after config changes
2. Verify the config JSON is valid
3. Check that the PYTHONPATH points to the correct directory

### Execution errors

1. MCP package may not be installed:
   ```bash
   pip install mcp
   ```

2. Try running the MCP server manually:
   ```bash
   python -m jester.server.mcp
   ```

## Security Notes

- Code execution is sandboxed with timeout limits
- Dangerous patterns (eval with input, exec) are blocked
- File system and network access are restricted in REPL mode
- Container mode provides additional isolation for complex code

## Configuration Options

You can customize the MCP server with environment variables:

```json
{
  "mcpServers": {
    "royale-code-court": {
      "command": "python",
      "args": ["-m", "jester.server.mcp"],
      "env": {
        "PYTHONPATH": "/path/to/royale-code-court",
        "JESTER_TIMEOUT": "10",
        "JESTER_DB_PATH": "~/.royale-code-court/metrics.db"
      }
    }
  }
}
```
