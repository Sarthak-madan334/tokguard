#!/usr/bin/env node

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const { maybeAutoUpdate, isWithin } = require('./lib/auto-update');

const rootDir = __dirname;

function findPython() {
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

const args = process.argv.slice(2);

if (args[0] === 'uninstall') {
  let globalRoot;
  try {
    globalRoot = execSync('npm root -g', { encoding: 'utf8', timeout: 10000 }).trim();
  } catch (_) {
    process.stderr.write('[tokguard] Could not locate the global npm package directory.\n');
    process.exit(1);
  }

  if (!isWithin(globalRoot, rootDir)) {
    process.stderr.write('[tokguard] This command removes a global install only. For a local install, run `npm uninstall tokguard` in that project.\n');
    process.exit(1);
  }

  try {
    execSync('npm uninstall --global tokguard', { stdio: 'inherit' });
    process.stdout.write('[tokguard] Uninstalled globally. Project files, .tokguard data, and assistant settings were left untouched.\n');
  } catch (_) {
    process.exitCode = 1;
  }
  process.exit(process.exitCode || 0);
}

const pythonBin = findPython();
const updateExitCode = maybeAutoUpdate({ rootDir, args });
if (updateExitCode !== null) process.exit(updateExitCode);

// Auto-check and install mcp package if missing
try {
  execSync(`"${pythonBin}" -c "import mcp"`, { stdio: 'ignore' });
} catch (e) {
  try {
    process.stderr.write('[tokguard] Installing required Python dependency (mcp)...\n');
    execSync(`"${pythonBin}" -m pip install mcp --quiet`, { stdio: 'inherit' });
  } catch (err) {}
}

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
  // Claude Code launches user-scoped MCP servers from its config directory.
  // Use its active project directory when available so TokGuard maps the repo
  // the user is working in, rather than the assistant's config folder.
  cwd: process.env.CLAUDE_PROJECT_DIR || process.cwd(),
  env: env,
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code || 0);
  }
});

