import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";

import { api, clearToken, post, saveToken } from "@/src/api";
import { copy, Lang } from "@/src/i18n";
import type { Profile, User } from "@/src/types";

if (Platform.OS !== "web") {
  WebBrowser.maybeCompleteAuthSession();
}

type Status = "loading" | "anon" | "onboarding" | "ready";

type AuthContextValue = {
  status: Status;
  user: User | null;
  profile: Profile | null;
  lang: Lang;
  t: (typeof copy)["en"];
  setLang: (lang: Lang) => void;
  signInEmail: (mode: "signin" | "signup", email: string, password: string, name: string) => Promise<void>;
  signInGoogle: () => Promise<void>;
  completeOnboarding: (profile: Profile) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const GOOGLE_AUTH_URL = (process.env.EXPO_PUBLIC_GOOGLE_AUTH_URL || "https://auth.emergentagent.com").replace(/\/$/, "");
const processedSessions = new Set<string>();

function extractSessionId(url: string): string | null {
  const match = url.match(/[?#&]session_id=([^&#]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [lang, setLang] = useState<Lang>("en");

  const applySession = useCallback(async () => {
    const result = await api<{ user: User; profile: Profile | null }>("/me");
    setUser(result.user);
    setProfile(result.profile);
    setLang(((result.profile?.language as Lang) || result.user.language || "en") as Lang);
    setStatus(result.profile ? "ready" : "onboarding");
  }, []);

  const exchangeSession = useCallback(
    async (sessionId: string) => {
      if (processedSessions.has(sessionId)) return;
      processedSessions.add(sessionId);
      const result = await post<{ session_token: string; user: User }>("/auth/session", { session_id: sessionId });
      await saveToken(result.session_token);
      await applySession();
    },
    [applySession],
  );

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      try {
        if (Platform.OS === "web" && typeof window !== "undefined") {
          const sessionId = extractSessionId(window.location.href);
          if (sessionId) {
            try {
              await exchangeSession(sessionId);
              window.history.replaceState(window.history.state, "", window.location.pathname);
            } catch {
              // fall through to stored-session check
            }
          }
        } else {
          const initialUrl = await Linking.getInitialURL();
          const sessionId = initialUrl ? extractSessionId(initialUrl) : null;
          if (sessionId) {
            try {
              await exchangeSession(sessionId);
            } catch {
              // fall through to stored-session check
            }
          }
        }
        await applySession();
      } catch {
        await clearToken();
        if (!cancelled) {
          setUser(null);
          setProfile(null);
          setStatus("anon");
        }
      }
    };
    boot();
    const subscription = Linking.addEventListener("url", ({ url }) => {
      const sessionId = extractSessionId(url);
      if (sessionId) exchangeSession(sessionId).catch(() => undefined);
    });
    return () => {
      cancelled = true;
      subscription.remove();
    };
  }, [applySession, exchangeSession]);

  const signInEmail = useCallback(
    async (mode: "signin" | "signup", email: string, password: string, name: string) => {
      const result = await post<{ token: string; user: User }>(mode === "signin" ? "/auth/login" : "/auth/signup", { email, password, name });
      await saveToken(result.token);
      await applySession();
    },
    [applySession],
  );

  const signInGoogle = useCallback(async () => {
    const redirectUrl = Platform.OS === "web" && typeof window !== "undefined" ? `${window.location.origin}/` : Linking.createURL("/");
    const authUrl = `${GOOGLE_AUTH_URL}/?redirect=${encodeURIComponent(redirectUrl)}`;
    if (Platform.OS === "web" && typeof window !== "undefined") {
      window.location.href = authUrl;
      return;
    }
    const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUrl);
    const url = (result as { url?: string }).url;
    if (url) {
      const sessionId = extractSessionId(url);
      if (sessionId) await exchangeSession(sessionId);
    }
    // Android may return `dismiss` with no URL even on success — the Linking
    // listener registered above captures the deep link in that case.
  }, [exchangeSession]);

  const completeOnboarding = useCallback((nextProfile: Profile) => {
    setProfile(nextProfile);
    setStatus("ready");
  }, []);

  const signOut = useCallback(async () => {
    await clearToken();
    setUser(null);
    setProfile(null);
    setStatus("anon");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, profile, lang, t: copy[lang], setLang, signInEmail, signInGoogle, completeOnboarding, signOut }),
    [status, user, profile, lang, signInEmail, signInGoogle, completeOnboarding, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
