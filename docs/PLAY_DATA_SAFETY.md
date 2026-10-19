# Google Play Data Safety: draft answers for Wellstride

**Draft for review. Not legal advice.** Prepared from the code on `main` (October 2026). Re-check it against the code before every
store release, and have the Privacy Policy (`/privacy`) and these answers reviewed together: Google compares them.

Support email used in the policies: `SUPPORT_EMAIL` (default `support@inkbrief.in`): **confirm it.**

## 1. Overview answers

| Play Console question | Answer | Why |
|---|---|---|
| Does your app collect or share any of the required user data types? | **Yes** | See the table below. |
| Is all of the user data collected by your app encrypted in transit? | **Yes** | The app talks to the backend over HTTPS only. **Check once the production backend is live (Phase 6):** it must be served over HTTPS, not the `http://` LAN address used in development. |
| Do you provide a way for users to request that their data is deleted? | **Yes** | In the app: Settings, Delete account (removes the account and every collection, immediately). Public URL for the Play Console: `https://<your-backend-domain>/delete-account`. Email request: `SUPPORT_EMAIL`. |
| Data deletion URL | `https://<your-backend-domain>/delete-account` | Served by the backend, no login. |
| Privacy Policy URL | `https://<your-backend-domain>/privacy` | Served by the backend, no login. |
| Committed to the Play Families Policy? | **No** | The app is for adults only (18+). Target audience in Play Console: 18 and over. |
| Independent security review? | No | Not done. |

## 2. Data types

"Shared" below follows Google's definition. **Decision for you:** the meal photo, profile, health details and coach messages are sent to
Google (Gemini) and Groq to produce results. Google treats a provider that only processes data on your behalf, under terms that stop it
using the data for its own purposes, as a *service provider*, which is not "sharing". Whether Gemini's and Groq's terms for the plan you use
meet that (some free tiers allow the provider to use submitted content to improve its products) is something to check in their current terms.
**Until you have checked, the safe answer is to declare these as Shared** (the "Shared" column below is filled in that way).

| Data type (Play category) | What it is in Wellstride | Collected | Shared (with whom) | Purpose | Optional? |
|---|---|---|---|---|---|
| **Personal info: Email address** | Sign-up email (or Google account email) | Yes | No | Account management; password reset and verification emails (sent through Resend) | Required to have an account |
| **Personal info: Name** | The name you enter (defaults to the start of your email) | Yes | No | Account management; greeting in the app | Optional (a default is used) |
| **Personal info: User IDs** | Random account ID | Yes | No | Account management | Required |
| **Personal info: Other info** | Age, sex (can be "Prefer not to say"), language | Yes | Yes: Groq (inside the profile sent for plans and coach answers) | App functionality; personalisation; age check (18+) | Age required (18+ rule); sex optional; language chosen by you |
| **Health and fitness: Health info** | Height, weight, target weight, weight log, health conditions you list, allergies, dietary preferences, sleep (if Health Connect is turned on) | Yes | Yes: Groq (profile, conditions, allergies, weight history for the plan and coach). Sleep is not sent to AI | App functionality; personalisation | Height, weight and target are required to build a plan; conditions, allergies, sleep are optional |
| **Health and fitness: Fitness info** | Activities you log (type, minutes, distance, calories), steps, distance, exercise sessions (Health Connect, if turned on) | Yes | Yes: Groq (logged activities in the plan context). Health Connect data is not sent to AI | App functionality; personalisation | Optional |
| **Photos and videos: Photos** | A meal photo you choose to take or upload | Yes, processed but **not stored**: the image is sent for recognition and discarded | Yes: Google (Gemini); Groq if it is used as the backup recognizer | App functionality (identify the food, estimate nutrition) | Optional |
| **Messages: Other in-app messages** | What you type to the AI coach, and its replies | Yes | Yes: Groq | App functionality | Optional |
| **App activity: Other user-generated content** | Meals you log or edit, meal plans, reminder preferences, privacy toggles | Yes | Yes: Groq (meals inside the plan and coach context) | App functionality; personalisation | Optional |
| **Device or other IDs** | None collected (no advertising ID, no analytics SDK) | No | n/a | n/a | n/a |
| **Location, Contacts, Financial info, Calendar, Web browsing, Audio** | Not collected | No | n/a | n/a | n/a |
| **App info and performance** (crash logs, diagnostics) | Not collected by a third-party SDK. The server keeps short-lived technical logs (request errors, no health content, no images, no keys) | See note | No | Security, fixing bugs | n/a |

**IP addresses.** The server uses the IP address of requests only to limit repeated sign-in attempts (kept in memory, not stored in the
database) and it can appear in short-lived web-server logs. Play's list has no "IP address" row; many apps declare nothing for this, but if you
prefer to be conservative, declare *Device or other IDs* as collected for "Security, fraud prevention", not shared. Decide with the reviewer of the policy.

**The "Analytics" switch in Settings** stores a preference only. There is no analytics or advertising SDK in the app today
(`frontend/package.json`). If one is ever added, this document and the policy must change first.

## 3. Security practices (the section at the bottom of the form)

- Data is encrypted in transit: **Yes** (HTTPS).
- Users can request data deletion: **Yes** (in-app and public URL).
- Passwords are stored only as bcrypt hashes; reset and verification codes are stored only as keyed hashes.
- The sign-in session token is kept in the phone's secure storage (`expo-secure-store`).
- Data at rest: stored in MongoDB. Play does not ask about it, but turn on your database host's encryption at rest when you choose a host (Phase 6).

## 4. Permissions the app asks for, and why (for the Play Console permission forms)

| Permission | Where | Why |
|---|---|---|
| `CAMERA` | Photo meal logging | Take a photo of a meal to estimate nutrition. Optional: you can pick a gallery photo or log by hand. |
| `POST_NOTIFICATIONS` | Reminders | Meal, water, movement and weekly reminders you turn on. Scheduled on the phone; nothing is sent from a server. |
| Health Connect: `READ_STEPS`, `READ_DISTANCE`, `READ_ACTIVE_CALORIES_BURNED`, `READ_EXERCISE`, `READ_SLEEP` | Settings, "HealthKit / Health Connect" switch (off by default) | Show today's activity and sleep next to meals. Read-only, only after you turn it on and grant it in Android. Not sent to AI providers. |

The Health Connect permission declaration in Play Console needs a short video showing the feature and the in-app privacy policy link
(Settings, Privacy and terms). See the answers in `docs/PLAY_STORE_LISTING.md`.

## 5. What to confirm before you submit

1. Production backend runs on HTTPS; the URLs above are real.
2. Gemini and Groq terms for the plan in use (sharing versus service-provider answer, section 2).
3. Support email and the grievance contact in the policy.
4. Someone qualified has reviewed the Privacy Policy and Terms.
5. Every row above still matches the code (new collections, new SDKs, new permissions).
