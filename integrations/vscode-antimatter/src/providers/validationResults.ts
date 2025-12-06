/**
 * ValidationResultsProvider - Tree view for validation results
 */

import * as vscode from 'vscode';
import { ValidationResult } from '../client';

class ValidationItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly value: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly children?: ValidationItem[]
    ) {
        super(label, collapsibleState);
        this.description = value;
    }
}

export class ValidationResultsProvider implements vscode.TreeDataProvider<ValidationItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<ValidationItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private result: ValidationResult | null = null;

    setResults(result: ValidationResult): void {
        this.result = result;
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: ValidationItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ValidationItem): Thenable<ValidationItem[]> {
        if (!this.result) {
            return Promise.resolve([
                new ValidationItem('No validation results', 'Run a validation to see results', vscode.TreeItemCollapsibleState.None)
            ]);
        }

        if (!element) {
            // Root items
            const items: ValidationItem[] = [
                new ValidationItem(
                    'Status',
                    this.result.overall_success ? 'PASSED' : 'FAILED',
                    vscode.TreeItemCollapsibleState.None
                ),
                new ValidationItem(
                    'Syntax',
                    this.result.syntax_valid ? 'Valid' : 'Invalid',
                    vscode.TreeItemCollapsibleState.None
                ),
                new ValidationItem(
                    'Executes',
                    this.result.executes ? 'Yes' : 'No',
                    vscode.TreeItemCollapsibleState.None
                ),
                new ValidationItem(
                    'Complexity',
                    String(this.result.complexity_score || 0),
                    vscode.TreeItemCollapsibleState.None
                ),
                new ValidationItem(
                    'Time',
                    `${(this.result.execution_time_ms || 0).toFixed(1)}ms`,
                    vscode.TreeItemCollapsibleState.None
                )
            ];

            // Set icons based on status
            items[0].iconPath = this.result.overall_success
                ? new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed'))
                : new vscode.ThemeIcon('x', new vscode.ThemeColor('testing.iconFailed'));

            items[1].iconPath = this.result.syntax_valid
                ? new vscode.ThemeIcon('check')
                : new vscode.ThemeIcon('x');

            items[2].iconPath = this.result.executes
                ? new vscode.ThemeIcon('check')
                : new vscode.ThemeIcon('x');

            items[3].iconPath = new vscode.ThemeIcon('symbol-numeric');
            items[4].iconPath = new vscode.ThemeIcon('clock');

            // Add issues if any
            if (this.result.issues && this.result.issues.length > 0) {
                const issueItems = this.result.issues.map(issue =>
                    new ValidationItem(issue, '', vscode.TreeItemCollapsibleState.None)
                );
                issueItems.forEach(item => {
                    item.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('list.warningForeground'));
                });

                items.push(new ValidationItem(
                    'Issues',
                    `${this.result.issues.length}`,
                    vscode.TreeItemCollapsibleState.Expanded,
                    issueItems
                ));
            }

            // Add suggestions if any
            if (this.result.suggestions && this.result.suggestions.length > 0) {
                const suggestionItems = this.result.suggestions.map(suggestion =>
                    new ValidationItem(suggestion, '', vscode.TreeItemCollapsibleState.None)
                );
                suggestionItems.forEach(item => {
                    item.iconPath = new vscode.ThemeIcon('lightbulb');
                });

                items.push(new ValidationItem(
                    'Suggestions',
                    `${this.result.suggestions.length}`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    suggestionItems
                ));
            }

            return Promise.resolve(items);
        }

        // Return children
        return Promise.resolve(element.children || []);
    }
}
