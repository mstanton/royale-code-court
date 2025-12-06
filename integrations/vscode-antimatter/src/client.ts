/**
 * JesterClient - Communicates with the Royale Code Court Python backend
 *
 * Supports two modes:
 * 1. WebSocket connection to running server
 * 2. Direct subprocess execution (fallback)
 */

import * as vscode from 'vscode';
import * as cp from 'child_process';
import WebSocket from 'ws';

export interface ValidationResult {
    code_id?: string;
    syntax_valid: boolean;
    executes: boolean;
    overall_success: boolean;
    complexity_score?: number;
    patterns_detected?: string[];
    issues?: string[];
    suggestions?: string[];
    execution_time_ms?: number;
    execution_output?: string;
    tier?: string;
}

export interface ExecutionResult {
    success: boolean;
    output?: string;
    error?: string;
    execution_time_ms?: number;
    tier?: string;
    memory_mb?: number;
}

export interface SecurityResult {
    passed: boolean;
    issues?: Array<{
        severity: string;
        description: string;
        pattern?: string;
    }>;
}

export interface StatsResult {
    total_executions: number;
    success_rate: number;
    avg_execution_time_ms: number;
    learned_patterns: number;
    by_tier?: Record<string, any>;
}

export class JesterClient {
    private pythonPath: string;
    private jesterPath: string;
    private serverPort: number;
    private ws: WebSocket | null = null;
    private serverProcess: cp.ChildProcess | null = null;
    private connected: boolean = false;
    private messageQueue: Map<string, { resolve: Function; reject: Function }> = new Map();
    private messageId: number = 0;

    constructor(pythonPath: string, jesterPath: string, serverPort: number) {
        this.pythonPath = pythonPath;
        this.jesterPath = jesterPath;
        this.serverPort = serverPort;
    }

    isConnected(): boolean {
        return this.connected;
    }

    async connect(): Promise<boolean> {
        try {
            return await this.connectWebSocket();
        } catch (error) {
            console.error('WebSocket connection failed, using subprocess mode:', error);
            return true; // Subprocess mode is always available
        }
    }

    private async connectWebSocket(): Promise<boolean> {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://localhost:${this.serverPort}`;

            this.ws = new WebSocket(wsUrl);

            this.ws.on('open', () => {
                console.log('Connected to Jester WebSocket server');
                this.connected = true;
                resolve(true);
            });

            this.ws.on('message', (data: WebSocket.Data) => {
                try {
                    const message = JSON.parse(data.toString());
                    const pending = this.messageQueue.get(message.id);
                    if (pending) {
                        this.messageQueue.delete(message.id);
                        if (message.error) {
                            pending.reject(new Error(message.error));
                        } else {
                            pending.resolve(message.result);
                        }
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            });

            this.ws.on('close', () => {
                this.connected = false;
                console.log('Disconnected from Jester WebSocket server');
            });

            this.ws.on('error', (error) => {
                this.connected = false;
                reject(error);
            });

            // Timeout after 5 seconds
            setTimeout(() => {
                if (!this.connected) {
                    reject(new Error('Connection timeout'));
                }
            }, 5000);
        });
    }

    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
    }

    async startServer(): Promise<boolean> {
        // Try to connect first - maybe server is already running
        try {
            const connected = await this.connectWebSocket();
            if (connected) {
                return true;
            }
        } catch {
            // Server not running, start it
        }

        return new Promise((resolve) => {
            const jesterModule = this.jesterPath
                ? `${this.jesterPath}/jester`
                : 'jester';

            // Start the WebSocket server
            this.serverProcess = cp.spawn(this.pythonPath, [
                '-c',
                `
import asyncio
import json
import websockets
from jester.core.event_stream import get_event_bus, EventStream
from jester.core.models import AgentType
from jester.execution.executor import CodeExecutor
from jester.agents.jester import JesterAgent
from jester.core.metrics import MetricsCollector

event_bus = get_event_bus()
executor = CodeExecutor(EventStream(event_bus, AgentType.JESTER))
metrics = MetricsCollector()
jester = JesterAgent(event_bus, executor=executor, metrics=metrics)
jester.start()

async def handle_client(websocket, path):
    async for message in websocket:
        try:
            data = json.loads(message)
            msg_id = data.get('id', '')
            command = data.get('command', '')
            params = data.get('params', {})

            result = None
            error = None

            if command == 'validate':
                code = params.get('code', '')
                validation = await jester.validate(code, 'python')
                result = {
                    'syntax_valid': validation.syntax_valid,
                    'executes': validation.executes,
                    'overall_success': validation.overall_success,
                    'complexity_score': validation.complexity_score,
                    'patterns_detected': validation.patterns_detected,
                    'issues': validation.issues,
                    'suggestions': validation.suggestions,
                    'execution_time_ms': validation.execution_result.execution_time_ms if validation.execution_result else 0,
                    'execution_output': validation.execution_result.output[:500] if validation.execution_result else '',
                    'tier': validation.execution_result.tier.value if validation.execution_result else 'unknown'
                }

            elif command == 'execute':
                code = params.get('code', '')
                timeout = params.get('timeout', 5.0)
                exec_result = await executor.execute(code, 'python', timeout=timeout)
                result = {
                    'success': exec_result.success,
                    'output': exec_result.output,
                    'error': exec_result.error,
                    'execution_time_ms': exec_result.execution_time_ms,
                    'tier': exec_result.tier.value,
                    'memory_mb': exec_result.memory_usage_mb
                }

            elif command == 'security':
                code = params.get('code', '')
                issues = jester._check_security(code)
                result = {
                    'passed': len(issues) == 0,
                    'issues': [
                        {'severity': s.value, 'description': d, 'pattern': n}
                        for n, s, d in issues
                    ]
                }

            elif command == 'stats':
                stats = metrics.get_execution_stats()
                pattern_stats = metrics.get_pattern_stats()
                result = {
                    'total_executions': stats.get('total_executions', 0),
                    'success_rate': stats.get('success_rate', 0),
                    'avg_execution_time_ms': stats.get('avg_execution_time_ms', 0),
                    'learned_patterns': len(pattern_stats),
                    'by_tier': stats.get('by_tier', {})
                }

            else:
                error = f'Unknown command: {command}'

            response = {'id': msg_id, 'result': result, 'error': error}
            await websocket.send(json.dumps(response))

        except Exception as e:
            await websocket.send(json.dumps({'id': msg_id, 'error': str(e)}))

async def main():
    async with websockets.serve(handle_client, 'localhost', ${this.serverPort}):
        print('Antimatter server started on port ${this.serverPort}')
        await asyncio.Future()  # Run forever

asyncio.run(main())
                `
            ], {
                env: {
                    ...process.env,
                    PYTHONPATH: this.jesterPath || process.env.PYTHONPATH
                }
            });

            this.serverProcess.stdout?.on('data', (data) => {
                console.log(`Jester server: ${data}`);
                if (data.toString().includes('started')) {
                    // Server started, try to connect
                    setTimeout(async () => {
                        try {
                            await this.connectWebSocket();
                            resolve(true);
                        } catch {
                            resolve(false);
                        }
                    }, 1000);
                }
            });

            this.serverProcess.stderr?.on('data', (data) => {
                console.error(`Jester server error: ${data}`);
            });

            this.serverProcess.on('close', (code) => {
                console.log(`Jester server exited with code ${code}`);
                this.serverProcess = null;
            });

            // Timeout
            setTimeout(() => {
                if (!this.connected) {
                    resolve(false);
                }
            }, 10000);
        });
    }

    async stopServer(): Promise<void> {
        this.disconnect();
        if (this.serverProcess) {
            this.serverProcess.kill();
            this.serverProcess = null;
        }
    }

    private async sendCommand(command: string, params: any): Promise<any> {
        if (this.connected && this.ws) {
            return this.sendWebSocketCommand(command, params);
        } else {
            return this.executeSubprocess(command, params);
        }
    }

    private async sendWebSocketCommand(command: string, params: any): Promise<any> {
        return new Promise((resolve, reject) => {
            const id = String(++this.messageId);
            this.messageQueue.set(id, { resolve, reject });

            const message = JSON.stringify({ id, command, params });
            this.ws!.send(message);

            // Timeout after 30 seconds
            setTimeout(() => {
                if (this.messageQueue.has(id)) {
                    this.messageQueue.delete(id);
                    reject(new Error('Request timeout'));
                }
            }, 30000);
        });
    }

    private async executeSubprocess(command: string, params: any): Promise<any> {
        return new Promise((resolve, reject) => {
            const pythonCode = this.getSubprocessCode(command, params);

            const proc = cp.spawn(this.pythonPath, ['-c', pythonCode], {
                env: {
                    ...process.env,
                    PYTHONPATH: this.jesterPath || process.env.PYTHONPATH
                }
            });

            let stdout = '';
            let stderr = '';

            proc.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            proc.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            proc.on('close', (code) => {
                if (code === 0) {
                    try {
                        const result = JSON.parse(stdout);
                        resolve(result);
                    } catch {
                        reject(new Error(`Failed to parse output: ${stdout}`));
                    }
                } else {
                    reject(new Error(stderr || `Process exited with code ${code}`));
                }
            });

            proc.on('error', reject);
        });
    }

    private getSubprocessCode(command: string, params: any): string {
        const paramsJson = JSON.stringify(params);

        return `
import asyncio
import json
import sys

async def main():
    from jester.core.event_stream import get_event_bus, EventStream
    from jester.core.models import AgentType
    from jester.execution.executor import CodeExecutor
    from jester.agents.jester import JesterAgent
    from jester.core.metrics import MetricsCollector

    event_bus = get_event_bus()
    executor = CodeExecutor(EventStream(event_bus, AgentType.JESTER))
    metrics = MetricsCollector()
    jester = JesterAgent(event_bus, executor=executor, metrics=metrics)
    jester.start()

    params = json.loads('${paramsJson.replace(/'/g, "\\'")}')
    command = '${command}'

    if command == 'validate':
        code = params.get('code', '')
        validation = await jester.validate(code, 'python')
        result = {
            'syntax_valid': validation.syntax_valid,
            'executes': validation.executes,
            'overall_success': validation.overall_success,
            'complexity_score': validation.complexity_score,
            'patterns_detected': validation.patterns_detected,
            'issues': validation.issues,
            'suggestions': validation.suggestions,
            'execution_time_ms': validation.execution_result.execution_time_ms if validation.execution_result else 0,
            'execution_output': validation.execution_result.output[:500] if validation.execution_result else '',
            'tier': validation.execution_result.tier.value if validation.execution_result else 'unknown'
        }

    elif command == 'execute':
        code = params.get('code', '')
        timeout = params.get('timeout', 5.0)
        exec_result = await executor.execute(code, 'python', timeout=timeout)
        result = {
            'success': exec_result.success,
            'output': exec_result.output,
            'error': exec_result.error,
            'execution_time_ms': exec_result.execution_time_ms,
            'tier': exec_result.tier.value,
            'memory_mb': exec_result.memory_usage_mb
        }

    elif command == 'security':
        code = params.get('code', '')
        issues = jester._check_security(code)
        result = {
            'passed': len(issues) == 0,
            'issues': [
                {'severity': s.value, 'description': d, 'pattern': n}
                for n, s, d in issues
            ]
        }

    elif command == 'stats':
        stats = metrics.get_execution_stats()
        pattern_stats = metrics.get_pattern_stats()
        result = {
            'total_executions': stats.get('total_executions', 0),
            'success_rate': stats.get('success_rate', 0),
            'avg_execution_time_ms': stats.get('avg_execution_time_ms', 0),
            'learned_patterns': len(pattern_stats),
            'by_tier': stats.get('by_tier', {})
        }

    jester.stop()
    print(json.dumps(result))

asyncio.run(main())
        `;
    }

    async validateCode(code: string): Promise<ValidationResult> {
        return this.sendCommand('validate', { code });
    }

    async executeCode(code: string, timeout?: number): Promise<ExecutionResult> {
        return this.sendCommand('execute', { code, timeout });
    }

    async checkSecurity(code: string): Promise<SecurityResult> {
        return this.sendCommand('security', { code });
    }

    async getStats(): Promise<StatsResult> {
        return this.sendCommand('stats', {});
    }
}
