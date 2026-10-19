"""Public legal pages (Privacy Policy, Terms, how to delete an account), served as plain HTML with no login.

These are plain-language drafts for the owner to have reviewed before launch; they are not legal advice.
CONSENT_VERSION is stored on a user when they agree. Bump it whenever the Privacy Policy or Terms change in a way people
must agree to again; users on an older version are asked once on next launch.
"""
import os
from html import escape

CONSENT_VERSION = "2026-10-19"
LAST_UPDATED = "19 October 2026"


def support_email() -> str:
    return (os.getenv("SUPPORT_EMAIL") or "support@inkbrief.in").strip()


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Wellstride</title>
<style>
  body {{ margin: 0; background: #fdfbf7; color: #2b2a26; font: 17px/1.65 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 720px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 30px; margin: 0 0 4px; color: #3d5a4c; }}
  h2 {{ font-size: 20px; margin: 32px 0 8px; color: #3d5a4c; }}
  p, li {{ margin: 8px 0; }}
  .meta {{ color: #6b6a63; font-size: 14px; }}
  a {{ color: #3d5a4c; }}
  nav {{ margin-top: 40px; font-size: 14px; }}
  nav a {{ margin-right: 16px; }}
</style>
</head>
<body>
<main>
<h1>{title}</h1>
<p class="meta">Wellstride · Version {version} · Last updated {updated}</p>
{body}
<nav><a href="/privacy">Privacy Policy</a><a href="/terms">Terms of Use</a><a href="/delete-account">Delete your account</a></nav>
</main>
</body>
</html>
"""


def privacy_body(email: str) -> str:
    return f"""
<p>Wellstride is a food, activity and wellness app for adults in India. This policy explains, in plain words, what we collect,
why, who else sees it, and the choices you have. If you have a question, write to <a href="mailto:{email}">{email}</a>.</p>

<h2>1. Who can use Wellstride</h2>
<p>Wellstride is for people <strong>aged 18 and over</strong>. We do not knowingly collect information from anyone under 18.
If you learn that a child has made an account, tell us at {email} and we will delete it.</p>

<h2>2. What we collect</h2>
<ul>
<li><strong>Account:</strong> your name, email address and a password (stored only as a one-way hash), or your Google account email and name if you sign in with Google. Your chosen language.</li>
<li><strong>Profile and health details you enter:</strong> age, sex, height, weight and target weight, activity level, dietary preferences, allergies, foods you dislike, cooking time, budget, your goal, and any <strong>health conditions</strong> you choose to list (for example diabetes or blood pressure).</li>
<li><strong>What you log:</strong> meals, activities, weight entries, your meal plan, and your reminder and privacy settings.</li>
<li><strong>Meal photos</strong> that you choose to take or upload for food recognition.</li>
<li><strong>Coach messages:</strong> what you type to the AI coach and its replies.</li>
<li><strong>Phone health data</strong> (steps, activity) only if you turn on the optional health connection and grant permission.</li>
<li><strong>Technical data:</strong> your time zone and the IP address of your requests, used for security and to limit abuse. We do not use advertising identifiers.</li>
</ul>

<h2>3. Why we use it</h2>
<p>To run the app: to build your meal plan, estimate calories, show your progress, answer coach questions, send the reminders you ask for, keep your
account secure, and fix problems. We do not sell your data, and we do not use it for advertising.</p>

<h2>4. AI providers: who else sees your data</h2>
<p>Wellstride uses third-party AI services to create results for you. When you use these features, the information needed for the request is sent to them over an encrypted connection:</p>
<ul>
<li><strong>Google (Gemini)</strong> receives <strong>meal photos</strong> you submit, to identify the food and estimate nutrition.</li>
<li><strong>Groq</strong> receives your <strong>profile and health details, your recent meals, activity and weight, and your coach messages</strong>, to write your meal plan, coach answers and weekly review. If photo recognition falls back to Groq, it receives the meal photo too.</li>
</ul>
<p>We send only what the request needs and do not send your email address or password. These providers process the data under their own terms and privacy
policies, and may process it outside India. Please do not include other people's personal information in photos or messages.</p>

<h2>5. How long we keep it</h2>
<p>We keep your data while your account is open. When you delete your account (see section 8), your account and all the data above are removed from our
database immediately. Server logs that may contain technical information are kept for a short time (up to 30 days) and then removed.
Anything an AI provider keeps is governed by that provider's own policy.</p>

<h2>6. Security</h2>
<p>Connections to Wellstride are encrypted (HTTPS). Passwords are hashed with bcrypt and never stored in plain text. Sign-in attempts are rate-limited.
No system is perfectly secure, so please choose a strong, unique password and keep your phone locked.</p>

<h2>7. Wellness guidance, not medical advice</h2>
<p>Wellstride gives general wellness and nutrition guidance. It is <strong>not medical advice</strong> and does not diagnose, treat or prevent any
condition. Photo and calorie estimates can be wrong. Talk to a doctor or registered dietitian before changing your diet or exercise,
especially if you are pregnant, have a medical condition or take medicine.</p>

<h2>8. Your rights and choices</h2>
<p>You can use these rights under India's Digital Personal Data Protection Act, 2023 and similar laws:</p>
<ul>
<li><strong>Access:</strong> see your information in the app, or ask us for a copy.</li>
<li><strong>Correction:</strong> change your profile and logs in the app, or ask us to fix anything.</li>
<li><strong>Deletion:</strong> in the app, go to <em>Settings, Delete account</em>. Or follow <a href="/delete-account">these steps</a>, or email {email} from your account address.</li>
<li><strong>Withdraw consent:</strong> you can stop using the app and delete your account at any time. Optional features (photos, health connection, reminders) can be turned off in Settings.</li>
<li><strong>Grievance:</strong> if you have a complaint about how your data is handled, write to {email} with the subject "Grievance". We will reply within 7 days and resolve it within 30 days.</li>
</ul>

<h2>9. Changes</h2>
<p>If we change this policy in a way that matters, we will update the date above and ask you to agree again in the app.</p>

<h2>10. Contact</h2>
<p><a href="mailto:{email}">{email}</a></p>

<h2>తెలుగు సారాంశం</h2>
<p>Wellstride 18 ఏళ్లు, ఆపై వయస్సు ఉన్నవారి కోసం. మేము మీ ఖాతా, ప్రొఫైల్, ఆరోగ్య వివరాలు, భోజనాలు, కార్యకలాపాలు, బరువు, భోజన ఫొటోలు మరియు కోచ్ సందేశాలను నిల్వ చేస్తాము.
భోజన ఫొటోలు Google (Gemini)కి, మీ ప్రొఫైల్ మరియు సందేశాలు Groqకి ఫలితాలు ఇవ్వడానికి పంపబడతాయి. ఇది వైద్య సలహా కాదు.
సెట్టింగ్స్‌లో "ఖాతాను తొలగించండి" ద్వారా మీ ఖాతా మరియు మొత్తం డేటాను ఎప్పుడైనా తొలగించవచ్చు. సంప్రదించండి: {email}</p>
"""


def terms_body(email: str) -> str:
    return f"""
<p>These Terms of Use are the agreement between you and Wellstride for using the Wellstride app and website. By creating an account you
confirm that you have read them and the <a href="/privacy">Privacy Policy</a> and agree to both.</p>

<h2>1. You must be 18 or over</h2>
<p>Wellstride is only for adults aged 18 and over. By signing up you confirm that you are at least 18.</p>

<h2>2. Wellness guidance, not medical advice</h2>
<p>Everything in Wellstride, including meal plans, calorie and nutrition estimates, photo recognition, coach answers and weekly reviews, is
general information for wellness. It is <strong>not medical advice</strong>, diagnosis or treatment, and it does not replace a doctor or dietitian.
Estimates can be wrong. Do not ignore professional advice because of something in the app. If you feel unwell, seek medical help.
Check ingredients yourself if you have allergies.</p>

<h2>3. Your account</h2>
<p>Give accurate information and keep your password private. You are responsible for activity on your account. Tell us at
{email} if you think someone else has accessed it.</p>

<h2>4. Acceptable use</h2>
<ul>
<li>Do not break the law, attack or overload the service, or try to access other people's data.</li>
<li>Do not upload photos or messages that are unlawful, or that contain other people's private information, without their permission.</li>
<li>Do not use automated tools to scrape the app or to abuse the AI features.</li>
</ul>

<h2>5. AI features and third parties</h2>
<p>Some features use third-party AI providers (Google Gemini and Groq) as described in the Privacy Policy. Their answers can be incomplete or
inaccurate, and the services can be busy or unavailable. We do not guarantee that any feature will always work.</p>

<h2>6. Your content</h2>
<p>You keep ownership of what you enter and upload. You give Wellstride permission to store and process it only to provide the service to you,
as described in the Privacy Policy.</p>

<h2>7. Ending your account</h2>
<p>You can delete your account at any time in <em>Settings, Delete account</em>. We may suspend or close accounts that break these Terms or
put others at risk.</p>

<h2>8. Limits on our responsibility</h2>
<p>Wellstride is provided "as is". To the extent the law allows, we are not responsible for losses that come from relying on estimates or
guidance in the app, or from interruptions to the service. Nothing here limits rights you have under Indian consumer law.</p>

<h2>9. Changes</h2>
<p>We may update these Terms. If a change matters, we will update the date above and ask you to agree again in the app.</p>

<h2>10. Governing law and contact</h2>
<p>These Terms are governed by the laws of India. Questions or complaints: <a href="mailto:{email}">{email}</a>.</p>
"""


def delete_account_body(email: str) -> str:
    return f"""
<p>You can delete your Wellstride account and all of your data at any time.</p>

<h2>In the app (fastest)</h2>
<ol>
<li>Open Wellstride and tap the settings icon.</li>
<li>Tap <strong>Delete account</strong>.</li>
<li>Confirm by typing <strong>DELETE</strong> (and your password if you use one).</li>
</ol>
<p>Your account and all of your data are deleted straight away and you are signed out.</p>

<h2>If you cannot open the app</h2>
<p>Email <a href="mailto:{email}">{email}</a> from the email address on your account with the subject "Delete my account". We will delete
the account and confirm by email within 7 days.</p>

<h2>What is deleted</h2>
<p>Your account and sign-in sessions, profile and health details, meals, activities, weight entries, meal plans, coach messages, health data
synced from your phone, reminder and privacy settings. Meal photos are not kept after recognition. Copies in routine backups and
short-term server logs are removed within 30 days. Some information may be kept longer only if the law requires it.</p>
"""


def render(page: str) -> str:
    email = escape(support_email())
    title, body = {
        "privacy": ("Privacy Policy", privacy_body),
        "terms": ("Terms of Use", terms_body),
        "delete-account": ("Delete your account", delete_account_body),
    }[page]
    return PAGE.format(title=title, version=CONSENT_VERSION, updated=LAST_UPDATED, body=body(email))
