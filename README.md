# RepTrack — Personal Gym Tracker

A responsive Streamlit fitness app with personal profiles, cloud authentication, workout logging, exercise guidance, a history calendar, daily body-weight tracking, progress charts, personal records, and data export.

## Highlights

- Profile creation with full name and username. The home greeting uses the saved profile name, e.g. **“Hey, [your name]. What are we training today?”**
- Email/password authentication through Supabase Auth in cloud mode. Username login is enabled if the server-only `SUPABASE_SERVICE_ROLE_KEY` is configured; email login always remains available.
- Local development mode with SQLite and salted PBKDF2 password hashes so you can test without configuring Supabase first.
- 50+ seeded exercises with target muscles, equipment, exercise instructions and demo-search links, plus user-created exercises.
- Multiple muscle group selection, workout sessions, individual set/rep/weight logging, RPE, notes, per-set editing/deletion, and workout completion/abandonment.
- Calendar with completed-workout marks and details for historical sessions.
- Daily body-weight log, unit conversion (kg/lb), Plotly charts, workout-frequency charts, streaks, volume summaries, muscle-group balance and saved-set records.
- Dark/light profile preference, weekly goal, optional weight goal, and JSON/CSV export.
- Supabase RLS policies for user-owned database records.

## 1. Run locally (quick test)

You need Python 3.10+ (Python 3.11 is a good choice).

```bash
cd reptrack
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate      # Windows PowerShell
pip install -r requirements.txt
streamlit run app.py
```

If Supabase credentials are not configured, the app runs in **local SQLite development mode**. Create a profile from the sign-up tab; you can sign in later using your username or email and password. Local mode stores data in `data/reptrack_local.db` on that machine.

> Important: Streamlit Community Cloud's app filesystem should not be treated as permanent storage. For online deployment and cross-device sync, configure Supabase as described below.

## 2. Create the cloud database

1. Create a project at [Supabase](https://supabase.com/).
2. Open **SQL Editor** in your new project.
3. Open `supabase/schema.sql` from this repository, copy the complete SQL, and run it in the SQL Editor. It creates the tables, indexes, Row Level Security policies, and shared exercise library.
4. In Supabase, open **Project Settings → API** (the API keys area) and copy the project URL and the publishable/anon key. Do not put a service-role key into source code.
5. In **Authentication → URL Configuration**, set the Site URL to your deployed Streamlit app URL after deployment. Configure email confirmation and reset-password settings to suit your account policy. If email confirmation is enabled, new users need to confirm their email before their first login.

### Required Streamlit secrets

In the deployed app, open **App settings → Secrets** and add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_ANON_KEY = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
```

### Optional username login

Supabase's standard password sign-in authenticates by email. To let users enter either their username or email in the login field, add the service-role key as an **optional server-side Streamlit secret**:

```toml
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
```

The app uses this key only in server-side code to look up the email for a submitted username, then authenticates the submitted password through Supabase Auth. Never commit this key to GitHub, never put it into `app.py`, and never expose it in frontend code. If you prefer not to store a service-role key in Streamlit Secrets, omit it and use email/password login; Supabase RLS still protects user-owned app records.

You can also put these secret values into `.streamlit/secrets.toml` for local cloud-mode testing. That file is ignored by Git. Do not commit your real secrets.

## 3. Deploy to Streamlit Community Cloud

1. Create a new GitHub repository, for example `reptrack`.
2. Upload the **contents of this project folder** to the repository root (so `app.py`, `requirements.txt`, `services/`, `components/`, `data/` and `supabase/` appear at the root).
3. Visit [Streamlit Community Cloud](https://share.streamlit.io/) and create a new app connected to the repository.
4. Set the main file path to `app.py`.
5. Add the Supabase secrets from the previous section in the app's Secrets settings.
6. Deploy. On the first start, create your profile; then use the same account on mobile and laptop to access the same cloud records.

## Database tables

`profiles`, `exercises`, `workout_sessions`, `workout_exercises`, `workout_sets`, and `body_weight_entries` are created by `supabase/schema.sql`. All private tables have Row Level Security enabled and explicit owner policies. System exercise entries are shared read-only records; custom exercises are owned by the creator.

## Testing

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py services/*.py components/*.py
```

## Notes and current scope

- The exercise demo control opens a YouTube search for the exercise rather than claiming a specific video has been verified; exercise instructions are also included in the app.
- Workout streaks count consecutive dates with a saved **completed** session; rest days are not auto-marked as missed.
- Body-weight graphs display entered measurements only. No data is fabricated for dates without an entry.
- This project does not ship with a hosted Supabase project or your account credentials. You must create/configure your own project and keep its secrets private.
