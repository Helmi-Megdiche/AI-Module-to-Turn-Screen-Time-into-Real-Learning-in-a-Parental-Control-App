#!/usr/bin/env node
/**
 * Cross-platform test runner: backend Jest, ai-service pytest, optional full eval.
 *
 * Usage:
 *   node scripts/run-all-tests.js           # fast: jest + pytest
 *   node scripts/run-all-tests.js --full    # + evaluate_moderation.py --strict (slow, loads model)
 */

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const backend = path.join(root, 'backend');
const aiService = path.join(root, 'ai-service');

const full = process.argv.includes('--full');

function run(cmd, args, cwd) {
  const r = spawnSync(cmd, args, {
    cwd,
    stdio: 'inherit',
    shell: true,
    env: process.env,
  });
  const code = r.status === null ? 1 : r.status;
  if (code !== 0) {
    console.error(`\n[run-all-tests] FAILED: ${cmd} ${args.join(' ')} (exit ${code})\n`);
  }
  return code;
}

/** @returns {{ cmd: string, prefix: string[], exe?: string } | null} */
function findPython() {
  const fromEnv = process.env.AI_VENV_PYTHON || process.env.PYTHON_FOR_TESTS;
  if (fromEnv && fs.existsSync(fromEnv)) {
    return { cmd: fromEnv, prefix: [], exe: fromEnv };
  }

  const candidates = [
    { cmd: 'py', prefix: ['-3'] },
    { cmd: 'python', prefix: [] },
    { cmd: 'python3', prefix: [] },
  ];
  for (const { cmd, prefix } of candidates) {
    const args = [...prefix, '-c', 'import sys; sys.exit(0)'];
    const r = spawnSync(cmd, args, { stdio: 'pipe', shell: true });
    if ((r.status ?? 1) === 0) {
      return { cmd, prefix };
    }
  }
  return null;
}

let failed = 0;

console.log('\n=== Backend: Jest ===\n');
failed += run('npm', ['test', '--', '--passWithNoTests'], backend);

console.log('\n=== AI service: pytest ===\n');
const py = findPython();
if (!py) {
  console.error('[run-all-tests] No working Python on PATH (py -3, python, python3).');
  failed += 1;
} else if (py.exe) {
  failed += run(py.exe, ['-m', 'pytest', 'tests', '-q'], aiService);
} else {
  failed += run(py.cmd, [...py.prefix, '-m', 'pytest', 'tests', '-q'], aiService);
}

if (full && py) {
  console.log('\n=== AI service: evaluate_moderation.py --strict (slow) ===\n');
  if (py.exe) {
    failed += run(py.exe, ['evaluate_moderation.py', '--strict'], aiService);
  } else {
    failed += run(py.cmd, [...py.prefix, 'evaluate_moderation.py', '--strict'], aiService);
  }
} else if (full && !py) {
  failed += 1;
} else {
  console.log('\n[run-all-tests] Skipped evaluate_moderation.py (use --full for strict 15-case eval).\n');
}

if (failed > 0) {
  process.exit(1);
}
console.log('\n[run-all-tests] All executed steps passed.\n');
process.exit(0);
