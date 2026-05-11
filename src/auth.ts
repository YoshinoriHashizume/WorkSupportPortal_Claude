import NextAuth from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter";
import Credentials from "next-auth/providers/credentials";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";
import { JWTSessionError } from "@auth/core/errors";
import { prisma } from "@/infrastructure/persistence/prisma/client";
import { authConfig } from "@/auth.config";
import { ensureUserHasMenuAccess } from "@/domains/identity/application/bootstrap-menu-access";

/** 未設定だと開発サーバー再起動のたびに鍵が変わり、既存 Cookie が JWTSessionError になる */
function getAuthSecret(): string {
  const s = process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET;
  if (!s) {
    throw new Error(
      "AUTH_SECRET（または NEXTAUTH_SECRET）を .env.local に設定してください。`openssl rand -base64 32` などで生成できます。",
    );
  }
  return s;
}

const isDev = process.env.NODE_ENV === "development";
const devMode = process.env.AUTH_DEV_MODE === "true";

const providers = [];

if (isDev && devMode) {
  providers.push(
    Credentials({
      id: "dev-local",
      name: "開発用ログイン",
      credentials: {
        email: { label: "メール", type: "email" },
        password: { label: "パスワード", type: "password" },
      },
      async authorize(credentials) {
        const email = credentials?.email as string | undefined;
        const password = credentials?.password as string | undefined;
        if (email !== "dev@local" || password !== "dev") return null;

        const user = await prisma.user.upsert({
          where: { email: "dev@local" },
          update: { name: "開発ユーザー" },
          create: {
            email: "dev@local",
            name: "開発ユーザー",
          },
        });
        await ensureUserHasMenuAccess(prisma, user.id);
        return { id: user.id, name: user.name, email: user.email };
      },
    }),
  );
}

const entraId = process.env.AUTH_MICROSOFT_ENTRA_ID_ID;
const entraSecret = process.env.AUTH_MICROSOFT_ENTRA_ID_SECRET;
const entraIssuer = process.env.AUTH_MICROSOFT_ENTRA_ID_ISSUER;

if (entraId && entraSecret) {
  providers.push(
    MicrosoftEntraID({
      clientId: entraId,
      clientSecret: entraSecret,
      ...(entraIssuer ? { issuer: entraIssuer } : {}),
    }),
  );
}

if (providers.length === 0) {
  providers.push(
    Credentials({
      id: "unconfigured",
      name: "unconfigured",
      credentials: {},
      authorize: async () => null,
    }),
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(prisma),
  secret: getAuthSecret(),
  // Edge middleware でも検証しやすいよう JWT（DB セッションは未使用）
  session: { strategy: "jwt", maxAge: 30 * 24 * 60 * 60 },
  ...authConfig,
  providers,
  logger: {
    error(error) {
      // 秘密鍵変更・古い Cookie では復号失敗しがち。Cookie は core 側で削除済み
      if (error instanceof JWTSessionError) {
        if (isDev) {
          console.warn(
            "[auth] セッション Cookie を復号できませんでした（無視してログイン画面を表示します）。AUTH_SECRET を変えた場合はブラウザの localhost の Cookie を削除してください。",
          );
        }
        return;
      }
      const name =
        error instanceof Error && "type" in error
          ? String((error as { type?: string }).type)
          : error instanceof Error
            ? error.name
            : "Error";
      console.error(`[auth][error] ${name}:`, error);
    },
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        // session コールバックは token.sub を user.id にマッピングするため必須
        token.sub = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user && token.sub) {
        session.user.id = token.sub;
      }
      return session;
    },
  },
  events: {
    async signIn({ user }) {
      if (user?.id) {
        await ensureUserHasMenuAccess(prisma, user.id);
      }
    },
  },
});
