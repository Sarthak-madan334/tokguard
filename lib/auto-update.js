'use strict';

const { execSync, spawnSync } = require('child_process');
const path = require('path');

function parseVersion(version) {
  const match = String(version).trim().replace(/^v/, '').match(/^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/);
  if (!match) return null;
  return { core: match.slice(1, 4).map(Number), prerelease: match[4] || null };
}

function isNewerVersion(candidate, current) {
  const next = parseVersion(candidate);
  const installed = parseVersion(current);
  if (!next || !installed) return false;
  for (let index = 0; index < 3; index += 1) {
    if (next.core[index] !== installed.core[index]) return next.core[index] > installed.core[index];
  }
  if (next.prerelease === installed.prerelease) return false;
  if (next.prerelease === null) return true;
  if (installed.prerelease === null) return false;
  return next.prerelease.localeCompare(installed.prerelease, undefined, { numeric: true }) > 0;
}

function isWithin(parent, candidate) {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate));
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

function maybeAutoUpdate(options = {}) {
  const rootDir = options.rootDir || path.resolve(__dirname, '..');
  const args = options.args || process.argv.slice(2);
  const env = options.env || process.env;
  const run = options.execSync || execSync;
  const spawn = options.spawnSync || spawnSync;
  const writeError = options.writeError || ((message) => process.stderr.write(message));

  if (env.TOKGUARD_AUTO_UPDATE === '0' || env.TOKGUARD_AUTO_UPDATE === 'false' || env.TOKGUARD_AUTO_UPDATE_RESTART === '1') return null;

  let globalRoot;
  let installedVersion;
  try {
    globalRoot = run('npm root -g', { encoding: 'utf8', timeout: 10000 }).trim();
    if (!isWithin(globalRoot, rootDir)) return null;
    installedVersion = require(path.join(rootDir, 'package.json')).version;
  } catch (_) {
    return null;
  }

  let latestVersion;
  try {
    latestVersion = run('npm view tokguard version --json', { encoding: 'utf8', timeout: 10000 }).trim().replace(/^"|"$/g, '');
  } catch (_) {
    return null;
  }
  if (!isNewerVersion(latestVersion, installedVersion)) return null;

  writeError(`[tokguard] Updating ${installedVersion} → ${latestVersion} before continuing...\n`);
  try {
    run('npm install --global tokguard@latest --no-audit --no-fund', { encoding: 'utf8', timeout: 120000, stdio: 'pipe' });
  } catch (_) {
    writeError('[tokguard] Automatic update failed; continuing with the installed version.\n');
    return null;
  }

  const updatedCli = path.join(rootDir, 'cli.js');
  const nextEnv = { ...env, TOKGUARD_AUTO_UPDATE_RESTART: '1' };
  const result = spawn(process.execPath, [updatedCli, ...args], { stdio: 'inherit', env: nextEnv });
  if (result.error) {
    writeError('[tokguard] Update installed, but restarting the updated command failed; continuing.\n');
    return null;
  }
  return typeof result.status === 'number' ? result.status : 1;
}

module.exports = { isNewerVersion, isWithin, maybeAutoUpdate };
