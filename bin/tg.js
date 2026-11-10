#!/usr/bin/env node

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Root of tokguard package
const rootDir = path.resolve(__dirname, '..');

function findPython() {
  // Check common Windows Python location if Windows
  if (process.platform === 'win32' && process.env.LOCALAPPDATA) {
    const candidates = [
      path.join(process.env.LOCALAPPDATA, 'Python', 'pythoncore-3.14-64', 'python.exe'),
      path.join(process.env.LOCALAPPDATA, 'Programs', 'Python', 'Python312', 'python.exe'),
      path.join(process.env.LOCALAPPDATA, 'Programs', 'Python', 'Python311', 'python.exe'),
      path.join(process.env.LOCALAPPDATA, 'Programs', 'Python', 'Python310', 'python.exe'),
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) return p;
    }
  }

  const cmds = process.platform === 'win32' ? ['python', 'py', 'python3'] : ['python3', 'python'];
  for (const cmd of cmds) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch (e) {}
  }
  return 'python';
}

const pythonBin = findPython();
const args = process.argv.slice(2);

// Check if invoking mcp server directly
let targetModule = 'tg.cli';
let passArgs = args;

if (args.length > 0 && args[0] === 'mcp') {
  targetModule = 'tg.mcp_server';
  passArgs = args.slice(1);
}

const env = Object.assign({}, process.env);
env.PYTHONPATH = env.PYTHONPATH ? `${rootDir}${path.delimiter}${env.PYTHONPATH}` : rootDir;

const child = spawn(pythonBin, ['-m', targetModule, ...passArgs], {
  stdio: 'inherit',
  cwd: process.cwd(),
  env: env
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code || 0);
  }
});

