import { makeRedirectUri, ResponseType, useAuthRequest, useAutoDiscovery } from "expo-auth-session";
import * as Crypto from "expo-crypto";
import * as WebBrowser from "expo-web-browser";
import { useCallback, useState } from "react";

// On web this closes the Google sign-in popup and hands the result back to the page that opened it.
WebBrowser.maybeCompleteAuthSession();

// The OAuth client ID the app signs in with (a "Web application" client in Google Cloud Console). Without it Google
// sign-in is switched off: the button is hidden and email sign-in works as normal.
export const GOOGLE_CLIENT_ID = (process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID || "").trim();
export const googleEnabled = GOOGLE_CLIENT_ID.length > 0;

export type GoogleSignInResult = { idToken: string; nonce: string };

// Asks Google for an ID token (OpenID Connect, implicit flow); the backend verifies it at POST /auth/google.
// Kept in this one file so it can be swapped for @react-native-google-signin/google-signin, which Expo recommends
// for store builds (it needs a development build, not Expo Go), without touching the rest of the app.
export function useGoogleSignIn() {
  const discovery = useAutoDiscovery("https://accounts.google.com");
  const [nonce, setNonce] = useState(() => Crypto.randomUUID());
  const [request, , promptAsync] = useAuthRequest(
    {
      clientId: GOOGLE_CLIENT_ID || "google-sign-in-not-configured",
      responseType: ResponseType.IdToken,
      scopes: ["openid", "profile", "email"],
      redirectUri: makeRedirectUri({ scheme: "wellstride", path: "oauthredirect" }),
      usePKCE: false,
      extraParams: { nonce },
    },
    discovery,
  );

  const getIdToken = useCallback(async (): Promise<GoogleSignInResult | null> => {
    if (!googleEnabled || !request) return null;
    const used = nonce;
    setNonce(Crypto.randomUUID()); // every attempt uses a fresh nonce
    const result = await promptAsync();
    const idToken = result.type === "success" ? result.params?.id_token : undefined;
    return idToken ? { idToken, nonce: used } : null;
  }, [nonce, promptAsync, request]);

  return { ready: googleEnabled && !!request, getIdToken };
}
