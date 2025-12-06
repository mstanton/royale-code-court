/**
 * StatusBarManager - Manages the Antimatter status bar item
 */

import * as vscode from 'vscode';

export class StatusBarManager {
    public statusBarItem: vscode.StatusBarItem;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.showReady();
        this.statusBarItem.show();
    }

    showReady(): void {
        this.statusBarItem.text = '$(beaker) Antimatter';
        this.statusBarItem.tooltip = 'Antimatter: Ready to validate';
        this.statusBarItem.backgroundColor = undefined;
        this.statusBarItem.command = 'antimatter.validateSelection';
    }

    showValidating(): void {
        this.statusBarItem.text = '$(sync~spin) Validating...';
        this.statusBarItem.tooltip = 'Antimatter: Validating code';
        this.statusBarItem.backgroundColor = undefined;
    }

    showExecuting(): void {
        this.statusBarItem.text = '$(play~spin) Executing...';
        this.statusBarItem.tooltip = 'Antimatter: Executing code in sandbox';
        this.statusBarItem.backgroundColor = undefined;
    }

    showStarting(): void {
        this.statusBarItem.text = '$(sync~spin) Starting...';
        this.statusBarItem.tooltip = 'Antimatter: Starting validation server';
        this.statusBarItem.backgroundColor = undefined;
    }

    showSuccess(): void {
        this.statusBarItem.text = '$(check) Antimatter';
        this.statusBarItem.tooltip = 'Antimatter: Validation passed';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');

        // Reset after 3 seconds
        setTimeout(() => this.showReady(), 3000);
    }

    showWarning(): void {
        this.statusBarItem.text = '$(warning) Antimatter';
        this.statusBarItem.tooltip = 'Antimatter: Warnings detected';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    }

    showError(): void {
        this.statusBarItem.text = '$(error) Antimatter';
        this.statusBarItem.tooltip = 'Antimatter: Validation failed';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }

    showDisconnected(): void {
        this.statusBarItem.text = '$(debug-disconnect) Antimatter';
        this.statusBarItem.tooltip = 'Antimatter: Server disconnected';
        this.statusBarItem.backgroundColor = undefined;
        this.statusBarItem.command = 'antimatter.startServer';
    }
}
