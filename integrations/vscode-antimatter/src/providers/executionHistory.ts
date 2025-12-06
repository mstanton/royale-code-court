/**
 * ExecutionHistoryProvider - Tree view for execution history
 */

import * as vscode from 'vscode';

export interface ExecutionRecord {
    timestamp: Date;
    code: string;
    success: boolean;
    output?: string;
    error?: string;
    time_ms?: number;
}

class HistoryItem extends vscode.TreeItem {
    constructor(
        public readonly record: ExecutionRecord,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(
            record.code.substring(0, 50) + (record.code.length > 50 ? '...' : ''),
            collapsibleState
        );

        this.description = record.timestamp.toLocaleTimeString();
        this.tooltip = `${record.code}\n\nTime: ${(record.time_ms || 0).toFixed(1)}ms`;

        this.iconPath = record.success
            ? new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed'))
            : new vscode.ThemeIcon('x', new vscode.ThemeColor('testing.iconFailed'));

        // Add context for output/error viewing
        this.contextValue = record.success ? 'execution-success' : 'execution-failure';
    }
}

export class ExecutionHistoryProvider implements vscode.TreeDataProvider<HistoryItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<HistoryItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private history: ExecutionRecord[] = [];
    private maxHistorySize = 50;

    addExecution(record: ExecutionRecord): void {
        this.history.unshift(record);

        // Trim history
        if (this.history.length > this.maxHistorySize) {
            this.history = this.history.slice(0, this.maxHistorySize);
        }

        this._onDidChangeTreeData.fire(undefined);
    }

    clearHistory(): void {
        this.history = [];
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: HistoryItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: HistoryItem): Thenable<HistoryItem[]> {
        if (element) {
            return Promise.resolve([]);
        }

        if (this.history.length === 0) {
            return Promise.resolve([]);
        }

        return Promise.resolve(
            this.history.map(record =>
                new HistoryItem(record, vscode.TreeItemCollapsibleState.None)
            )
        );
    }
}
