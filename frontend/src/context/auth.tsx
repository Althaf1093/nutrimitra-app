import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, clearToken, getToken, post, saveToken } from "@/src/api";
import { copy, Lang } from "@/src/i18n";
import { useGoogleSignIn } from "@/src/lib/google-auth";
import { setFontLanguage } from "@/src/theme";
import { storage } from "@/src/utils/storage";
import type { Profile, User } from "@/src/types";

type Status = "loading" | "anon" | "consent" | "onboarding" | "ready";

type AuthContextValue = {
  status: Status;
  user: User | null;
  profile: Profile | null;
  lang: Lang;
  t: (typeof copy)["en"];
  setLang: (lang: Lang) => void;
  signInEmail: (mode: "signin" | "signup", email: string, password: string, name: string, acceptTerms?: boolean) => Promise<void>;
  signInGoogle: (acceptTerms?: boolean) => Promise<void>;
  acceptConsent: () => Promise<void>;
  refreshUser: () => Promise<void>;
  completeOnboarding: (profile: Profile) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [lang, setLang] = useState<Lang>("en");

  useEffect(() => {
    setFontLanguage(lang);
  }, [lang]);

  const applySession = useCallback(async () => {
    const result = await api<{ user: User; profile: Profile | null }>("/me");
    setUser(result.user);
    setProfile(result.profile);
    const storedLang = await storage.getItem<Lang | "">("nutrimitra.lang", "");
    const resolvedLang = storedLang === "te" || storedLang === "en" ? storedLang : (((result.profile?.language as Lang) || result.user.language || "en") as Lang);
    setLang(resolvedLang);
    // A saved profile under 18 (from before the age rule) goes back through onboarding to re-enter an adult age.
    // Accounts that have not agreed to the current Terms and Privacy Policy are asked once, before anything else.
    setStatus(result.user.needs_consent ? "consent" : result.profile && Number(result.profile.age) >= 18 ? "ready" : "onboarding");
  }, []);

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      try {
        // Nothing saved means nobody is signed in: skip the request that would only come back 401.
        if (!(await getToken())) {
          if (!cancelled) setStatus("anon");
          return;
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
    return () => {
      cancelled = true;
    };
  }, [applySession]);

  const signInEmail = useCallback(
    async (mode: "signin" | "signup", email: string, password: string, name: string, acceptTerms = false) => {
      const result = await post<{ token: string; user: User }>(mode === "signin" ? "/auth/login" : "/auth/signup", mode === "signin" ? { email, password, name } : { email, password, name, accept_terms: acceptTerms });
      await saveToken(result.token);
      await applySession();
    },
    [applySession],
  );

  const googleSignIn = useGoogleSignIn();
  const getGoogleIdToken = googleSignIn.getIdToken;
  const signInGoogle = useCallback(async (acceptTerms = false) => {
    const result = await getGoogleIdToken();
    if (!result) return; // closed or cancelled
    const response = await post<{ token: string; user: User }>("/auth/google", { id_token: result.idToken, nonce: result.nonce, accept_terms: acceptTerms });
    await saveToken(response.token);
    await applySession();
  }, [applySession, getGoogleIdToken]);


  const acceptConsent = useCallback(async () => {
    await post("/consent", { accept_terms: true });
    await applySession();
  }, [applySession]);

  const refreshUser = useCallback(async () => {
    await applySession();
  }, [applySession]);

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

  const changeLang = useCallback((next: Lang) => {
    setLang(next);
    storage.setItem("nutrimitra.lang", next);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, profile, lang, t: copy[lang], setLang: changeLang, signInEmail, signInGoogle, acceptConsent, refreshUser, completeOnboarding, signOut }),
    [status, user, profile, lang, changeLang, signInEmail, signInGoogle, acceptConsent, refreshUser, completeOnboarding, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
