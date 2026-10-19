# Google Play store listing: draft for Wellstride

**Draft for review.** Nothing here has been entered in Play Console. Check each claim against the finished app before you submit,
because Google compares the listing, the Data Safety form and the app itself.

## App details

| Field | Draft |
|---|---|
| App name | Wellstride |
| Package name | `in.inkbrief.wellstride` |
| Default language | English (India). Add Telugu as a second listing language. |
| Category | **Health & Fitness** |
| Tags (pick what Play offers) | Nutrition, Diet & weight management, Fitness |
| Contact email | `SUPPORT_EMAIL` (default `support@inkbrief.in`): **confirm** |
| Privacy Policy URL | `https://<your-backend-domain>/privacy` |
| Account deletion URL | `https://<your-backend-domain>/delete-account` |
| Price | Free, no ads, no in-app purchases (as of this draft) |

## Short description (80 characters maximum)

> Indian meal plans, calorie logging and an AI wellness coach in English & Telugu.

(80 characters.) Alternative: "Daily Indian meal plans, food photo logging and a wellness coach, in Telugu too." (80)

## Full description (4000 characters maximum; this draft is about 1,900)

> **Wellness that feels like home.**
>
> Wellstride is a daily companion for eating well, moving more and feeling your best, built around the food Indian homes actually cook.
> Use it in English or Telugu.
>
> **What you can do**
> • **A meal plan made for you.** Tell us your goal, diet (vegetarian, eggetarian, non-vegetarian or vegan), allergies, cooking time and budget. Get a 7-day plan of familiar meals, and refresh it as your week changes.
> • **Log meals in seconds.** Tap to log a planned meal, edit it, or add your own. Calories and protein, carbs and fat update as you go.
> • **Log with a photo.** Take a picture of your plate and get an estimate of the dish and its nutrition. You check and correct it before saving.
> • **Ask the coach.** Ask for a quick recipe, a swap, or what to eat now. Answers use your goals and what you have eaten today.
> • **Track your progress.** Log your weight, see your trend, and get a simple weekly review.
> • **Stay active.** Log walks, strength and other activity and see calories burned. Optionally connect Health Connect to see steps and sleep.
> • **Gentle reminders.** Meals, water, movement and a weekly check-in, only if you turn them on.
>
> **Your data, your control**
> Wellstride is for adults aged 18 and over. Your account and everything in it can be deleted from Settings at any time. Meal photos are not kept after
> the food is recognised. To create plans, estimate nutrition and answer coach questions, some details (for example your meal photo, profile and chat messages)
> are sent securely to third-party AI services, as explained in our Privacy Policy.
>
> **Important**
> Wellstride gives general wellness and nutrition guidance. It is not medical advice and does not diagnose or treat any condition. Photo and calorie
> estimates can be wrong. Please talk to a doctor or dietitian before changing your diet or exercise, especially if you have a health condition,
> are pregnant or take medicine.

Before publishing, remove any line for a feature that is not in the build you upload (for example Health Connect until it is tested on a device).

## Graphics checklist (not produced here)

- App icon 512x512: `frontend/assets/store/icon-512.png` (placeholder, replace with the final mark).
- Feature graphic 1024x500.
- At least 2 phone screenshots (aim for 6-8): Today, Plan, Photo confirm, Coach, Progress, Settings. Take them in English and Telugu.

## Content rating (IARC questionnaire) notes

Answers expected from the app as built. Answer honestly in the questionnaire itself.

- Violence, sexual content, profanity, drugs, gambling: none.
- User-generated content / users interacting: **No user-to-user interaction.** The AI coach is a chat with a model, not other people; say so. Content a user types stays in their account.
- Shares user location: No. Digital purchases: No.
- Health information is collected (declared in Data Safety).
- Expected rating: Everyone / equivalent. The app itself is restricted to adults by its own 18+ rule; set Target audience to **18 and over** only.

## Target audience and content

- Target age group: **18 and over** (not 13-17, not under 13). The app is not designed for children, so it is not in the Families programme.
- Ads: **No ads.** News app: No. COVID-19 contact tracing or status: No. Government app: No. Financial features: No.
- App access: the app needs an account. In "App access", give Google a **test account** (email and password, created for review) and state that it is already verified
  and has consent recorded. Create it just before submitting, on the production backend.

## Health apps declaration (Play Console, "Health apps")

Suggested answers. Confirm each against the final build and the form's current wording.

| Question | Draft answer |
|---|---|
| Does the app have health features? | Yes: nutrition and weight management, fitness/activity tracking. |
| Is it a medical device, or does it diagnose, treat, cure or prevent disease? | **No.** General wellness only. The app and the policies say it is not medical advice. |
| Does it provide clinical or medical advice from a licensed professional? | No. AI-generated general wellness guidance, with a disclaimer shown in the app. |
| Does it access Health Connect? | Yes, read-only, **off by default**, only after the person turns it on and grants permission. Not sent to AI providers. |
| Health Connect data types and why | Steps, distance, active calories, exercise sessions, sleep: to show the day's activity and sleep next to meals. No writing to Health Connect. |
| Handles sensitive health information? | Yes: height, weight, conditions and allergies the person enters. Shown in Data Safety, policy and consent at sign-up. |
| Clinical trial, research, or government use? | No. |
| Privacy policy covers health data and AI processing? | Yes: `/privacy` section 2 and 4. |

Health Connect declaration: Play asks for a video of the permission flow and the feature; record it from the Android build once Phase 5 device testing is done.

## Pre-launch checklist

1. Production backend on HTTPS; policy and deletion URLs are live and open without login.
2. Support email confirmed and monitored.
3. Policies reviewed; `docs/PLAY_DATA_SAFETY.md` answers match.
4. Real screenshots and graphics.
5. Test account created for Google's reviewers.
6. Closed testing track with testers (Google requires testing for new personal developer accounts before production; check the current rule on your account).
