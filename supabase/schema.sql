-- RepTrack: run this whole file in the Supabase SQL Editor before deploying.
-- All user-owned tables use Row Level Security. Never put the service-role key in source code.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique,
  email text not null unique,
  full_name text not null,
  created_at timestamptz not null default now(),
  body_weight_goal_kg numeric(6,2),
  weekly_goal integer not null default 4 check (weekly_goal between 0 and 14),
  preferred_unit text not null default 'kg' check (preferred_unit in ('kg','lb')),
  theme text not null default 'dark' check (theme in ('dark','light'))
);

create table if not exists public.exercises (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id) on delete cascade,
  name text not null,
  muscle_group text not null,
  target_muscles text not null default '',
  equipment text not null default '',
  difficulty text not null default 'Beginner',
  instructions text not null default '',
  image_url text not null default '',
  video_url text not null default '',
  is_custom boolean not null default false,
  created_at timestamptz not null default now(),
  constraint exercise_owner_rules check ((owner_id is null and is_custom = false) or owner_id is not null)
);
create index if not exists exercises_owner_group_idx on public.exercises(owner_id, muscle_group);

create table if not exists public.workout_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  workout_date date not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  status text not null default 'active' check (status in ('active','completed','abandoned')),
  muscle_groups text not null default '',
  notes text not null default '',
  duration_minutes integer check (duration_minutes is null or duration_minutes >= 0),
  created_at timestamptz not null default now()
);
create index if not exists workout_sessions_user_date_idx on public.workout_sessions(user_id, workout_date desc);
create index if not exists workout_sessions_user_status_idx on public.workout_sessions(user_id, status);

create table if not exists public.workout_exercises (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  workout_id uuid not null references public.workout_sessions(id) on delete cascade,
  exercise_id uuid references public.exercises(id) on delete set null,
  exercise_name text not null,
  sort_order integer not null default 0,
  notes text not null default '',
  created_at timestamptz not null default now()
);
create index if not exists workout_exercises_workout_idx on public.workout_exercises(user_id, workout_id, sort_order);

create table if not exists public.workout_sets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  workout_id uuid not null references public.workout_sessions(id) on delete cascade,
  workout_exercise_id uuid not null references public.workout_exercises(id) on delete cascade,
  set_number integer not null check (set_number > 0),
  weight_kg numeric(7,3) not null default 0 check (weight_kg >= 0),
  reps integer not null default 0 check (reps >= 0),
  rpe numeric(3,1) check (rpe is null or (rpe between 1 and 10)),
  completed boolean not null default true,
  created_at timestamptz not null default now(),
  unique (workout_exercise_id, set_number)
);
create index if not exists workout_sets_workout_idx on public.workout_sets(user_id, workout_id);

create table if not exists public.body_weight_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  entry_date date not null,
  weight_kg numeric(6,2) not null check (weight_kg > 0 and weight_kg < 500),
  notes text not null default '',
  created_at timestamptz not null default now(),
  unique (user_id, entry_date)
);
create index if not exists body_weight_user_date_idx on public.body_weight_entries(user_id, entry_date desc);

alter table public.profiles enable row level security;
alter table public.exercises enable row level security;
alter table public.workout_sessions enable row level security;
alter table public.workout_exercises enable row level security;
alter table public.workout_sets enable row level security;
alter table public.body_weight_entries enable row level security;

-- Profiles
 drop policy if exists "profile select own" on public.profiles;
 create policy "profile select own" on public.profiles for select to authenticated using (id = auth.uid());
 drop policy if exists "profile insert own" on public.profiles;
 create policy "profile insert own" on public.profiles for insert to authenticated with check (id = auth.uid());
 drop policy if exists "profile update own" on public.profiles;
 create policy "profile update own" on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
 drop policy if exists "profile delete own" on public.profiles;
 create policy "profile delete own" on public.profiles for delete to authenticated using (id = auth.uid());

-- Shared exercise library is read-only; users can CRUD only their own custom exercises.
 drop policy if exists "exercise read global or own" on public.exercises;
 create policy "exercise read global or own" on public.exercises for select to authenticated using (owner_id is null or owner_id = auth.uid());
 drop policy if exists "exercise insert own" on public.exercises;
 create policy "exercise insert own" on public.exercises for insert to authenticated with check (owner_id = auth.uid() and is_custom = true);
 drop policy if exists "exercise update own" on public.exercises;
 create policy "exercise update own" on public.exercises for update to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());
 drop policy if exists "exercise delete own" on public.exercises;
 create policy "exercise delete own" on public.exercises for delete to authenticated using (owner_id = auth.uid());

-- User-owned records: every operation is scoped to auth.uid().
 drop policy if exists "workout_sessions select own" on public.workout_sessions;
 create policy "workout_sessions select own" on public.workout_sessions for select to authenticated using (user_id = auth.uid());
 drop policy if exists "workout_sessions insert own" on public.workout_sessions;
 create policy "workout_sessions insert own" on public.workout_sessions for insert to authenticated with check (user_id = auth.uid());
 drop policy if exists "workout_sessions update own" on public.workout_sessions;
 create policy "workout_sessions update own" on public.workout_sessions for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
 drop policy if exists "workout_sessions delete own" on public.workout_sessions;
 create policy "workout_sessions delete own" on public.workout_sessions for delete to authenticated using (user_id = auth.uid());
 drop policy if exists "workout_exercises select own" on public.workout_exercises;
 create policy "workout_exercises select own" on public.workout_exercises for select to authenticated using (user_id = auth.uid());
 drop policy if exists "workout_exercises insert own" on public.workout_exercises;
 create policy "workout_exercises insert own" on public.workout_exercises for insert to authenticated with check (user_id = auth.uid());
 drop policy if exists "workout_exercises update own" on public.workout_exercises;
 create policy "workout_exercises update own" on public.workout_exercises for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
 drop policy if exists "workout_exercises delete own" on public.workout_exercises;
 create policy "workout_exercises delete own" on public.workout_exercises for delete to authenticated using (user_id = auth.uid());
 drop policy if exists "workout_sets select own" on public.workout_sets;
 create policy "workout_sets select own" on public.workout_sets for select to authenticated using (user_id = auth.uid());
 drop policy if exists "workout_sets insert own" on public.workout_sets;
 create policy "workout_sets insert own" on public.workout_sets for insert to authenticated with check (user_id = auth.uid());
 drop policy if exists "workout_sets update own" on public.workout_sets;
 create policy "workout_sets update own" on public.workout_sets for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
 drop policy if exists "workout_sets delete own" on public.workout_sets;
 create policy "workout_sets delete own" on public.workout_sets for delete to authenticated using (user_id = auth.uid());
 drop policy if exists "body_weight_entries select own" on public.body_weight_entries;
 create policy "body_weight_entries select own" on public.body_weight_entries for select to authenticated using (user_id = auth.uid());
 drop policy if exists "body_weight_entries insert own" on public.body_weight_entries;
 create policy "body_weight_entries insert own" on public.body_weight_entries for insert to authenticated with check (user_id = auth.uid());
 drop policy if exists "body_weight_entries update own" on public.body_weight_entries;
 create policy "body_weight_entries update own" on public.body_weight_entries for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
 drop policy if exists "body_weight_entries delete own" on public.body_weight_entries;
 create policy "body_weight_entries delete own" on public.body_weight_entries for delete to authenticated using (user_id = auth.uid());

-- Shared library items. Execute this file as the database owner in the Supabase SQL Editor.
insert into public.exercises
(id, owner_id, name, muscle_group, target_muscles, equipment, difficulty, instructions, image_url, video_url, is_custom, created_at)
values
  ('72e92b3c-7185-5b4b-b725-139ac71a8ce0', NULL, 'Lat Pulldown', 'Back', 'Lats, upper back', 'Cable machine', 'Beginner', 'Sit tall and secure your thighs under the pads. Grip the bar slightly wider than shoulder-width. Pull the bar toward your upper chest by driving your elbows down; avoid swinging or pulling behind your neck. Return slowly with control.', '', 'https://www.youtube.com/results?search_query=Lat+Pulldown+proper+form+tutorial', FALSE, now()),
  ('466596f2-cd13-5d83-92e1-9f44a0d533c3', NULL, 'Seated Cable Row', 'Back', 'Mid-back, lats, rear delts', 'Cable row machine', 'Beginner', 'Sit upright with a neutral spine and soft knees. Pull the handle toward your lower ribs while drawing your shoulder blades back. Keep your torso steady and extend your arms slowly without rounding your back.', '', 'https://www.youtube.com/results?search_query=Seated+Cable+Row+proper+form+tutorial', FALSE, now()),
  ('ee29b822-663b-531f-8da3-ad8a4b1dce9b', NULL, 'Single-Arm Dumbbell Row', 'Back', 'Lats, rhomboids', 'Dumbbell, bench', 'Beginner', 'Support one hand and knee on a bench. Keep your back flat and pull the dumbbell toward your hip, keeping the elbow close to your body. Lower under control, then switch sides.', '', 'https://www.youtube.com/results?search_query=Single+Arm+Dumbbell+Row+proper+form+tutorial', FALSE, now()),
  ('f05168a5-1d41-5af1-a9de-726b9507395c', NULL, 'Close-Grip Lat Pulldown', 'Back', 'Lats, biceps', 'Cable machine, close-grip handle', 'Beginner', 'Sit tall and hold the close-grip attachment. Pull toward the upper chest with elbows traveling down and slightly forward. Avoid rocking backward or shrugging, then return with control.', '', 'https://www.youtube.com/results?search_query=Close+Grip+Lat+Pulldown+proper+form', FALSE, now()),
  ('6d2ce252-5081-5442-a481-d3b70daa3006', NULL, 'Barbell Bent-Over Row', 'Back', 'Mid-back, lats, spinal erectors', 'Barbell', 'Intermediate', 'Hinge at the hips with knees slightly bent and spine neutral. Brace your trunk and pull the bar toward your lower ribs. Keep the bar close and avoid jerking your torso; lower with control.', '', 'https://www.youtube.com/results?search_query=Barbell+Bent+Over+Row+proper+form', FALSE, now()),
  ('51d9f57d-21a8-5622-acd8-b6999b3f768d', NULL, 'T-Bar Row', 'Back', 'Mid-back, lats, rear delts', 'T-bar row machine or landmine', 'Intermediate', 'Stand with feet stable and brace your core. Keep your chest supported if the machine provides a pad. Pull the handles toward your torso by driving elbows back, pause briefly, then lower slowly without rounding your back.', '', 'https://www.youtube.com/results?search_query=T+Bar+Row+proper+form+tutorial', FALSE, now()),
  ('933c852a-4f4d-576c-821f-c0f1018053b3', NULL, 'Chest-Supported Row', 'Back', 'Rhomboids, lats, rear delts', 'Incline bench, dumbbells', 'Beginner', 'Lie chest-down on an incline bench with feet firmly planted. Pull the weights toward your ribs without lifting your chest off the pad. Lower slowly and keep your neck neutral.', '', 'https://www.youtube.com/results?search_query=Chest+Supported+Row+proper+form', FALSE, now()),
  ('991d9a5c-c991-5a3b-93c0-6459a3b84aab', NULL, 'Straight-Arm Pulldown', 'Back', 'Lats, teres major', 'Cable machine, straight bar or rope', 'Beginner', 'Stand facing the cable with a slight hip hinge and soft elbows. Sweep the bar down toward your thighs by engaging your lats. Keep your torso steady and return slowly.', '', 'https://www.youtube.com/results?search_query=Straight+Arm+Pulldown+proper+form', FALSE, now()),
  ('14dbcc0b-4a03-53cb-8713-36f9cb7ab86c', NULL, 'Assisted Pull-Up', 'Back', 'Lats, upper back, biceps', 'Assisted pull-up machine', 'Beginner', 'Set assistance to a manageable level and grip the handles securely. Start with shoulders controlled, pull your chest upward, and lower slowly to a comfortable full stretch. Avoid kicking or swinging.', '', 'https://www.youtube.com/results?search_query=Assisted+Pull+Up+proper+form', FALSE, now()),
  ('64289384-89cb-5978-a9a0-3ff19cfb1e6f', NULL, 'Pull-Up', 'Back', 'Lats, upper back, biceps', 'Pull-up bar', 'Advanced', 'Use a secure overhand grip and brace your body. Pull until your chin clears the bar without craning your neck. Lower under control and avoid excessive swinging. Use assistance if needed.', '', 'https://www.youtube.com/results?search_query=Pull+Up+proper+form+tutorial', FALSE, now()),
  ('6f390804-ab87-5694-a5c2-34ee0c5052d6', NULL, 'Barbell Curl', 'Biceps', 'Biceps brachii, brachialis', 'Barbell or EZ bar', 'Beginner', 'Stand tall with elbows near your sides. Curl the bar without leaning backward or swinging your shoulders. Squeeze near the top, then lower slowly through a comfortable range.', '', 'https://www.youtube.com/results?search_query=Barbell+Biceps+Curl+proper+form', FALSE, now()),
  ('e256bef2-2165-54f6-8956-91eec6cb855b', NULL, 'EZ-Bar Curl', 'Biceps', 'Biceps, brachialis', 'EZ curl bar', 'Beginner', 'Hold the angled grips with wrists comfortable. Keep your elbows close to your torso and curl smoothly. Avoid using momentum; lower until your arms are nearly straight without forcing the elbows.', '', 'https://www.youtube.com/results?search_query=EZ+Bar+Curl+proper+form', FALSE, now()),
  ('84dedc16-bb0d-51d5-809d-870d787eabcd', NULL, 'Alternating Dumbbell Curl', 'Biceps', 'Biceps brachii', 'Dumbbells', 'Beginner', 'Stand or sit tall with a dumbbell in each hand. Curl one weight while keeping the upper arm still. Rotate the palm upward naturally, lower with control, then alternate sides.', '', 'https://www.youtube.com/results?search_query=Alternating+Dumbbell+Curl+proper+form', FALSE, now()),
  ('cb434999-ca32-53eb-a226-ea74d60c56f8', NULL, 'Incline Dumbbell Curl', 'Biceps', 'Biceps brachii', 'Incline bench, dumbbells', 'Intermediate', 'Set the bench to a moderate incline and let your arms hang naturally. Curl without moving the shoulders forward, pause near the top, then lower slowly. Use a lighter load if you cannot control the lowering phase.', '', 'https://www.youtube.com/results?search_query=Incline+Dumbbell+Curl+proper+form', FALSE, now()),
  ('97d513a2-62e7-597d-9430-0815897f1ffe', NULL, 'Hammer Curl', 'Biceps', 'Brachialis, brachioradialis, biceps', 'Dumbbells', 'Beginner', 'Hold dumbbells with palms facing each other. Keep wrists neutral and elbows near your sides as you curl. Avoid rocking and lower in a controlled manner.', '', 'https://www.youtube.com/results?search_query=Hammer+Curl+proper+form', FALSE, now()),
  ('5463f294-0da8-5514-a2ee-01c68b6a8365', NULL, 'Preacher Curl', 'Biceps', 'Biceps brachii', 'Preacher bench, EZ bar or dumbbells', 'Intermediate', 'Position your upper arms on the preacher pad and keep them supported. Curl without lifting your elbows from the pad. Lower slowly and avoid forcing the elbow joint into a hard lockout.', '', 'https://www.youtube.com/results?search_query=Preacher+Curl+proper+form', FALSE, now()),
  ('483629f5-b841-59e9-a70a-fc6772ae0ae0', NULL, 'Cable Biceps Curl', 'Biceps', 'Biceps brachii', 'Cable machine, straight bar', 'Beginner', 'Stand stable with elbows tucked and cable tension maintained. Curl the handle toward your shoulders without swaying. Lower slowly while keeping your wrists comfortable.', '', 'https://www.youtube.com/results?search_query=Cable+Biceps+Curl+proper+form', FALSE, now()),
  ('bd84695e-007e-5b4a-b43c-24629094dc0c', NULL, 'Concentration Curl', 'Biceps', 'Biceps brachii', 'Dumbbell, bench', 'Beginner', 'Sit with legs apart and brace your upper arm against the inside of your thigh. Curl the dumbbell without swinging, squeeze gently, then lower with control. Repeat for the other arm.', '', 'https://www.youtube.com/results?search_query=Concentration+Curl+proper+form', FALSE, now()),
  ('71ba23a2-908b-5cc9-94a4-193a85f76278', NULL, 'Barbell Bench Press', 'Chest', 'Pectorals, triceps, front delts', 'Bench, barbell, rack', 'Intermediate', 'Set your feet firmly and retract your shoulder blades against the bench. Unrack with control, lower the bar toward mid-chest, and press upward without bouncing. Use safeties or a spotter for heavy sets.', '', 'https://www.youtube.com/results?search_query=Barbell+Bench+Press+proper+form', FALSE, now()),
  ('bb363cea-14b0-5c4b-a2f9-ee92db7c8acd', NULL, 'Incline Dumbbell Press', 'Chest', 'Upper chest, triceps, front delts', 'Incline bench, dumbbells', 'Beginner', 'Set a modest incline and keep your shoulder blades stable. Lower dumbbells toward the upper chest with elbows at a comfortable angle, then press up without clanking the weights together.', '', 'https://www.youtube.com/results?search_query=Incline+Dumbbell+Press+proper+form', FALSE, now()),
  ('72e2a475-c80f-523e-b9ab-7494a132ca46', NULL, 'Machine Chest Press', 'Chest', 'Pectorals, triceps', 'Chest press machine', 'Beginner', 'Adjust the seat so the handles align around mid-chest. Keep your back supported and wrists stacked over elbows. Press smoothly and return without letting the stack slam.', '', 'https://www.youtube.com/results?search_query=Machine+Chest+Press+proper+form', FALSE, now()),
  ('e342b183-932f-51cf-8884-37e6df186789', NULL, 'Cable Fly', 'Chest', 'Pectorals', 'Cable machine', 'Intermediate', 'Set the pulleys at a comfortable height and stand in a split stance. Keep a soft bend in the elbows and bring your arms together in an arc. Avoid overstretching the shoulders and return slowly.', '', 'https://www.youtube.com/results?search_query=Cable+Chest+Fly+proper+form', FALSE, now()),
  ('033347df-23e5-5f8f-bfc9-3c191bbd8b8c', NULL, 'Push-Up', 'Chest', 'Pectorals, triceps, core', 'Bodyweight', 'Beginner', 'Keep your body in a straight line from head to heels. Lower your chest by bending your elbows at a comfortable angle, then push the floor away. Elevate your hands if needed to maintain good form.', '', 'https://www.youtube.com/results?search_query=Push+Up+proper+form', FALSE, now()),
  ('57082621-76a0-545c-ad67-b912aefe974b', NULL, 'Pec Deck Fly', 'Chest', 'Pectorals', 'Pec deck machine', 'Beginner', 'Adjust the seat so your elbows or hands align comfortably with chest height. Bring the pads together without shrugging, pause, then open slowly only as far as your shoulders tolerate.', '', 'https://www.youtube.com/results?search_query=Pec+Deck+Fly+proper+form', FALSE, now()),
  ('bb65eaa0-ce1e-5066-92fd-4fd1c62f6156', NULL, 'Dumbbell Shoulder Press', 'Shoulders', 'Deltoids, triceps', 'Dumbbells, bench', 'Intermediate', 'Sit tall with dumbbells near shoulder height. Brace your core and press overhead along a comfortable path. Avoid excessive back arching; lower slowly and stop if you feel sharp pain.', '', 'https://www.youtube.com/results?search_query=Dumbbell+Shoulder+Press+proper+form', FALSE, now()),
  ('e5294796-42f3-5deb-a747-746bdd25fd34', NULL, 'Lateral Raise', 'Shoulders', 'Side deltoids', 'Dumbbells', 'Beginner', 'Stand tall with soft elbows. Raise the dumbbells out to the sides to a comfortable height, keeping shoulders away from your ears. Lower slowly and use a load that avoids swinging.', '', 'https://www.youtube.com/results?search_query=Dumbbell+Lateral+Raise+proper+form', FALSE, now()),
  ('d79ab28b-284d-5785-8f46-90b688d502c5', NULL, 'Rear Delt Fly', 'Shoulders', 'Rear deltoids, upper back', 'Dumbbells or reverse pec deck', 'Beginner', 'Hinge slightly at the hips or use a reverse pec deck. Sweep your arms outward with soft elbows and avoid shrugging. Return slowly while maintaining a stable torso.', '', 'https://www.youtube.com/results?search_query=Rear+Delt+Fly+proper+form', FALSE, now()),
  ('e602f042-7897-50e1-b2b1-c7251f8893f4', NULL, 'Face Pull', 'Shoulders', 'Rear delts, external rotators, upper back', 'Cable machine, rope', 'Beginner', 'Set the rope around face height. Pull toward your forehead with elbows out and thumbs moving back, keeping ribs down. Use moderate weight and avoid leaning your body backward.', '', 'https://www.youtube.com/results?search_query=Cable+Face+Pull+proper+form', FALSE, now()),
  ('85ed1cee-53af-573a-8fd0-d38ea453a065', NULL, 'Machine Shoulder Press', 'Shoulders', 'Deltoids, triceps', 'Shoulder press machine', 'Beginner', 'Adjust the seat so handles start around shoulder level. Keep your back against the pad, press smoothly overhead, and return without bouncing or locking forcefully.', '', 'https://www.youtube.com/results?search_query=Machine+Shoulder+Press+proper+form', FALSE, now()),
  ('a8877175-398c-56db-aca5-4b59c36b03cd', NULL, 'Rope Triceps Pushdown', 'Triceps', 'Triceps', 'Cable machine, rope', 'Beginner', 'Keep elbows close to your sides and shoulders relaxed. Extend your arms by moving at the elbows, separate the rope slightly at the bottom, then return slowly without letting elbows drift forward.', '', 'https://www.youtube.com/results?search_query=Rope+Triceps+Pushdown+proper+form', FALSE, now()),
  ('0b52db62-1f50-5aeb-8e7e-ed0d3ed3c6fe', NULL, 'Overhead Triceps Extension', 'Triceps', 'Triceps long head', 'Dumbbell or cable', 'Beginner', 'Keep ribs down and elbows pointing forward comfortably. Bend the elbows to lower the weight behind your head, then extend smoothly. Choose a load that does not strain your shoulders or elbows.', '', 'https://www.youtube.com/results?search_query=Overhead+Triceps+Extension+proper+form', FALSE, now()),
  ('d87b9dbc-8e23-5472-aef3-4259d8f80c5c', NULL, 'Cable Triceps Kickback', 'Triceps', 'Triceps', 'Cable or dumbbell', 'Beginner', 'Hinge slightly with upper arm held close to your side. Straighten the elbow without swinging the shoulder, pause briefly, and return with control.', '', 'https://www.youtube.com/results?search_query=Triceps+Kickback+proper+form', FALSE, now()),
  ('9a7245d7-d50c-5d84-a376-f5c178b1b46f', NULL, 'EZ-Bar Skull Crusher', 'Triceps', 'Triceps', 'EZ bar, bench', 'Intermediate', 'Lie on a bench and hold the bar above your shoulders. Bend your elbows to lower the bar toward a comfortable point near your forehead or behind the head, then extend. Use a spotter and controllable load.', '', 'https://www.youtube.com/results?search_query=EZ+Bar+Skull+Crusher+proper+form', FALSE, now()),
  ('d829bec0-cfba-5dcf-9196-e45c6bad2840', NULL, 'Dumbbell Wrist Curl', 'Forearms', 'Wrist flexors', 'Dumbbells, bench', 'Beginner', 'Rest your forearms on your thighs or a bench with palms upward. Let wrists extend slightly, then curl the hands upward. Keep the movement controlled and use a light weight.', '', 'https://www.youtube.com/results?search_query=Dumbbell+Wrist+Curl+proper+form', FALSE, now()),
  ('5628035e-a5c9-557c-8057-fb9ba2890c02', NULL, 'Reverse Curl', 'Forearms', 'Brachioradialis, forearms, biceps', 'EZ bar or dumbbells', 'Beginner', 'Use an overhand grip and keep wrists neutral. Curl by bending the elbows while keeping upper arms steady. Avoid wrist discomfort or swinging the body.', '', 'https://www.youtube.com/results?search_query=Reverse+Curl+proper+form', FALSE, now()),
  ('25fb1d81-2d05-5bd4-b360-ffc90100e58a', NULL, 'Barbell Back Squat', 'Legs', 'Quadriceps, glutes, trunk', 'Barbell, squat rack', 'Advanced', 'Set the bar securely across your upper back and brace your trunk. Sit down between your hips while keeping feet planted and knees tracking comfortably over toes. Use a depth you can control and set safety arms when available.', '', 'https://www.youtube.com/results?search_query=Barbell+Back+Squat+proper+form', FALSE, now()),
  ('87436431-a5fd-58fa-b3c3-ab595f5d3f9a', NULL, 'Leg Press', 'Legs', 'Quadriceps, glutes', 'Leg press machine', 'Beginner', 'Set your feet about shoulder-width on the platform. Lower the sled only as far as your hips stay supported, then press through your feet without forcefully locking your knees.', '', 'https://www.youtube.com/results?search_query=Leg+Press+proper+form', FALSE, now()),
  ('b767e18f-827d-5d19-906a-7431d5f5d360', NULL, 'Romanian Deadlift', 'Legs', 'Hamstrings, glutes, spinal erectors', 'Barbell or dumbbells', 'Intermediate', 'Hold the weights close to your legs. Push your hips backward with knees slightly bent and a neutral spine, stopping when you feel a hamstring stretch. Drive hips forward to stand without leaning back.', '', 'https://www.youtube.com/results?search_query=Romanian+Deadlift+proper+form', FALSE, now()),
  ('497ebcb5-be0f-543d-b6a9-4d8c70429d1f', NULL, 'Leg Extension', 'Quadriceps', 'Quadriceps', 'Leg extension machine', 'Beginner', 'Align the machine pivot with your knee and position the pad above your ankles. Extend your knees smoothly, pause, and lower under control. Use a pain-free range.', '', 'https://www.youtube.com/results?search_query=Leg+Extension+proper+form', FALSE, now()),
  ('02f079bf-ed73-538b-95ad-cb1b54bebcb0', NULL, 'Seated Leg Curl', 'Hamstrings', 'Hamstrings', 'Seated leg curl machine', 'Beginner', 'Adjust the machine so the knee aligns with the pivot and pads are secure. Curl your heels down and back, pause, then return slowly without letting the stack slam.', '', 'https://www.youtube.com/results?search_query=Seated+Leg+Curl+proper+form', FALSE, now()),
  ('32d6379f-8f81-5c69-9461-58ce506b50a0', NULL, 'Walking Lunge', 'Glutes', 'Glutes, quadriceps', 'Bodyweight or dumbbells', 'Intermediate', 'Take a controlled step forward and lower until both knees bend comfortably. Keep the front foot stable and torso upright, then push through the front foot to step through. Use bodyweight until balance is solid.', '', 'https://www.youtube.com/results?search_query=Walking+Lunge+proper+form', FALSE, now()),
  ('3cf4fb7f-11e6-57b5-87ea-542721724a24', NULL, 'Standing Calf Raise', 'Calves', 'Gastrocnemius, soleus', 'Calf raise machine or step', 'Beginner', 'Stand with the balls of your feet supported and heels free if using a step. Rise onto your toes, pause, then lower through a comfortable stretch. Avoid bouncing.', '', 'https://www.youtube.com/results?search_query=Standing+Calf+Raise+proper+form', FALSE, now()),
  ('e8b0c526-fc8b-5c68-92d6-ddd5a6816327', NULL, 'Seated Calf Raise', 'Calves', 'Soleus, calves', 'Seated calf raise machine', 'Beginner', 'Place the balls of your feet on the platform and the pad across your lower thighs. Lower your heels comfortably, then raise them as high as you can control. Pause briefly at both ends.', '', 'https://www.youtube.com/results?search_query=Seated+Calf+Raise+proper+form', FALSE, now()),
  ('41e9c757-b9ab-589d-be1f-1b4bef6227e6', NULL, 'Cable Crunch', 'Abs / Core', 'Rectus abdominis', 'Cable machine, rope', 'Beginner', 'Kneel facing the cable with rope near your head. Curl your ribs toward your pelvis by flexing the trunk, not by pulling only with your arms. Return slowly without letting the stack yank you up.', '', 'https://www.youtube.com/results?search_query=Cable+Crunch+proper+form', FALSE, now()),
  ('31e205fd-ffad-5d86-8cd2-8eb764d268f5', NULL, 'Plank', 'Abs / Core', 'Deep core, abdominals', 'Bodyweight', 'Beginner', 'Place elbows under shoulders and extend your legs. Keep a straight line from head to heels, brace your abdomen, and breathe steadily. End the set when your hips sag or rise.', '', 'https://www.youtube.com/results?search_query=Forearm+Plank+proper+form', FALSE, now()),
  ('427c957c-c476-578c-aca2-23a1f8dfe29e', NULL, 'Hanging Knee Raise', 'Abs / Core', 'Abdominals, hip flexors', 'Pull-up bar or captain''s chair', 'Intermediate', 'Hang securely or use a captain''s chair. Brace your trunk and bring knees upward without excessive swinging. Lower slowly and stop if your grip or shoulders become uncomfortable.', '', 'https://www.youtube.com/results?search_query=Hanging+Knee+Raise+proper+form', FALSE, now()),
  ('50e95ac1-5501-5aa0-a841-3acf9b949f4d', NULL, 'Treadmill Walk', 'Cardio', 'Cardiovascular system, legs', 'Treadmill', 'Beginner', 'Choose a comfortable speed and incline. Stand tall, use a natural stride, and increase intensity gradually. Use the safety clip where available and stop if you feel unwell.', '', 'https://www.youtube.com/results?search_query=Treadmill+Walking+workout+technique', FALSE, now()),
  ('1103f850-7069-52cd-9ba3-bc102453395c', NULL, 'Stationary Bike', 'Cardio', 'Cardiovascular system, legs', 'Stationary bike', 'Beginner', 'Adjust the seat so your knee remains slightly bent at the bottom of the pedal stroke. Start with an easy pace, maintain steady breathing, and increase resistance gradually.', '', 'https://www.youtube.com/results?search_query=Stationary+Bike+setup+proper+form', FALSE, now()),
  ('cf5b0fe9-cb23-54cf-ba8e-369d38a7482e', NULL, 'Burpee', 'Cardio', 'Full body, cardiovascular system', 'Bodyweight', 'Intermediate', 'Move between a squat, plank, and standing position at a pace you can control. Step your feet back instead of jumping if needed. Prioritize a stable trunk and comfortable wrist and shoulder positions.', '', 'https://www.youtube.com/results?search_query=Burpee+exercise+proper+form', FALSE, now()),
  ('288f0120-8d7a-5659-bf88-7a856e0c7e93', NULL, 'Hip Thrust', 'Glutes', 'Glutes, hamstrings', 'Bench, barbell or dumbbell', 'Intermediate', 'Support your upper back on a stable bench with feet planted. Drive through the feet and extend your hips until your torso is roughly level, avoiding over-arching the lower back. Lower with control.', '', 'https://www.youtube.com/results?search_query=Barbell+Hip+Thrust+proper+form', FALSE, now()),
  ('0b9abd35-c3a7-56bb-b97b-f33e0073f3c7', NULL, 'Dumbbell Goblet Squat', 'Quadriceps', 'Quadriceps, glutes, trunk', 'Dumbbell or kettlebell', 'Beginner', 'Hold a dumbbell close to your chest. Sit down between your hips while keeping your chest stable and feet planted. Stand by pushing through the floor; choose a comfortable depth.', '', 'https://www.youtube.com/results?search_query=Goblet+Squat+proper+form', FALSE, now()),
  ('7cd52a41-02b0-54f8-b00f-c834e7398b04', NULL, 'Dumbbell Shrug', 'Shoulders', 'Upper trapezius', 'Dumbbells', 'Beginner', 'Stand tall with weights at your sides. Raise your shoulders straight upward without rolling them, pause briefly, then lower slowly. Keep your neck relaxed and avoid jerking.', '', 'https://www.youtube.com/results?search_query=Dumbbell+Shrug+proper+form', FALSE, now())
on conflict (id) do nothing;

-- Optional: show only generic username-lookup responses from the Streamlit server.
-- Username-to-email resolution is done server-side only when SUPABASE_SERVICE_ROLE_KEY is set in Streamlit Secrets.
