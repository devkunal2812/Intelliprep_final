# Database Documentation — IntelliPrep Main Website

This document defines the production database schema, security model, and automation logic for the **Main Website**.  
The system allows for independent operation from the `test_website` utilizing a shared Supabase instance with dedicated `main_*` tables.

---

## 1. Architecture Overview

- **Platform**: Supabase (PostgreSQL 15+)
- **Authentication**: Managed via **Supabase Auth** (`auth.users`)
- **Data Isolation**: All application tables are prefixed with `main_`
- **Security**: Row Level Security (RLS) is strictly enforced on all tables
- **Concurrency**: High-concurrency design for adaptive testing and ML data collection

---

## 2. Authentication & User Identity

### `auth.users` (Supabase Managed)
Core identity table managed internally by Supabase.
- **ID**: UUID (Primary Key)
- **Role**: Secure credentials handling (passwords, JWTs)
- **Modifiable**: No (Managed by specific Supabase Auth API)

### `main_users`
Application-specific user profile linking to Supabase Auth.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `auth_user_id` | `uuid` | **PK**, FK -> `auth.users(id)` | 1:1 link to Supabase Identity |
| `created_at` | `timestamptz` | DEFAULT `now()` | Account creation timestamp |
| `is_active` | `boolean` | DEFAULT `true` | Soft-delete / Ban flag |

**Key Behavior:**
- Rows are automatically created via `handle_new_user` trigger upon signup.
- Primary Key is identical to `auth.users.id` for simplified joining.
- **RLS**: Users can only view their own profile.

---

## 3. Question Bank & Content

### `main_questions`
Static repository of all questions available for calibration and adaptive tests.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `bigserial` | **PK** | Unique Question ID |
| `question_text` | `text` | NOT NULL | The core question body |
| `option_a` | `text` | NOT NULL | Option A text |
| `option_b` | `text` | NOT NULL | Option B text |
| `option_c` | `text` | NOT NULL | Option C text |
| `option_d` | `text` | NOT NULL | Option D text |
| `correct_option` | `char(1)` | `'A','B','C','D'` | The correct answer key |
| `domain` | `text` | NOT NULL | Broad subject area (e.g., 'Verbal') |
| `topic` | `text` | NOT NULL | Specific topic (e.g., 'Grammar') |
| `difficulty` | `text` | `'easy','medium','hard'` | Editorial difficulty rating |
| `is_active` | `boolean` | DEFAULT `true` | Controls question visibility |

**Indexes:**
- `(domain, topic)`: For rapid filtering during test generation.
- `(difficulty)`: For adaptive selection algorithms.

---

## 4. Test Sessions

### `main_tests`
Represents a single test session/attempt by a user.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | **PK**, DEFAULT `gen_random_uuid()` | Unique Session ID |
| `auth_user_id` | `uuid` | FK -> `main_users` | The test taker |
| `test_type` | `text` | `'calibration', 'adaptive'` | Type of assessment |
| `status` | `text` | `'IN_PROGRESS', 'COMPLETED', 'ABANDONED'` | Lifecycle state |
| `question_ids` | `bigint[]` | NOT NULL | Frozen array of Question IDs defined at start |
| `start_time` | `timestamptz` | DEFAULT `now()` | Session start |
| `end_time` | `timestamptz` | NULLABLE | Session completion time |

**Key Behavior:**
- `question_ids` stores the fixed sequence of questions to ensure reproducibility.
- **RLS**: Users can only create and view their own tests.

---

## 5. Behavioral Data (ML Dataset)

### `main_attempts`
Granular, per-question interaction data. This is the primary dataset for ML training.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `bigserial` | **PK** | Unique Attempt ID |
| `test_id` | `uuid` | FK -> `main_tests` | Parent Test Session |
| `question_id` | `bigint` | FK -> `main_questions` | The Question attempted |
| `started_at` | `timestamptz` | NOT NULL | Time question was displayed |
| `submitted_at` | `timestamptz` | NULLABLE | Time answer was submitted |
| `selected_option` | `char(1)` | `'A','B','C','D'` | User's choice |
| `is_correct` | `boolean` | NULLABLE | Computed correctness |
| `time_taken_sec` | `integer` | `>= 0` | Time spent on question |
| `attempt_number` | `integer` | NOT NULL | Order within the test (1-based) |

**Constraints:**
- `UNIQUE (test_id, question_id)`: Enforces strictly one attempt per question per test.
- **RLS**: Users can only manage attempts linked to their own tests.

---

## 6. User State & Adaptive Logic

### `main_user_skill`
Persisted state for adaptive algorithms to avoid expensive real-time aggregations.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `auth_user_id` | `uuid` | **PK**, FK -> `main_users` | User ID |
| `overall_accuracy` | `float` | DEFAULT `0` | Running average accuracy |
| `avg_time_sec` | `float` | DEFAULT `0` | Running average response time |
| `topic_accuracy` | `jsonb` | DEFAULT `{}` | Dictionary of accuracy per topic |
| `tests_completed` | `integer` | DEFAULT `0` | Total finished tests |
| `last_updated` | `timestamptz` | DEFAULT `now()` | Last sync timestamp |

**Usage:**
- Automatically initialized via trigger.
- Updated asynchronously or at the end of a test session.

---

## 7. Database Automation & Triggers

### User Initialization Flow
A Postgres trigger ensures that every new Supabase user has corresponding application rows immediately.

**Trigger**: `on_auth_user_created`  
**Event**: `AFTER INSERT ON auth.users`  
**Function**: `handle_new_user()`

**Logic:**
```sql
BEGIN
  -- Create Public Profile
  INSERT INTO main_users (auth_user_id) VALUES (new.id);
  
  -- Initialize Adaptive State
  INSERT INTO main_user_skill (auth_user_id) VALUES (new.id);
  
  RETURN new;
END;
```

---

## 8. Security Model (Row Level Security)

RLS is **ENABLED** on all tables. 

**Policy Summary:**

| Table | Operation | Policy Logic |
| :--- | :--- | :--- |
| `main_users` | SELECT | User can read own profile (`auth.uid() = auth_user_id`) |
| `main_users` | INSERT | **System Only** (Handled by Trigger) |
| `main_user_skill` | SELECT | User can read own skills (`auth.uid() = auth_user_id`) |
| `main_user_skill` | UPDATE | **Service Role Only** (Backend updates state) |
| `main_tests` | ALL | User manages own tests (`auth.uid() = auth_user_id`) |
| `main_attempts` | ALL | User manages attempts via parent test ownership |

---

## 9. Appendix: Questions CSV Import Format

For bulk uploading questions, ensure the CSV matches the `main_questions` schema:
`question_text`, `option_a`, `option_b`, `option_c`, `option_d`, `correct_option`, `domain`, `topic`, `difficulty`