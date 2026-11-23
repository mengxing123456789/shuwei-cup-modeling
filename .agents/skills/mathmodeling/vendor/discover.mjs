/**
 * 找到当前 DSH Web GUI 的端口并返回可用 base URL。
 *
 * 为什么需要探测：端口每次重启都会变（实测见过 54532 / 61694 / 65082）。
 * 硬编码会在下次重启后失效。
 *
 * 三级策略：
 *   1. 环境变量 DSH_WEB_URL / DSH_WEB_PORT
 *   2. 扫描本地监听端口，找能响应 /dsh-agents/api/state 的那个
 *   3. 从最近的会话日志里读（可能过期，仅作参考）
 *
 * 找到后用一次真实请求确认，不确认就不返回。
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const HOME = os.homedir();
const DSH = path.join(HOME, '.dsh');

/** 对某个端口发一次探测请求，成功返回 true。 */
async function probe(port) {
  const url = `http://127.0.0.1:${port}/dsh-agents/api/state`;
  try {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 2500);
    const res = await fetch(url, {
      headers: {
        Origin: `http://127.0.0.1:${port}`,
        Referer: `http://127.0.0.1:${port}/`,
        Accept: 'application/json',
      },
      signal: ctl.signal,
    });
    clearTimeout(timer);
    if (!res.ok) return false;
    const j = await res.json();
    // 必须有 teams 字段才算真的命中（防止别的服务碰巧 200）
    return j && Array.isArray(j.teams);
  } catch {
    return false;
  }
}

/** 列出本地监听端口（Windows 用 netstat，其它平台用 lsof）。 */
function listeningPorts() {
  const ports = new Set();
  try {
    if (process.platform === 'win32') {
      const out = execSync('netstat -ano -p TCP', { encoding: 'utf8', maxBuffer: 8 << 20 });
      for (const line of out.split('\n')) {
        // TCP  127.0.0.1:65082  0.0.0.0:0  LISTENING  1234
        const m = line.match(/TCP\s+127\.0\.0\.1:(\d+)\s+\S+\s+LISTENING/i);
        if (m) ports.add(Number(m[1]));
      }
    } else {
      const out = execSync('lsof -nP -iTCP -sTCP:LISTEN', { encoding: 'utf8', maxBuffer: 8 << 20 });
      for (const line of out.split('\n')) {
        const m = line.match(/127\.0\.0\.1:(\d+)/);
        if (m) ports.add(Number(m[1]));
      }
    }
  } catch { /* 忽略 */ }
  return [...ports].sort((a, b) => b - a);   // 大端口优先，DSH 通常用动态高端口
}

/** 从会话日志里找最近的 web URL（辅助信号）。 */
function portFromLogs() {
  const candidates = [];
  const sessDir = path.join(DSH, 'sessions');
  if (!fs.existsSync(sessDir)) return candidates;
  try {
    const files = [];
    const walk = (d) => {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, e.name);
        if (e.isDirectory()) walk(p);
        else if (e.name.endsWith('.jsonl')) files.push(p);
      }
    };
    walk(sessDir);
    // 只看最新的几个（日志是 zstd，这里读解压后的 .jsonl，没有就跳过）
    for (const f of files.slice(-5)) {
      const txt = fs.readFileSync(f, 'utf8');
      for (const m of txt.matchAll(/http:\/\/127\.0\.0\.1:(\d+)/g)) {
        candidates.push(Number(m[1]));
      }
    }
  } catch { /* 忽略 */ }
  return [...new Set(candidates)];
}

/**
 * 主入口：返回 { port, base }。
 * 找不到就抛错，并给出排查建议。
 */
export async function findBase() {
  // 1) 环境变量
  const envUrl = process.env.DSH_WEB_URL || process.env.DSH_URL;
  if (envUrl) {
    const m = envUrl.match(/:(\d+)/);
    if (m && await probe(Number(m[1]))) {
      return { port: Number(m[1]), base: `http://127.0.0.1:${m[1]}`, via: 'env' };
    }
  }
  const envPort = Number(process.env.DSH_WEB_PORT || process.env.DSH_PORT || 0);
  if (envPort && await probe(envPort)) {
    return { port: envPort, base: `http://127.0.0.1:${envPort}`, via: 'env-port' };
  }

  // 2) 扫描监听端口
  const ports = listeningPorts();
  for (const p of ports) {
    if (await probe(p)) {
      return { port: p, base: `http://127.0.0.1:${p}`, via: 'scan' };
    }
  }

  // 3) 从日志里读（可能过期，最后再试）
  for (const p of portFromLogs()) {
    if (await probe(p)) {
      return { port: p, base: `http://127.0.0.1:${p}`, via: 'log' };
    }
  }

  throw new Error(
    '找不到运行中的 DSH Web GUI。\n' +
    '  排查：\n' +
    '    1. DSH Desktop 是否在运行？\n' +
    '    2. 设环境变量 DSH_WEB_URL=http://127.0.0.1:<端口> 后重试\n' +
    `    3. 已扫描 ${ports.length} 个本地监听端口，均无响应 /dsh-agents/api/state`
  );
}

/** 带 dsh-agents 路由所需的同源头，调用任意 API。 */
export async function api(base, route, { method = 'GET', body } = {}) {
  const url = `${base}/dsh-agents/api/${route}`;
  const headers = {
    Origin: base,
    Referer: `${base}/`,
    Accept: 'application/json',
  };
  let payload;
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json; charset=utf-8';
    // 显式按 UTF-8 编码，避免中文被转成 ?
    payload = Buffer.from(JSON.stringify(body), 'utf8');
  }
  const res = await fetch(url, { method, headers, body: payload });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { raw: text }; }
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status} ${route}: ${json.message || text.slice(0, 200)}`);
    err.code = json.code;
    throw err;
  }
  return json;
}
