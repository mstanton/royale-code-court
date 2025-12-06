/**
 * PatternsProvider - Tree view for detected patterns
 */

import * as vscode from 'vscode';

class PatternItem extends vscode.TreeItem {
    constructor(
        public readonly patternName: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(patternName, collapsibleState);

        // Format pattern name for display
        this.label = patternName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        this.tooltip = `Pattern: ${patternName}`;

        // Set icon based on pattern type
        if (patternName.includes('error') || patternName.includes('security')) {
            this.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('list.warningForeground'));
        } else if (patternName.includes('async') || patternName.includes('generator')) {
            this.iconPath = new vscode.ThemeIcon('sync');
        } else if (patternName.includes('class') || patternName.includes('decorator')) {
            this.iconPath = new vscode.ThemeIcon('symbol-class');
        } else if (patternName.includes('function') || patternName.includes('lambda')) {
            this.iconPath = new vscode.ThemeIcon('symbol-function');
        } else if (patternName.includes('comprehension') || patternName.includes('expression')) {
            this.iconPath = new vscode.ThemeIcon('symbol-array');
        } else {
            this.iconPath = new vscode.ThemeIcon('symbol-misc');
        }
    }
}

export class PatternsProvider implements vscode.TreeDataProvider<PatternItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<PatternItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private patterns: string[] = [];

    setPatterns(patterns: string[]): void {
        this.patterns = patterns;
        this._onDidChangeTreeData.fire(undefined);
    }

    clearPatterns(): void {
        this.patterns = [];
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: PatternItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: PatternItem): Thenable<PatternItem[]> {
        if (element) {
            return Promise.resolve([]);
        }

        if (this.patterns.length === 0) {
            return Promise.resolve([]);
        }

        return Promise.resolve(
            this.patterns.map(pattern =>
                new PatternItem(pattern, vscode.TreeItemCollapsibleState.None)
            )
        );
    }
}
