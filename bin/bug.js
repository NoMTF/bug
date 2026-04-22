#!/usr/bin/env node
/**
 * bug — Node.js entry point for the bug-version generator.
 *
 * Lets non-Python users run the tool with `npx bug` or `node bin/bug.js`.
 * This is a thin, cross-platform launcher around scripts/make_bug_version.py
 * and scripts/inject_bug.py. It resolves a usable Python interpreter, forwards
 * arguments, and streams child stdio straight through.
 */

"use strict";

const { spawn, spawnSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const ROOT = path.resolve(__dirname, "..");
const SCRIPTS = path.join(ROOT, "scripts");

const COMMANDS = {
  "bug-version": "make_bug_version.py",
  make: "make_bug_version.py",
  inject: "inject_bug.py",
  sandbox: "inject_bug.py",
};

function resolvePython() {
  const override = process.env.BUG_PYTHON;
  if (override) return override;
  const candidates =
    process.platform === "win32"
      ? ["py", "python", "python3"]
      : ["python3", "python"];
  for (const candidate of candidates) {
    const probe = spawnSync(candidate, ["--version"], { stdio: "ignore" });
    if (probe.status === 0) return candidate;
  }
  return null;
}

function printUsage() {
  process.stdout.write(
    [
      "Usage: bug <command> [options]",
      "",
      "Commands:",
      "  bug-version <source> [flags]   Create <source>-bug-version and -clean-backup",
      "  inject      <sandbox> [flags]  Mutate a sandbox directory in place",
      "  languages                      Print supported file extensions",
      "  help                           Show this message",
      "",
      "Flags are forwarded to the underlying Python script. Use --help for more.",
      "",
      "Examples:",
      "  bug bug-version ./my-app --profile messy --count 12",
      "  bug inject ./examples/js-kata --bug off-by-one",
      "",
    ].join("\n"),
  );
}

function printLanguages() {
  const supported = [
    ".py",
    ".js, .jsx, .ts, .tsx, .mjs, .cjs",
    ".go",
    ".rs",
    ".java",
    ".kt, .kts",
    ".swift",
    ".cs",
    ".c, .cc, .cpp, .cxx, .h, .hpp, .hxx",
    ".rb",
    ".php",
  ];
  process.stdout.write("Supported source file extensions:\n");
  for (const row of supported) process.stdout.write(`  ${row}\n`);
}

function main(argv) {
  if (argv.length === 0 || argv[0] === "help" || argv[0] === "-h" || argv[0] === "--help") {
    printUsage();
    return 0;
  }
  if (argv[0] === "languages" || argv[0] === "--languages") {
    printLanguages();
    return 0;
  }

  const [commandName, ...rest] = argv;
  const scriptName = COMMANDS[commandName];
  if (!scriptName) {
    process.stderr.write(`error: unknown command "${commandName}"\n\n`);
    printUsage();
    return 2;
  }

  const scriptPath = path.join(SCRIPTS, scriptName);
  if (!fs.existsSync(scriptPath)) {
    process.stderr.write(`error: missing script ${scriptPath}\n`);
    return 1;
  }

  const python = resolvePython();
  if (!python) {
    process.stderr.write(
      "error: no Python interpreter found. Install Python 3.8+ or set BUG_PYTHON.\n",
    );
    return 1;
  }

  const child = spawn(python, [scriptPath, ...rest], {
    stdio: "inherit",
    cwd: process.cwd(),
  });
  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
  return 0;
}

const exitCode = main(process.argv.slice(2));
if (typeof exitCode === "number" && exitCode !== 0) process.exit(exitCode);
