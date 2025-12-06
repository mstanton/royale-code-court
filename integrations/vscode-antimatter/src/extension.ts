/**
 * Antimatter - VS Code Extension for Royale Code Court
 *
 * Validates AI-generated code before you trust it.
 * Provides inline validation, security scanning, and execution in a secure sandbox.
 */

import * as vscode from 'vscode';
import { JesterClient } from './client';
import { ValidationResultsProvider } from './providers/validationResults';
import { ExecutionHistoryProvider } from './providers/executionHistory';
import { PatternsProvider } from './providers/patterns';
import { DiagnosticsManager } from './diagnostics';
import { CodeLensProvider } from './providers/codeLens';
import { StatusBarManager } from './statusBar';

let client: JesterClient;
let diagnosticsManager: DiagnosticsManager;
let statusBarManager: StatusBarManager;
let validationResultsProvider: ValidationResultsProvider;
let executionHistoryProvider: ExecutionHistoryProvider;
let patternsProvider: PatternsProvider;

export async function activate(context: vscode.ExtensionContext) {
    console.log('Antimatter extension is activating...');

    // Initialize components
    const config = vscode.workspace.getConfiguration('antimatter');

    client = new JesterClient(
        config.get('pythonPath', 'python'),
        config.get('jesterPath', ''),
        config.get('serverPort', 8765)
    );

    diagnosticsManager = new DiagnosticsManager();
    statusBarManager = new StatusBarManager();

    // Initialize tree view providers
    validationResultsProvider = new ValidationResultsProvider();
    executionHistoryProvider = new ExecutionHistoryProvider();
    patternsProvider = new PatternsProvider();

    // Register tree views
    vscode.window.registerTreeDataProvider('antimatter.validationResults', validationResultsProvider);
    vscode.window.registerTreeDataProvider('antimatter.executionHistory', executionHistoryProvider);
    vscode.window.registerTreeDataProvider('antimatter.patterns', patternsProvider);

    // Register CodeLens provider
    const codeLensProvider = new CodeLensProvider(client);
    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider(
            { language: 'python', scheme: 'file' },
            codeLensProvider
        )
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('antimatter.validateSelection', () => validateSelection()),
        vscode.commands.registerCommand('antimatter.validateFile', () => validateFile()),
        vscode.commands.registerCommand('antimatter.executeCode', () => executeCode()),
        vscode.commands.registerCommand('antimatter.checkSecurity', () => checkSecurity()),
        vscode.commands.registerCommand('antimatter.showStats', () => showStats()),
        vscode.commands.registerCommand('antimatter.startServer', () => startServer()),
        vscode.commands.registerCommand('antimatter.stopServer', () => stopServer()),
        vscode.commands.registerCommand('antimatter.showValidationDetails', (result) => showValidationDetails(result))
    );

    // Auto-start server if configured
    if (config.get('autoStart', true)) {
        try {
            await startServer();
        } catch (error) {
            console.error('Failed to auto-start Antimatter server:', error);
        }
    }

    // Register on-save validation if configured
    if (config.get('validateOnSave', false)) {
        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(async (document) => {
                if (document.languageId === 'python') {
                    await validateDocument(document);
                }
            })
        );
    }

    // Register diagnostics
    context.subscriptions.push(diagnosticsManager.diagnosticCollection);

    // Register status bar
    context.subscriptions.push(statusBarManager.statusBarItem);

    console.log('Antimatter extension activated successfully');
}

export function deactivate() {
    if (client) {
        client.disconnect();
    }
}

// Command implementations

async function validateSelection(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    if (selection.isEmpty) {
        vscode.window.showWarningMessage('No code selected. Select code to validate.');
        return;
    }

    const code = editor.document.getText(selection);
    await validateCode(code, editor.document, selection.start.line);
}

async function validateFile(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    await validateDocument(editor.document);
}

async function validateDocument(document: vscode.TextDocument): Promise<void> {
    const code = document.getText();
    await validateCode(code, document, 0);
}

async function validateCode(code: string, document: vscode.TextDocument, startLine: number): Promise<void> {
    statusBarManager.showValidating();

    try {
        if (!client.isConnected()) {
            const connected = await client.connect();
            if (!connected) {
                vscode.window.showErrorMessage('Antimatter: Could not connect to validation server. Try starting it with "Antimatter: Start Validation Server"');
                statusBarManager.showError();
                return;
            }
        }

        const result = await client.validateCode(code);

        // Update diagnostics
        diagnosticsManager.updateDiagnostics(document, result, startLine);

        // Update tree views
        validationResultsProvider.setResults(result);
        if (result.patterns_detected) {
            patternsProvider.setPatterns(result.patterns_detected);
        }

        // Show status
        if (result.overall_success) {
            statusBarManager.showSuccess();
            vscode.window.showInformationMessage(
                `Antimatter: Code validated successfully! (${result.execution_time_ms?.toFixed(1) || 0}ms)`
            );
        } else {
            statusBarManager.showError();
            const issues = result.issues?.join(', ') || 'Unknown issues';
            vscode.window.showWarningMessage(`Antimatter: Validation failed - ${issues}`);
        }

        // Show inline decorations if configured
        const config = vscode.workspace.getConfiguration('antimatter');
        if (config.get('showInlineResults', true)) {
            showInlineResults(document, result, startLine);
        }

    } catch (error) {
        statusBarManager.showError();
        vscode.window.showErrorMessage(`Antimatter: Validation error - ${error}`);
    }
}

async function executeCode(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    const code = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);

    statusBarManager.showExecuting();

    try {
        if (!client.isConnected()) {
            await client.connect();
        }

        const result = await client.executeCode(code);

        // Add to execution history
        executionHistoryProvider.addExecution({
            timestamp: new Date(),
            code: code.substring(0, 100) + (code.length > 100 ? '...' : ''),
            success: result.success,
            output: result.output,
            error: result.error,
            time_ms: result.execution_time_ms
        });

        if (result.success) {
            statusBarManager.showSuccess();

            // Show output in output channel
            const outputChannel = vscode.window.createOutputChannel('Antimatter Execution');
            outputChannel.clear();
            outputChannel.appendLine('=== Antimatter Execution Result ===');
            outputChannel.appendLine(`Status: SUCCESS`);
            outputChannel.appendLine(`Time: ${result.execution_time_ms?.toFixed(1) || 0}ms`);
            outputChannel.appendLine(`Tier: ${result.tier || 'repl'}`);
            outputChannel.appendLine('');
            outputChannel.appendLine('--- Output ---');
            outputChannel.appendLine(result.output || '(no output)');
            outputChannel.show();

        } else {
            statusBarManager.showError();

            const outputChannel = vscode.window.createOutputChannel('Antimatter Execution');
            outputChannel.clear();
            outputChannel.appendLine('=== Antimatter Execution Result ===');
            outputChannel.appendLine(`Status: FAILED`);
            outputChannel.appendLine('');
            outputChannel.appendLine('--- Error ---');
            outputChannel.appendLine(result.error || 'Unknown error');
            outputChannel.show();
        }

    } catch (error) {
        statusBarManager.showError();
        vscode.window.showErrorMessage(`Antimatter: Execution error - ${error}`);
    }
}

async function checkSecurity(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    const code = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);

    statusBarManager.showValidating();

    try {
        if (!client.isConnected()) {
            await client.connect();
        }

        const result = await client.checkSecurity(code);

        if (result.issues && result.issues.length > 0) {
            statusBarManager.showWarning();

            // Show security issues in a webview panel
            const panel = vscode.window.createWebviewPanel(
                'antimatterSecurity',
                'Antimatter Security Report',
                vscode.ViewColumn.Beside,
                {}
            );

            panel.webview.html = getSecurityReportHtml(result.issues);

        } else {
            statusBarManager.showSuccess();
            vscode.window.showInformationMessage('Antimatter: No security issues detected!');
        }

    } catch (error) {
        statusBarManager.showError();
        vscode.window.showErrorMessage(`Antimatter: Security check error - ${error}`);
    }
}

async function showStats(): Promise<void> {
    try {
        if (!client.isConnected()) {
            await client.connect();
        }

        const stats = await client.getStats();

        const panel = vscode.window.createWebviewPanel(
            'antimatterStats',
            'Antimatter Statistics',
            vscode.ViewColumn.Beside,
            {}
        );

        panel.webview.html = getStatsHtml(stats);

    } catch (error) {
        vscode.window.showErrorMessage(`Antimatter: Could not fetch stats - ${error}`);
    }
}

async function startServer(): Promise<void> {
    statusBarManager.showStarting();

    try {
        const started = await client.startServer();
        if (started) {
            statusBarManager.showReady();
            vscode.window.showInformationMessage('Antimatter: Validation server started');
        } else {
            statusBarManager.showError();
            vscode.window.showErrorMessage('Antimatter: Could not start validation server');
        }
    } catch (error) {
        statusBarManager.showError();
        vscode.window.showErrorMessage(`Antimatter: Server start error - ${error}`);
    }
}

async function stopServer(): Promise<void> {
    try {
        await client.stopServer();
        statusBarManager.showDisconnected();
        vscode.window.showInformationMessage('Antimatter: Validation server stopped');
    } catch (error) {
        vscode.window.showErrorMessage(`Antimatter: Server stop error - ${error}`);
    }
}

function showValidationDetails(result: any): void {
    const panel = vscode.window.createWebviewPanel(
        'antimatterValidation',
        'Validation Details',
        vscode.ViewColumn.Beside,
        {}
    );

    panel.webview.html = getValidationDetailsHtml(result);
}

function showInlineResults(document: vscode.TextDocument, result: any, startLine: number): void {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }

    // Create decorations based on result
    const successDecorationType = vscode.window.createTextEditorDecorationType({
        backgroundColor: new vscode.ThemeColor('antimatter.validBackground'),
        isWholeLine: true,
        overviewRulerColor: 'green',
        overviewRulerLane: vscode.OverviewRulerLane.Right
    });

    const errorDecorationType = vscode.window.createTextEditorDecorationType({
        backgroundColor: new vscode.ThemeColor('antimatter.invalidBackground'),
        isWholeLine: true,
        overviewRulerColor: 'red',
        overviewRulerLane: vscode.OverviewRulerLane.Right
    });

    if (result.overall_success) {
        // Highlight successful validation briefly
        const range = new vscode.Range(startLine, 0, startLine, 0);
        editor.setDecorations(successDecorationType, [range]);

        setTimeout(() => {
            editor.setDecorations(successDecorationType, []);
        }, 2000);
    } else {
        // Highlight errors
        const range = new vscode.Range(startLine, 0, startLine, 0);
        editor.setDecorations(errorDecorationType, [range]);

        setTimeout(() => {
            editor.setDecorations(errorDecorationType, []);
        }, 5000);
    }
}

// HTML generators for webview panels

function getSecurityReportHtml(issues: any[]): string {
    const issueRows = issues.map(issue => `
        <tr class="${issue.severity}">
            <td><span class="severity ${issue.severity}">${issue.severity?.toUpperCase() || 'UNKNOWN'}</span></td>
            <td>${issue.description || issue}</td>
            <td>${issue.pattern || '-'}</td>
        </tr>
    `).join('');

    return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        h1 { color: var(--vscode-foreground); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid var(--vscode-panel-border); }
        th { background: var(--vscode-editor-background); }
        .severity { padding: 2px 8px; border-radius: 4px; font-weight: bold; }
        .severity.critical { background: #dc3545; color: white; }
        .severity.high { background: #fd7e14; color: white; }
        .severity.medium { background: #ffc107; color: black; }
        .severity.low { background: #17a2b8; color: white; }
    </style>
</head>
<body>
    <h1>Security Report</h1>
    <p>Found ${issues.length} potential security issue(s)</p>
    <table>
        <tr>
            <th>Severity</th>
            <th>Description</th>
            <th>Pattern</th>
        </tr>
        ${issueRows}
    </table>
</body>
</html>`;
}

function getStatsHtml(stats: any): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        h1, h2 { color: var(--vscode-foreground); }
        .stat-card {
            background: var(--vscode-editor-background);
            padding: 20px;
            margin: 10px 0;
            border-radius: 8px;
            border: 1px solid var(--vscode-panel-border);
        }
        .stat-value { font-size: 2em; font-weight: bold; color: var(--vscode-textLink-foreground); }
        .stat-label { color: var(--vscode-descriptionForeground); }
    </style>
</head>
<body>
    <h1>Antimatter Statistics</h1>

    <div class="stat-card">
        <div class="stat-value">${stats.total_executions || 0}</div>
        <div class="stat-label">Total Executions</div>
    </div>

    <div class="stat-card">
        <div class="stat-value">${((stats.success_rate || 0) * 100).toFixed(1)}%</div>
        <div class="stat-label">Success Rate</div>
    </div>

    <div class="stat-card">
        <div class="stat-value">${(stats.avg_execution_time_ms || 0).toFixed(1)}ms</div>
        <div class="stat-label">Average Execution Time</div>
    </div>

    <h2>Learned Patterns</h2>
    <p>${stats.learned_patterns || 0} patterns recognized</p>
</body>
</html>`;
}

function getValidationDetailsHtml(result: any): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        h1, h2 { color: var(--vscode-foreground); }
        .status { padding: 10px; border-radius: 4px; margin-bottom: 20px; }
        .status.success { background: #1a472a; color: #90ee90; }
        .status.failure { background: #472a2a; color: #ff6b6b; }
        .section { margin: 20px 0; }
        .label { color: var(--vscode-descriptionForeground); }
        .value { color: var(--vscode-foreground); }
        ul { padding-left: 20px; }
        pre { background: var(--vscode-editor-background); padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Validation Details</h1>

    <div class="status ${result.overall_success ? 'success' : 'failure'}">
        ${result.overall_success ? 'PASSED' : 'FAILED'}
    </div>

    <div class="section">
        <span class="label">Syntax Valid:</span>
        <span class="value">${result.syntax_valid ? 'Yes' : 'No'}</span>
    </div>

    <div class="section">
        <span class="label">Executes:</span>
        <span class="value">${result.executes ? 'Yes' : 'No'}</span>
    </div>

    <div class="section">
        <span class="label">Complexity:</span>
        <span class="value">${result.complexity_score || 0}</span>
    </div>

    ${result.patterns_detected?.length ? `
    <h2>Patterns Detected</h2>
    <ul>
        ${result.patterns_detected.map((p: string) => `<li>${p}</li>`).join('')}
    </ul>
    ` : ''}

    ${result.issues?.length ? `
    <h2>Issues</h2>
    <ul>
        ${result.issues.map((i: string) => `<li>${i}</li>`).join('')}
    </ul>
    ` : ''}

    ${result.suggestions?.length ? `
    <h2>Suggestions</h2>
    <ul>
        ${result.suggestions.map((s: string) => `<li>${s}</li>`).join('')}
    </ul>
    ` : ''}

    ${result.execution_output ? `
    <h2>Execution Output</h2>
    <pre>${result.execution_output}</pre>
    ` : ''}
</body>
</html>`;
}
