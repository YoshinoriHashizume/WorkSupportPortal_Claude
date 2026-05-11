import "server-only";

import fs from "node:fs";

import oracledb from "oracledb";
import { getOracleConnectEnv } from "@/infrastructure/oracle/config";

/** ORACLE_CLIENT_LIB_DIR がコンテナ／プロセスで欠けているときの既定（Dockerfile のレイアウト）。 */
function oracleInstantClientLibDir(): string | undefined {
  const fromEnv = process.env.ORACLE_CLIENT_LIB_DIR?.trim();
  if (fromEnv) return fromEnv;
  const dockerPath = "/opt/oracle/instantclient";
  try {
    if (process.platform !== "win32" && fs.existsSync(`${dockerPath}/libclntsh.so`)) {
      return dockerPath;
    }
  } catch {
    /* 起動時の fs エラーは無視 */
  }
  return undefined;
}

let pool: oracledb.Pool | null = null;
let thickModeReady = false;

function envFlag(name: string): boolean {
  const v = process.env[name]?.trim().toLowerCase();
  return v === "true" || v === "1" || v === "yes";
}

/** Instant Client を使わず Thin のみで接続する（DB ユーザーのパスワード検証子が 11G/12C 以降である必要あり。10G 系は NJS-116）。 */
export function isOracleThinOnlyMode(): boolean {
  return envFlag("ORACLE_USE_THIN");
}

/**
 * 32-bit 版 Instant Client を明示的に読み込む（ORACLE_CLIENT_LIB_DIR 等に 32-bit 展開先を指定）。
 * 32-bit の libclntsh / oci は 64-bit の Node からは読み込めないため、Node も 32-bit（process.arch === ia32）である必要がある。
 */
export function isOracle32BitClientMode(): boolean {
  return envFlag("ORACLE_USE_32BIT_CLIENT");
}

/**
 * node-oracledb 6 の既定は Thin モード。DB 側の古いパスワード検証子（例: 0x939 / 10G）では Thin が使えず NJS-116 となる。
 * Instant Client による Thick で接続する（https://node-oracledb.readthedocs.io/en/latest/user_guide/initialization.html）。
 * クライアントを入れずに Thin で繋ぐには DB 側で当該ユーザーのパスワードを再設定し ORACLE_USE_THIN=true を参照。
 */
function ensureOracleThickMode(): void {
  if (thickModeReady) return;

  if (isOracle32BitClientMode()) {
    if (process.arch !== "ia32") {
      throw new Error(
        "ORACLE_USE_32BIT_CLIENT=true ですが、この Node.js は 32-bit ではありません（process.arch=" +
          `${process.arch}）。32-bit の Oracle Instant Client を使うには 32-bit 版の Node.js で起動してください。` +
          "64-bit Node で 32-bit クライアントのみを使うことはできません。64-bit 用 Instant Client を使う場合は ORACLE_USE_32BIT_CLIENT を外してください。",
      );
    }
    const libDir =
      process.env.ORACLE_CLIENT_LIB_DIR_32?.trim() ||
      process.env.ORACLE_CLIENT_LIB_DIR?.trim();
    if (!libDir) {
      throw new Error(
        "ORACLE_USE_32BIT_CLIENT=true のときは、32-bit Instant Client の展開先を ORACLE_CLIENT_LIB_DIR または ORACLE_CLIENT_LIB_DIR_32 に設定してください。",
      );
    }
    try {
      oracledb.initOracleClient({ libDir });
      thickModeReady = true;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (/already been called|already initialized|NJS-064|DPY-3010/i.test(msg)) {
        thickModeReady = true;
        return;
      }
      throw new Error(
        `${msg} — 32-bit Instant Client が ${libDir} に正しく展開されているか（oci.dll / libclntsh.so）、` +
          "Oracle の「Instant Client for Windows/Linux 32-bit」パッケージであることを確認してください。",
      );
    }
    return;
  }

  try {
    const libDir = oracleInstantClientLibDir();
    if (libDir) {
      oracledb.initOracleClient({ libDir });
    } else {
      oracledb.initOracleClient();
    }
    thickModeReady = true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (/already been called|already initialized|NJS-064|DPY-3010/i.test(msg)) {
      thickModeReady = true;
      return;
    }
    const osHint =
      process.platform === "win32"
        ? "PATH に Instant Client を含めるか、ORACLE_CLIENT_LIB_DIR に oci.dll があるフォルダを設定してください。"
        : "ORACLE_CLIENT_LIB_DIR に libclntsh.so があるディレクトリを設定するか、LD_LIBRARY_PATH にそのディレクトリを追加し ldconfig 等で共有ライブラリとして認識させてください。";
    const archHint =
      process.arch === "ia32"
        ? "この Node は 32-bit（ia32）です。32-bit 用の Instant Client を入れるか、ORACLE_USE_32BIT_CLIENT=true と ORACLE_CLIENT_LIB_DIR を設定してください。"
        : "この Node は 64-bit 系（例: x64）です。32-bit 専用の Instant Client ではなく、同じビット幅のパッケージ（多くは x86-64 / win64 用）を入れてください。確認: node -p \"process.arch\"。";
    throw new Error(
      `${msg} — Oracle Instant Client（Basic または Basic Light）が必要です。${archHint} ${osHint}（Thick モード / NJS-116 対策）`,
    );
  }
}

export function isOracleConfigured(): boolean {
  return Boolean(process.env.ORACLE_PASSWORD?.trim());
}

/** 必須 Oracle 環境変数の一覧。値は `.env.local` / シークレットに集約する。 */
const REQUIRED_ORACLE_ENVS = [
  "ORACLE_HOST",
  "ORACLE_PORT",
  "ORACLE_SID",
  "ORACLE_USER",
  "ORACLE_PASSWORD",
] as const;

function missingOracleEnvKeys(env: ReturnType<typeof getOracleConnectEnv>): string[] {
  const missing: string[] = [];
  if (!env.host) missing.push("ORACLE_HOST");
  if (env.port == null) missing.push("ORACLE_PORT");
  if (!env.sid) missing.push("ORACLE_SID");
  if (!env.user) missing.push("ORACLE_USER");
  if (!env.password) missing.push("ORACLE_PASSWORD");
  return missing;
}

export async function getOraclePool(): Promise<oracledb.Pool> {
  if (pool) return pool;
  const e = getOracleConnectEnv();
  const missing = missingOracleEnvKeys(e);
  if (missing.length > 0) {
    throw new Error(
      `Oracle 接続用の環境変数が未設定です: ${missing.join(", ")}（必須: ${REQUIRED_ORACLE_ENVS.join(", ")}）。値は \`.env.local\` または本番のシークレットに設定してください（接続パラメータの仕様: アプリケーション仕様書 §8.2.1）。`,
    );
  }
  if (!isOracleThinOnlyMode()) {
    ensureOracleThickMode();
  }
  const connectString = `(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=${e.host})(PORT=${e.port}))(CONNECT_DATA=(SID=${e.sid})))`;
  pool = await oracledb.createPool({
    user: e.user,
    password: e.password,
    connectString,
    poolMin: 0,
    poolMax: 6,
    poolIncrement: 1,
  });
  return pool;
}
