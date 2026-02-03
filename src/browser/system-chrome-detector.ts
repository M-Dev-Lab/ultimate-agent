import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export type BrowserExecutable = {
  kind: "brave" | "canary" | "chromium" | "chrome" | "edge" | "custom";
  path: string;
  userDataDir?: string;
};

const CHROMIUM_DESKTOP_IDS = new Set([
  "google-chrome.desktop",
  "google-chrome-beta.desktop",
  "google-chrome-unstable.desktop",
  "brave-browser.desktop",
  "microsoft-edge.desktop",
  "microsoft-edge-beta.desktop",
  "microsoft-edge-dev.desktop",
  "microsoft-edge-canary.desktop",
  "chromium.desktop",
  "chromium-browser.desktop",
  "vivaldi.desktop",
  "vivaldi-stable.desktop",
  "opera.desktop",
  "opera-gx.desktop",
  "yandex-browser.desktop",
  "org.chromium.Chromium.desktop",
]);

const CHROMIUM_EXE_NAMES = new Set([
  "chrome",
  "chromium",
  "chromium-browser",
  "google-chrome",
  "google-chrome-stable",
  "google-chrome-beta",
  "google-chrome-unstable",
  "brave",
  "brave-browser",
  "brave-browser-stable",
  "microsoft-edge",
  "microsoft-edge-beta",
  "microsoft-edge-dev",
  "microsoft-edge-canary",
  "vivaldi",
  "vivaldi-stable",
  "opera",
  "opera-stable",
  "opera-gx",
  "yandex-browser",
]);

function exists(filePath: string): boolean {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

function execText(
  command: string,
  args: string[],
  timeoutMs = 1200,
): string | null {
  try {
    const output = execSync(
      args.length > 0 ? `${command} ${args.join(' ')}` : command,
      {
        encoding: "utf8",
        timeout: timeoutMs,
      }
    );
    return String(output ?? "").trim() || null;
  } catch {
    return null;
  }
}

function inferKindFromExecutableName(name: string): BrowserExecutable["kind"] {
  const lower = name.toLowerCase();
  if (lower.includes("brave")) {
    return "brave";
  }
  if (lower.includes("edge") || lower.includes("msedge")) {
    return "edge";
  }
  if (lower.includes("chromium")) {
    return "chromium";
  }
  if (lower.includes("canary") || lower.includes("sxs")) {
    return "canary";
  }
  if (lower.includes("opera") || lower.includes("vivaldi") || lower.includes("yandex")) {
    return "chromium";
  }
  return "chrome";
}

function findDesktopFilePath(desktopId: string): string | null {
  const candidates = [
    path.join(os.homedir(), ".local", "share", "applications", desktopId),
    path.join("/usr/local/share/applications", desktopId),
    path.join("/usr/share/applications", desktopId),
    path.join("/var/lib/snapd/desktop/applications", desktopId),
  ];
  for (const candidate of candidates) {
    if (exists(candidate)) {
      return candidate;
    }
  }
  return null;
}

function readDesktopExecLine(desktopPath: string): string | null {
  try {
    const raw = fs.readFileSync(desktopPath, "utf8");
    const lines = raw.split(/\r?\n/);
    for (const line of lines) {
      if (line.startsWith("Exec=")) {
        return line.slice("Exec=".length).trim();
      }
    }
  } catch {
    // ignore
  }
  return null;
}

function extractExecutableFromExecLine(execLine: string): string | null {
  const tokens = splitExecLine(execLine);
  for (const token of tokens) {
    if (!token) continue;
    if (token === "env") continue;
    if (token.includes("=") && !token.startsWith("/") && !token.includes("\\")) continue;
    return token.replace(/^["']|["']$/g, "");
  }
  return null;
}

function splitExecLine(line: string): string[] {
  const tokens: string[] = [];
  let current = "";
  let inQuotes = false;
  let quoteChar = "";
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if ((ch === '"' || ch === "'") && (!inQuotes || ch === quoteChar)) {
      if (inQuotes) {
        inQuotes = false;
        quoteChar = "";
      } else {
        inQuotes = true;
        quoteChar = ch;
      }
      continue;
    }
    if (!inQuotes && /\s/.test(ch)) {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }
    current += ch;
  }
  if (current) {
    tokens.push(current);
  }
  return tokens;
}

function resolveLinuxExecutablePath(command: string): string | null {
  const cleaned = command.trim().replace(/%[a-zA-Z]/g, "");
  if (!cleaned) return null;
  if (cleaned.startsWith("/")) return cleaned;
  const resolved = execText("which", [cleaned], 800);
  return resolved ? resolved.trim() : null;
}

function findFirstExecutable(candidates: Array<BrowserExecutable>): BrowserExecutable | null {
  for (const candidate of candidates) {
    if (exists(candidate.path)) {
      return candidate;
    }
  }
  return null;
}

export function findSystemChromeExecutableLinux(): BrowserExecutable | null {
  const candidates: Array<BrowserExecutable> = [
    { kind: "chrome", path: "/usr/bin/google-chrome" },
    { kind: "chrome", path: "/usr/bin/google-chrome-stable" },
    { kind: "chrome", path: "/usr/bin/chrome" },
    { kind: "brave", path: "/usr/bin/brave-browser" },
    { kind: "brave", path: "/usr/bin/brave-browser-stable" },
    { kind: "brave", path: "/usr/bin/brave" },
    { kind: "brave", path: "/snap/bin/brave" },
    { kind: "edge", path: "/usr/bin/microsoft-edge" },
    { kind: "edge", path: "/usr/bin/microsoft-edge-stable" },
    { kind: "chromium", path: "/usr/bin/chromium" },
    { kind: "chromium", path: "/usr/bin/chromium-browser" },
    { kind: "chromium", path: "/snap/bin/chromium" },
    { kind: "chromium", path: "/snap/bin/chromium-browser" },
  ];

  return findFirstExecutable(candidates);
}

export function detectDefaultBrowserExecutableLinux(): BrowserExecutable | null {
  const desktopId =
    execText("xdg-settings", ["get", "default-web-browser"]) ||
    execText("xdg-mime", ["query", "default", "x-scheme-handler/http"]);
  
  if (!desktopId) {
    return null;
  }
  
  const trimmed = desktopId.trim();
  if (!CHROMIUM_DESKTOP_IDS.has(trimmed)) {
    return null;
  }
  
  const desktopPath = findDesktopFilePath(trimmed);
  if (!desktopPath) {
    return null;
  }
  
  const execLine = readDesktopExecLine(desktopPath);
  if (!execLine) {
    return null;
  }
  
  const command = extractExecutableFromExecLine(execLine);
  if (!command) {
    return null;
  }
  
  const resolved = resolveLinuxExecutablePath(command);
  if (!resolved) {
    return null;
  }
  
  const exeName = path.posix.basename(resolved).toLowerCase();
  if (!CHROMIUM_EXE_NAMES.has(exeName)) {
    return null;
  }
  
  return { kind: inferKindFromExecutableName(exeName), path: resolved };
}

export function getSystemChromeExecutable(): BrowserExecutable | null {
  const platform = os.platform();
  
  if (platform !== "linux") {
    console.log(`[Browser] Platform ${platform} not supported for system browser detection`);
    return null;
  }
  
  const detected = detectDefaultBrowserExecutableLinux();
  if (detected) {
    console.log(`[Browser] Detected default browser: ${detected.kind} at ${detected.path}`);
    return detected;
  }
  
  const fallback = findSystemChromeExecutableLinux();
  if (fallback) {
    console.log(`[Browser] Using fallback browser: ${fallback.kind} at ${fallback.path}`);
    return fallback;
  }
  
  console.log("[Browser] No system Chrome/Chromium found");
  return null;
}

export function autoDetectBrowserPath(): string | null {
  const executable = getSystemChromeExecutable();
  return executable?.path || null;
}

export function getBrowserUserDataDir(kind: BrowserExecutable["kind"]): string | null {
  const homeDir = os.homedir();
  
  const possiblePaths: string[] = [];
  
  switch (kind) {
    case "chrome":
      possiblePaths.push(
        path.join(homeDir, ".config", "google-chrome", "Default"),
        path.join(homeDir, ".config", "chrome-sandbox", "Default")
      );
      break;
    case "chromium":
      possiblePaths.push(
        path.join(homeDir, "snap", "chromium", "common", "chromium", "Default"),
        path.join(homeDir, ".config", "chromium", "Default"),
        path.join(homeDir, ".config", "chromium-browser", "Default")
      );
      break;
    case "brave":
      possiblePaths.push(
        path.join(homeDir, ".config", "BraveSoftware", "Brave-Browser", "Default")
      );
      break;
    case "edge":
      possiblePaths.push(
        path.join(homeDir, ".config", "microsoft-edge", "Default")
      );
      break;
    default:
      possiblePaths.push(
        path.join(homeDir, "snap", "chromium", "common", "chromium", "Default"),
        path.join(homeDir, ".config", "google-chrome", "Default"),
        path.join(homeDir, ".config", "chromium", "Default")
      );
  }
  
  for (const dir of possiblePaths) {
    if (exists(dir)) {
      console.log(`[Browser] Found user data dir: ${dir}`);
      return dir;
    }
  }
  
  console.log(`[Browser] No user data dir found for ${kind}, will launch fresh session`);
  return null;
}

export function getSystemChromeWithProfile(): { executablePath: string; userDataDir: string } | null {
  const executable = getSystemChromeExecutable();
  if (!executable) {
    return null;
  }
  
  const userDataDir = getBrowserUserDataDir(executable.kind);
  if (!userDataDir) {
    return null;
  }
  
  return {
    executablePath: executable.path,
    userDataDir
  };
}
