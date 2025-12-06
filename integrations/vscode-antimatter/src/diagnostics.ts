/**
 * DiagnosticsManager - Manages VS Code diagnostics for validation results
 */

import * as vscode from 'vscode';
import { ValidationResult } from './client';

export class DiagnosticsManager {
    public diagnosticCollection: vscode.DiagnosticCollection;

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('antimatter');
    }

    updateDiagnostics(document: vscode.TextDocument, result: ValidationResult, startLine: number): void {
        const diagnostics: vscode.Diagnostic[] = [];

        // Add syntax errors
        if (!result.syntax_valid && result.issues) {
            for (const issue of result.issues) {
                if (issue.toLowerCase().includes('syntax')) {
                    // Try to extract line number from error message
                    const lineMatch = issue.match(/line (\d+)/i);
                    const line = lineMatch ? parseInt(lineMatch[1]) - 1 + startLine : startLine;

                    const range = new vscode.Range(line, 0, line, 1000);
                    const diagnostic = new vscode.Diagnostic(
                        range,
                        issue,
                        vscode.DiagnosticSeverity.Error
                    );
                    diagnostic.source = 'Antimatter';
                    diagnostic.code = 'syntax-error';
                    diagnostics.push(diagnostic);
                }
            }
        }

        // Add execution errors
        if (!result.executes && result.issues) {
            for (const issue of result.issues) {
                if (issue.toLowerCase().includes('execution failed') ||
                    issue.toLowerCase().includes('error')) {
                    const range = new vscode.Range(startLine, 0, startLine, 1000);
                    const diagnostic = new vscode.Diagnostic(
                        range,
                        issue,
                        vscode.DiagnosticSeverity.Error
                    );
                    diagnostic.source = 'Antimatter';
                    diagnostic.code = 'execution-error';
                    diagnostics.push(diagnostic);
                }
            }
        }

        // Add suggestions as hints
        if (result.suggestions) {
            for (const suggestion of result.suggestions) {
                const range = new vscode.Range(startLine, 0, startLine, 1000);
                const diagnostic = new vscode.Diagnostic(
                    range,
                    suggestion,
                    vscode.DiagnosticSeverity.Hint
                );
                diagnostic.source = 'Antimatter';
                diagnostic.code = 'suggestion';
                diagnostics.push(diagnostic);
            }
        }

        // Add security issues as warnings
        if (result.issues) {
            for (const issue of result.issues) {
                if (issue.includes('CRITICAL') || issue.includes('HIGH')) {
                    const range = new vscode.Range(startLine, 0, startLine, 1000);
                    const diagnostic = new vscode.Diagnostic(
                        range,
                        issue,
                        vscode.DiagnosticSeverity.Warning
                    );
                    diagnostic.source = 'Antimatter';
                    diagnostic.code = 'security-issue';
                    diagnostics.push(diagnostic);
                }
            }
        }

        this.diagnosticCollection.set(document.uri, diagnostics);
    }

    clear(document?: vscode.TextDocument): void {
        if (document) {
            this.diagnosticCollection.delete(document.uri);
        } else {
            this.diagnosticCollection.clear();
        }
    }
}
