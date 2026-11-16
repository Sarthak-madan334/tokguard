'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { isNewerVersion, isWithin, maybeAutoUpdate } = require('../lib/auto-update');

test('compares stable and prerelease versions', () => {
  assert.equal(isNewerVersion('2.0.0', '1.9.9'), true);
  assert.equal(isNewerVersion('2.0.0', '2.0.0-rc.1'), true);
  assert.equal(isNewerVersion('1.9.9', '2.0.0'), false);
  assert.equal(isNewerVersion('not-semver', '1.0.0'), false);
});

test('identifies packages below the global npm root only', () => {
  const root = path.join(os.tmpdir(), 'npm-global', 'node_modules');
  assert.equal(isWithin(root, path.join(root, 'tokguard')), true);
  assert.equal(isWithin(root, path.join(os.tmpdir(), 'npm-global', 'node_modules-extra', 'tokguard')), false);
  assert.equal(isWithin(root, root), false);
});

test('installs a newer global release and resumes the original arguments', (t) => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'tg-auto-update-'));
  const installDir = path.join(tempRoot, 'node_modules', 'tokguard');
  fs.mkdirSync(installDir, { recursive: true });
  fs.writeFileSync(path.join(installDir, 'package.json'), JSON.stringify({ version: '1.2.3' }));
  fs.writeFileSync(path.join(installDir, 'cli.js'), '');
  t.after(() => fs.rmSync(tempRoot, { recursive: true, force: true }));

  const commands = [];
  const messages = [];
  let restart;
  const exitCode = maybeAutoUpdate({
    rootDir: installDir,
    args: ['map', '--json'],
    env: {},
    execSync(command) {
      commands.push(command);
      if (command === 'npm root -g') return `${path.dirname(installDir)}\n`;
      if (command === 'npm view tokguard version --json') return '"2.0.0"\n';
      if (command.startsWith('npm install --global tokguard@latest')) return '';
      throw new Error(`Unexpected command: ${command}`);
    },
    spawnSync(command, args, options) {
      restart = { command, args, options };
      return { status: 0 };
    },
    writeError(message) { messages.push(message); },
  });

  assert.equal(exitCode, 0);
  assert.deepEqual(commands, [
    'npm root -g',
    'npm view tokguard version --json',
    'npm install --global tokguard@latest --no-audit --no-fund',
  ]);
  assert.deepEqual(restart.args.slice(1), ['map', '--json']);
  assert.equal(restart.options.env.TOKGUARD_AUTO_UPDATE_RESTART, '1');
  assert.match(messages.join(''), /Updating 1\.2\.3 → 2\.0\.0/);
});

test('respects opt-out and leaves local installs untouched', () => {
  let calls = 0;
  assert.equal(maybeAutoUpdate({ env: { TOKGUARD_AUTO_UPDATE: '0' }, execSync() { calls += 1; } }), null);
  assert.equal(calls, 0);

  const localRoot = path.join(os.tmpdir(), 'tokguard-project', 'node_modules', 'tokguard');
  assert.equal(maybeAutoUpdate({
    rootDir: localRoot,
    args: [],
    env: {},
    execSync() { calls += 1; return path.join(os.tmpdir(), 'npm-global', 'node_modules'); },
  }), null);
  assert.equal(calls, 1);
});

test('continues with the installed version when npm is unavailable', () => {
  const messages = [];
  assert.equal(maybeAutoUpdate({
    rootDir: __dirname,
    args: [],
    env: {},
    execSync() { throw new Error('offline'); },
    writeError(message) { messages.push(message); },
  }), null);
  assert.deepEqual(messages, []);
});
