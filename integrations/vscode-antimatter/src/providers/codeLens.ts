/**
 * CodeLensProvider - Provides inline actions for functions and classes
 */

import * as vscode from 'vscode';
import { JesterClient } from '../client';

export class CodeLensProvider implements vscode.CodeLensProvider {
    private client: JesterClient;

    constructor(client: JesterClient) {
        this.client = client;
    }

    provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
        const codeLenses: vscode.CodeLens[] = [];
        const text = document.getText();
        const lines = text.split('\n');

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            // Match function definitions
            const funcMatch = line.match(/^\s*(?:async\s+)?def\s+(\w+)\s*\(/);
            if (funcMatch) {
                const range = new vscode.Range(i, 0, i, line.length);

                // Add "Validate" lens
                codeLenses.push(new vscode.CodeLens(range, {
                    title: '$(beaker) Validate',
                    command: 'antimatter.validateFunction',
                    arguments: [document, i, funcMatch[1]]
                }));

                // Add "Execute" lens
                codeLenses.push(new vscode.CodeLens(range, {
                    title: '$(play) Execute',
                    command: 'antimatter.executeFunction',
                    arguments: [document, i, funcMatch[1]]
                }));
            }

            // Match class definitions
            const classMatch = line.match(/^\s*class\s+(\w+)/);
            if (classMatch) {
                const range = new vscode.Range(i, 0, i, line.length);

                codeLenses.push(new vscode.CodeLens(range, {
                    title: '$(beaker) Validate Class',
                    command: 'antimatter.validateClass',
                    arguments: [document, i, classMatch[1]]
                }));
            }
        }

        return codeLenses;
    }

    resolveCodeLens(codeLens: vscode.CodeLens): vscode.CodeLens {
        return codeLens;
    }
}
