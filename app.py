import streamlit as st
import sqlite3
import hashlib
import secrets
import joblib
from datetime import datetime

# Load trained ML model
savings_model = None

st.set_page_config(page_title="FinSight | Finance Dashboard", page_icon="💰", layout="wide")

DB = "finance_users.db"

def db():
    return sqlite3.connect(DB, check_same_thread=False)


def month_to_key(month_text):
    """Convert supported month labels to YYYY-MM for matching expense dates."""
    if not month_text:
        return None
    value = str(month_text).strip()
    for fmt in ("%Y-%m", "%B %Y", "%b %Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    return None

def init_db():
    con = db()

    # Users table
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")

    # Monthly financial information
    con.execute("""CREATE TABLE IF NOT EXISTS financial_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        salary REAL DEFAULT 0,
        other_income REAL DEFAULT 0,
        fixed_expenses REAL DEFAULT 0,
        savings REAL DEFAULT 0,
        investments REAL DEFAULT 0,
        UNIQUE(user_id, month),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    # Individual expenses
    con.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        amount REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
        # Login sessions
    con.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY,
            age INTEGER,
            dependents INTEGER,
            occupation TEXT,
            city_tier TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    con.commit()
    con.close()

def password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(name, email, password):
    con = db()
    try:
        con.execute(
            "INSERT INTO users(name,email,password) VALUES(?,?,?)",
            (name, email.strip().lower(), password_hash(password))
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()

def login_user(email, password):
    con = db()
    user = con.execute(
        "SELECT id,name,email FROM users WHERE email=? AND password=?",
        (email.strip().lower(), password_hash(password))
    ).fetchone()
    con.close()
    return user
def create_session(user_id):
    token = secrets.token_urlsafe(32)

    con = db()
    con.execute(
        "INSERT INTO sessions(token, user_id) VALUES(?, ?)",
        (token, user_id)
    )
    con.commit()
    con.close()

    return token


def get_user_from_session(token):
    if not token:
        return None

    con = db()

    user = con.execute(
        """
        SELECT users.id, users.name, users.email
        FROM users
        JOIN sessions ON users.id = sessions.user_id
        WHERE sessions.token = ?
        """,
        (token,)
    ).fetchone()

    con.close()

    return user


def delete_session(token):
    if not token:
        return

    con = db()
    con.execute(
        "DELETE FROM sessions WHERE token = ?",
        (token,)
    )
    con.commit()
    con.close()

init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

if "mode" not in st.session_state:
    st.session_state.mode = "login"

# Restore login after page refresh
session_token = st.query_params.get("session")

if not st.session_state.logged_in and session_token:
    saved_user = get_user_from_session(session_token)

    if saved_user:
        st.session_state.logged_in = True
        st.session_state.user = saved_user
st.markdown("""
<style>

/* =========================================
   FINESIGHT - GLOBAL PAGE
   ========================================= */

#MainMenu, footer, header {
    visibility: hidden;
}

.stApp {
    background:
        radial-gradient(circle at 10% 10%, #e6f5ed, transparent 30%),
        radial-gradient(circle at 90% 90%, #f8f2dd, transparent 28%),
        #f7faf8;
}


/* =========================================
   BRANDING
   ========================================= */

.brand {
    text-align: center;
    margin: 25px 0 18px;
}

.logo {
    width: 58px;
    height: 58px;
    margin: auto;
    border-radius: 16px;
    background: linear-gradient(135deg, #047857, #064e3b);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 29px;
    box-shadow: 0 10px 25px rgba(4,120,87,.20);
}

.title {
    font-size: 28px;
    font-weight: 800;
    color: #172033;
    margin-top: 10px;
}

.subtitle {
    color: #687386;
    font-size: 14px;
}


/* =========================================
   CARDS
   ========================================= */

.card {
    background: #ffffff;
    padding: 30px;
    border-radius: 22px;
    box-shadow: 0 15px 45px rgba(30,45,70,.10);
    border: 1px solid #e2e7ef;
}

.welcome {
    text-align: center;
    font-size: 23px;
    font-weight: 750;
    color: #172033;
}

.hint {
    text-align: center;
    color: #7a8495;
    font-size: 13px;
    margin: 5px 0 20px;
}

.small {
    text-align: center;
    color: #8a93a3;
    font-size: 12px;
    margin-top: 20px;
}


/* =========================================
TEXT
========================================= */

h1, h2, h3, h4, h5, h6,
p, .stMarkdown,
.stMetricLabel, .stMetricValue, .stMetricDelta {
color: #172033 !important;
}

.stMetricLabel {
color: #758095 !important;
}

/* =========================================
   TEXT INPUTS
   ========================================= */

.stTextInput label {
    color: #172033 !important;
    font-weight: 600 !important;
}

.stTextInput input {
    background: #ffffff !important;
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
    border: 1px solid #cfd7e6 !important;
    border-radius: 9px !important;
}


/* =========================================
   NUMBER INPUTS
   ========================================= */

.stNumberInput label {
    color: #172033 !important;
    font-weight: 600 !important;
}

.stNumberInput input {
    background: #ffffff !important;
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
}

.stNumberInput [data-baseweb="input"] {
    background: #ffffff !important;
    border: 1px solid #cfd7e6 !important;
    border-radius: 10px !important;
}

.stNumberInput button {
    background: #ffffff !important;
    color: #172033 !important;
    border-color: #cfd7e6 !important;
}

.stNumberInput button:hover {
    background: #ecfdf5 !important;
    color: #047857 !important;
}

/* =========================================
NORMAL BUTTONS
========================================= */

.stButton > button {
color: #172033 !important;
-webkit-text-fill-color: #172033 !important;
background-color: #ffffff !important;
border: 1px solid #cfd7e6 !important;
border-radius: 10px !important;
font-weight: 600 !important;
min-height: 42px !important;
box-shadow: 0 2px 6px rgba(30,45,70,.08) !important;
}

/* Normal button hover */
.stButton > button:hover {
color: #ffffff !important;
-webkit-text-fill-color: #ffffff !important;
background-color: #047857 !important;
border-color: #047857 !important;
}

/* =========================================
PRIMARY BUTTONS
========================================= */

.stButton > button[kind="primary"] {
color: #ffffff !important;
-webkit-text-fill-color: #ffffff !important;
background-color: #047857 !important;
border: 1px solid #047857 !important;
border-radius: 10px !important;
font-weight: 700 !important;
}

/* Primary button hover */
.stButton > button[kind="primary"]:hover {
color: #ffffff !important;
-webkit-text-fill-color: #ffffff !important;
background-color: #065f46 !important;
border-color: #065f46 !important;
}

/* =========================================
   SELECT BOX
   ========================================= */

.stSelectbox label {
    color: #172033 !important;
    font-weight: 600 !important;
}

.stSelectbox [data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #172033 !important;
    border: 1px solid #cfd7e6 !important;
    border-radius: 9px !important;
}

.stSelectbox [data-baseweb="select"] input {
    color: #172033 !important;
}


/* =========================================
   DATE INPUT - FORCE LIGHT
   ========================================= */

div[data-testid="stDateInput"] {
    color-scheme: light !important;
}

div[data-testid="stDateInput"] label {
    color: #172033 !important;
    font-weight: 600 !important;
}

div[data-testid="stDateInput"] [data-baseweb="input"] {
    background: #ffffff !important;
    border: 1px solid #cfd7e6 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

div[data-testid="stDateInput"] [data-baseweb="input"] > div {
    background: #ffffff !important;
}

div[data-testid="stDateInput"] input {
    background: #ffffff !important;
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
    color-scheme: light !important;
    border: none !important;
    box-shadow: none !important;
}

div[data-testid="stDateInput"] button {
    background: #ffffff !important;
    color: #172033 !important;
    border: none !important;
}

div[data-testid="stDateInput"] button:hover {
    background: #ecfdf5 !important;
    color: #047857 !important;
}


/* =========================================
   DATE CALENDAR POPUP
   ========================================= */

[data-baseweb="calendar"] {
    background: #ffffff !important;
    color: #172033 !important;
    color-scheme: light !important;
    border: 1px solid #d7deea !important;
    border-radius: 12px !important;
    box-shadow: 0 12px 35px rgba(30,45,70,.18) !important;
}

[data-baseweb="calendar"] * {
    color: #172033 !important;
}

[data-baseweb="calendar"] button {
    background: #ffffff !important;
    color: #172033 !important;
    border: none !important;
}

[data-baseweb="calendar"] button:hover {
    background: #ecfdf5 !important;
    color: #047857 !important;
}

[data-baseweb="calendar"] [role="gridcell"] {
    background: #ffffff !important;
    color: #172033 !important;
}

[data-baseweb="calendar"] [role="gridcell"]:hover {
    background: #ecfdf5 !important;
    color: #047857 !important;
}

[data-baseweb="calendar"] [aria-selected="true"] {
    background: #047857 !important;
    color: #ffffff !important;
}

[data-baseweb="calendar"] [aria-current="date"] {
    color: #047857 !important;
    font-weight: 700 !important;
}


/* =========================================
   FOCUS EFFECTS
   ========================================= */

.stTextInput input:focus,
.stNumberInput input:focus,
div[data-testid="stDateInput"] input:focus {
    border-color: #047857 !important;
    box-shadow: 0 0 0 1px #047857 !important;
}
/* Make date input white */
div[data-testid="stDateInput"] input {
    background-color: white !important;
    color: #172033 !important;
    border: 1px solid #d9dee8 !important;
}

div[data-testid="stDateInput"] button {
    background-color: white !important;
    color: #172033 !important;
}



/* =========================================
   EMERALD EXECUTIVE REDESIGN — VISUAL ONLY
   ========================================= */
:root {
    --fs-navy: #12372b;
    --fs-blue: #047857;
    --fs-blue-dark: #065f46;
    --fs-blue-soft: #ecfdf5;
    --fs-border: #d6e7df;
    --fs-muted: #64796f;
    --fs-emerald-deep: #064e3b;
    --fs-gold: #d4af37;
}

.stApp {
    background: #f7faf8 !important;
}

/* Keep the dashboard centered and prevent it from stretching across ultrawide screens.
   Target both current and older Streamlit container selectors for compatibility. */
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] .main .block-container {
    width: 100% !important;
    max-width: 1180px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 1.25rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: clamp(1rem, 2.5vw, 1.75rem) !important;
    padding-right: clamp(1rem, 2.5vw, 1.75rem) !important;
    box-sizing: border-box !important;
}

/* Reduce oversized vertical gaps in the overview area. */
.brand {
    margin: 4px 0 18px !important;
    padding: 14px 18px !important;
}
.card {
    padding: 18px 22px !important;
}
.welcome {
    font-size: 21px !important;
}
.hint {
    margin: 4px 0 8px !important;
}
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {
    min-width: 0;
}

.brand {
    text-align: left !important;
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 8px 0 26px !important;
    padding: 18px 22px;
    background: linear-gradient(110deg, #ffffff 0%, #f3faf6 100%);
    border: 1px solid var(--fs-border);
    border-top: 3px solid var(--fs-gold);
    border-radius: 16px;
    box-shadow: 0 4px 18px rgba(6, 78, 59, 0.06);
}

.logo {
    flex: 0 0 52px;
    width: 52px !important;
    height: 52px !important;
    margin: 0 !important;
    border-radius: 13px !important;
    background: linear-gradient(145deg, #047857, #064e3b) !important;
    box-shadow: 0 6px 14px rgba(4, 120, 87, 0.2) !important;
}

.title {
    margin: 0 !important;
    font-size: 25px !important;
    letter-spacing: -0.5px;
    color: var(--fs-navy) !important;
}

.subtitle {
    margin-top: 3px;
    color: var(--fs-muted) !important;
}

.card {
    padding: 24px !important;
    border: 1px solid var(--fs-border) !important;
    border-radius: 16px !important;
    box-shadow: 0 5px 20px rgba(16, 42, 67, 0.055) !important;
}

h1, h2, h3, h4, h5, h6,
p, .stMarkdown,
.stMetricLabel, .stMetricValue, .stMetricDelta {
    color: var(--fs-navy) !important;
}

h1, h2, h3 {
    letter-spacing: -0.35px;
}

.stMetric {
    background: #ffffff;
    border: 1px solid var(--fs-border);
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 3px 12px rgba(16, 42, 67, 0.04);
}

.stMetricLabel {
    color: var(--fs-muted) !important;
    font-weight: 600 !important;
}

.stMetricValue {
    color: var(--fs-navy) !important;
    font-weight: 750 !important;
}

.stButton > button[kind="primary"] {
    background: var(--fs-blue) !important;
    border-color: var(--fs-blue) !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 10px rgba(4, 120, 87, 0.14) !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--fs-blue-dark) !important;
    border-color: var(--fs-blue-dark) !important;
}

.stButton > button:hover {
    background: var(--fs-blue-soft) !important;
    color: var(--fs-blue-dark) !important;
    -webkit-text-fill-color: var(--fs-blue-dark) !important;
    border-color: #9acbb7 !important;
}

.stTextInput input:focus,
.stNumberInput input:focus,
div[data-testid="stDateInput"] input:focus {
    border-color: var(--fs-blue) !important;
    box-shadow: 0 0 0 1px var(--fs-blue) !important;
}

.stSelectbox [data-baseweb="select"] > div,
.stTextInput input,
.stNumberInput [data-baseweb="input"],
div[data-testid="stDateInput"] [data-baseweb="input"] {
    border-radius: 10px !important;
    border-color: var(--fs-border) !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border: 1px solid var(--fs-border);
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stAlert"] {
    border-radius: 12px !important;
}

hr {
    border-color: var(--fs-border) !important;
    margin: 1.35rem 0 !important;
}

/* Dashboard hero */
.dashboard-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    padding: 32px 36px;
    margin: 8px 0 28px;
    border-radius: 24px;
    background: linear-gradient(118deg, #073d30 0%, #075943 54%, #0b7556 100%);
    border: 1px solid rgba(212, 175, 55, .42);
    box-shadow: 0 16px 36px rgba(6, 78, 59, .16);
    position: relative;
    overflow: hidden;
}
.dashboard-hero:after {
    content: "";
    position: absolute;
    width: 210px;
    height: 210px;
    border-radius: 50%;
    right: 12%;
    top: -145px;
    background: rgba(212, 175, 55, .12);
    border: 1px solid rgba(212, 175, 55, .12);
}
.dashboard-hero-copy { position: relative; z-index: 1; }
.dashboard-eyebrow {
    color: #e4c96f;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .14em;
    margin-bottom: 9px;
}
.dashboard-heading {
    color: #ffffff;
    font-size: clamp(25px, 3vw, 35px);
    line-height: 1.15;
    font-weight: 800;
    letter-spacing: -.04em;
}
.dashboard-description {
    max-width: 690px;
    color: rgba(255, 255, 255, .78);
    font-size: 14px;
    line-height: 1.65;
    margin-top: 10px;
}
.dashboard-hero-badge {
    z-index: 1;
    flex-shrink: 0;
    padding: 10px 14px;
    border: 1px solid rgba(228, 201, 111, .42);
    border-radius: 999px;
    background: rgba(255,255,255,.10);
    color: #f5e7b0;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .08em;
}
.hero-badge-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 7px;
    border-radius: 50%;
    background: #10a36d;
    box-shadow: 0 0 0 3px rgba(16,163,109,.12);
}

/* Executive dashboard layout */
[data-testid="stMainBlockContainer"] {
    max-width: 1420px !important;
    padding-top: 1.35rem !important;
    padding-bottom: 3rem !important;
}

[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #dce9e2 !important;
    border-radius: 16px !important;
    padding: 18px 20px !important;
    min-height: 112px;
    box-shadow: 0 5px 18px rgba(6, 78, 59, 0.055) !important;
    transition: transform .18s ease, box-shadow .18s ease;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 9px 24px rgba(6, 78, 59, 0.09) !important;
}

[data-testid="stMetricLabel"] p {
    font-size: 0.82rem !important;
    font-weight: 650 !important;
    letter-spacing: .015em;
    color: #66786f !important;
}

[data-testid="stMetricValue"] {
    font-size: clamp(1.35rem, 2vw, 1.9rem) !important;
    font-weight: 750 !important;
    color: #12372b !important;
}

[data-testid="stMetricDelta"] {
    font-size: .78rem !important;
}

/* Clear section hierarchy without changing any dashboard logic */
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] h2,
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] h3 {
    letter-spacing: -0.025em;
}

.stSubheader, h2, h3 {
    color: #12372b !important;
}

.stProgress > div > div {
    background: linear-gradient(90deg, #047857, #d4af37) !important;
    border-radius: 99px !important;
}

/* Softer, more consistent dashboard notices */
[data-testid="stAlert"] {
    border-radius: 13px !important;
    border-width: 1px !important;
    box-shadow: 0 3px 12px rgba(18, 55, 43, .035);
}

@media (max-width: 700px) {
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewContainer"] .main .block-container {
        max-width: 100% !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }
    .brand {
        padding: 12px 14px !important;
        gap: 10px;
        flex-wrap: wrap;
    }
    .title {
        font-size: 22px !important;
    }
    .subtitle {
        font-size: 12px !important;
    }
    .card {
        padding: 16px !important;
    }
    .dashboard-hero {
        padding: 22px 20px;
        align-items: flex-start;
        flex-direction: column;
    }
    .dashboard-hero-badge {
        align-self: flex-start;
    }
    [data-testid="stMetric"] {
        padding: 14px !important;
        min-height: 96px;
    }
}


/* Premium executive dashboard refinements */
.section-kicker {
    margin: 0 0 4px;
    color: #8a6d1d;
    font-size: 10px;
    font-weight: 850;
    letter-spacing: .16em;
}
[data-testid="stMetric"] {
    border-radius: 17px !important;
    border-color: #d7e6dd !important;
    box-shadow: 0 6px 20px rgba(6, 78, 59, .055) !important;
    min-height: 118px;
}
[data-testid="stMetric"]:first-child {
    border-top: 3px solid #0b7556 !important;
}
[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}
[data-testid="stExpander"] {
    border: 1px solid #d7e6dd !important;
    border-radius: 15px !important;
    background: rgba(255,255,255,.82) !important;
}
[data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"] {
    border: 1px solid #e0ebe4;
    border-radius: 16px;
    padding: 8px;
    background: #ffffff;
    box-shadow: 0 5px 18px rgba(6, 78, 59, .035);
}

</style>
""", unsafe_allow_html=True)

def branding():
    st.markdown("""
    <div class="brand">
      <div class="logo">₹</div>
      <div class="title">FinSight</div>
      <div class="subtitle">Personal Finance Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

def dashboard(): 
    branding() 

    user_id = st.session_state.user[0]
 
    st.markdown(
        f'<div class="dashboard-hero">'
        f'<div class="dashboard-hero-copy">'
        f'<div class="dashboard-eyebrow">PERSONAL FINANCE OVERVIEW</div>'
        f'<div class="dashboard-heading">Good to see you, {st.session_state.user[1].split()[0]}.</div>'
        f'<div class="dashboard-description">Your money, clearly organised. Review your monthly position and make your next financial decision with confidence.</div>'
        f'</div>'
        f'<div class="dashboard-hero-badge"><span class="hero-badge-dot"></span> FINANCIAL SNAPSHOT</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Month selection and month-specific financial values
    st.subheader("📅 Monthly Financial Details")

    con = db()
    financial_rows = con.execute(
        """
        SELECT id, month, salary, other_income,
               fixed_expenses, savings, investments
        FROM financial_data
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()
    con.close()

    if financial_rows:
        default_month = financial_rows[0][1]
    else:
        default_month = datetime.now().strftime("%B %Y")

    month = st.text_input(
        "Month (example: September 2026 or 2026-09)",
        value=default_month,
        key="financial_month_input",
        placeholder="Example: September 2026"
    )
    month_key = month_to_key(month)

    # Match an existing financial record by normalized month, not by whichever
    # month happened to be saved most recently.
    selected_record = None
    if month_key:
        for row in financial_rows:  # newest matching record wins
            if month_to_key(row[1]) == month_key:
                selected_record = row
                break

    defaults = {
        "salary": float(selected_record[2]) if selected_record else 0.0,
        "other_income": float(selected_record[3]) if selected_record else 0.0,
        "fixed_expenses": float(selected_record[4]) if selected_record else 0.0,
        "savings": float(selected_record[5]) if selected_record else 0.0,
        "investments": float(selected_record[6]) if selected_record else 0.0,
    }

    # Month-specific widget keys ensure switching months loads that month's
    # values instead of reusing the previous month's inputs.
    widget_month_key = month_key or "invalid-month"
    for field, default_value in defaults.items():
        widget_key = f"financial_{field}_{widget_month_key}"
        if widget_key not in st.session_state:
            st.session_state[widget_key] = default_value

    col1, col2 = st.columns(2)

    with col1:
        salary = st.number_input(
            "💵 Monthly Salary",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"financial_salary_{widget_month_key}"
        )
        fixed_expenses = st.number_input(
            "🏠 Fixed Monthly Expenses",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"financial_fixed_expenses_{widget_month_key}"
        )
        savings = st.number_input(
            "🏦 Monthly Savings",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"financial_savings_{widget_month_key}"
        )

    with col2:
        other_income = st.number_input(
            "💰 Other Income",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"financial_other_income_{widget_month_key}"
        )
        investments = st.number_input(
            "📈 Monthly Investments",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"financial_investments_{widget_month_key}"
        )

    if st.button(
        "Save Monthly Financial Data",
        type="primary",
        use_container_width=True
    ):
        if not month_key:
            st.error("Please enter a valid month, such as September 2026 or 2026-09.")
        else:
            # Store a consistent month label and update an existing equivalent
            # month (including older labels such as 'September 2026').
            canonical_month = datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
            con = db()
            if selected_record:
                con.execute(
                    """
                    UPDATE financial_data
                    SET month = ?, salary = ?, other_income = ?,
                        fixed_expenses = ?, savings = ?, investments = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (canonical_month, salary, other_income, fixed_expenses,
                     savings, investments, selected_record[0], user_id)
                )
            else:
                con.execute(
                    """
                    INSERT INTO financial_data
                    (user_id, month, salary, other_income,
                     fixed_expenses, savings, investments)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, canonical_month, salary, other_income,
                     fixed_expenses, savings, investments)
                )
            con.commit()
            con.close()
            st.success("Monthly financial data saved successfully! ✅")
            st.rerun()

    if not month_key:
        st.warning("Enter the month as 'September 2026' or '2026-09' so FinSight can match expenses to it.")

    st.divider()

    # Financial summary
    total_income = salary + other_income
    available_balance = total_income - fixed_expenses

    st.markdown(
        '<div class="section-kicker">YOUR MONEY AT A GLANCE</div>',
        unsafe_allow_html=True
    )
    st.subheader("Current Financial Summary")

    # Five aligned KPI cards create a cleaner executive dashboard overview.
    c1, c2, c3, c4, c5 = st.columns(5, gap="medium")

    c1.metric("Total Income", f"₹{total_income:,.0f}")
    c2.metric("Fixed Expenses", f"₹{fixed_expenses:,.0f}")
    c3.metric("Available Balance", f"₹{available_balance:,.0f}")
    c4.metric("Savings", f"₹{savings:,.0f}")
    c5.metric("Investments", f"₹{investments:,.0f}")

    st.info(
        "💡 Expense tracking and category-wise financial analysis "
        "will appear here once you start adding individual expenses."
    )
        # Get total spending for Financial Health
    con = db()

    total_spending = con.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ? AND substr(date, 1, 7) = ?
        """,
        (user_id, month_key or "")
    ).fetchone()[0]

    con.close()

    # =========================================
    # FINANCIAL HEALTH DASHBOARD
    # =========================================

    st.divider()
    st.subheader("❤️ Financial Health")

    # Calculate financial health metrics
    savings_rate = (
        (savings / total_income) * 100
        if total_income > 0 else 0
    )

    investment_rate = (
        (investments / total_income) * 100
        if total_income > 0 else 0
    )

    expense_rate = (
        ((fixed_expenses + total_spending) / total_income) * 100
        if total_income > 0 else 0
    )

    # Calculate score
    health_score = 0

    # Savings contribution
    if savings_rate >= 30:
        health_score += 35
    elif savings_rate >= 20:
        health_score += 25
    elif savings_rate >= 10:
        health_score += 15
    elif savings_rate > 0:
        health_score += 8

    # Investment contribution
    if investment_rate >= 20:
        health_score += 30
    elif investment_rate >= 10:
        health_score += 20
    elif investment_rate > 0:
        health_score += 10

    # Expense control
    if expense_rate <= 50:
        health_score += 35
    elif expense_rate <= 65:
        health_score += 25
    elif expense_rate <= 80:
        health_score += 15
    elif expense_rate <= 100:
        health_score += 5

    health_score = min(health_score, 100)

    # Score message
    if health_score >= 80:
        health_status = "Excellent"
        health_message = "Your current financial indicators are strong."
    elif health_score >= 60:
        health_status = "Good"
        health_message = "You have a healthy financial foundation."
    elif health_score >= 40:
        health_status = "Fair"
        health_message = "There is room to improve your savings and spending balance."
    else:
        health_status = "Needs Attention"
        health_message = "Review your expenses and savings allocation."

    # Main score
    st.metric(
        "Financial Health Score",
        f"{health_score}/100",
        health_status
    )

    st.progress(health_score / 100)

    st.caption(health_message)

    # Financial indicators
    h1, h2, h3 = st.columns(3)

    h1.metric(
        "💰 Savings Rate",
        f"{savings_rate:.1f}%"
    )

    h2.metric(
        "📈 Investment Rate",
        f"{investment_rate:.1f}%"
    )

    h3.metric(
        "💸 Expense Rate",
        f"{expense_rate:.1f}%"
    )

    # Financial health observations
    st.markdown("### 🔍 Financial Health Overview")

    if savings_rate >= 20:
        st.success(
            f"🏦 Your savings rate is {savings_rate:.1f}% of your income."
        )
    elif savings_rate > 0:
        st.warning(
            f"🏦 Your savings rate is {savings_rate:.1f}%. "
            "Increasing your savings contribution could strengthen your financial position."
        )
    else:
        st.info(
            "🏦 No savings contribution has been recorded yet."
        )

    if investment_rate > 0:
        st.success(
            f"📈 You are allocating {investment_rate:.1f}% of your income toward investments."
        )
    else:
        st.info(
            "📈 No investment contribution has been recorded yet."
        )

    if expense_rate <= 60:
        st.success(
            f"💸 Your recorded expenses represent {expense_rate:.1f}% of your income."
        )
    elif expense_rate <= 80:
        st.warning(
            f"💸 Your recorded expenses represent {expense_rate:.1f}% of your income."
        )
    else:
        st.error(
            f"💸 Your recorded expenses represent {expense_rate:.1f}% of your income."
        )

            # =========================================
    # SPENDING ANALYTICS
    # =========================================

    st.divider()
    st.subheader("📊 Spending Analytics")

    con = db()

    category_data = con.execute(
        """
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id = ? AND substr(date, 1, 7) = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
        """,
        (user_id, month_key or "")
    ).fetchall()

    total_spending = con.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ? AND substr(date, 1, 7) = ?
        """,
        (user_id, month_key or "")
    ).fetchone()[0]

    con.close()

    remaining_after_expenses = total_income - fixed_expenses - total_spending

    # Top metrics
    a1, a2, a3 = st.columns(3)

    a1.metric(
        "💸 Total Spending",
        f"₹{total_spending:,.0f}"
    )

    a2.metric(
        "📊 Spending Categories",
        len(category_data)
    )

    a3.metric(
        "💰 Balance After Expenses",
        f"₹{remaining_after_expenses:,.0f}"
    )

    if category_data:

        # Calculate percentages
        category_percentages = []

        for category, amount in category_data:
            percentage = (
                (amount / total_spending) * 100
                if total_spending > 0 else 0
            )

            category_percentages.append(
                (category, amount, percentage)
            )

        # Highest spending category
        highest_category = category_percentages[0]

        st.markdown("### 🔝 Top Spending Category")

        st.info(
            f"🏷️ **{highest_category[0]}** — "
            f"₹{highest_category[1]:,.0f} "
            f"({highest_category[2]:.1f}% of total spending)"
        )

        # Category breakdown
        st.markdown("### 📋 Category Breakdown")

        for category, amount, percentage in category_percentages:

            st.write(
                f"**{category}** · "
                f"₹{amount:,.0f} · "
                f"{percentage:.1f}%"
            )

            st.progress(
                min(percentage / 100, 1.0)
            )

        # Bar chart
        st.markdown("### 📊 Spending by Category")

        chart_data = {
            "Category": [
                row[0] for row in category_data
            ],
            "Amount": [
                row[1] for row in category_data
            ]
        }

        chart_df = pd.DataFrame(chart_data)

        st.bar_chart(
         data=chart_df,
         x="Category",
         y="Amount"
        )

        # Spending observations
        st.markdown("### 🔍 Spending Observations")

        if highest_category[2] >= 40:
            st.warning(
                f"⚠️ **{highest_category[0]}** accounts for "
                f"{highest_category[2]:.1f}% of your recorded spending."
            )
        elif highest_category[2] >= 25:
            st.info(
                f"💡 **{highest_category[0]}** is your largest "
                f"spending category at {highest_category[2]:.1f}%."
            )
        else:
            st.success(
                "✅ Your spending is distributed across multiple categories."
            )

    else:
        st.info(
            "💡 Add some expenses to see your spending analytics 📈"
        )
            # =========================================
    # EXPENSE PREDICTION
    # =========================================

    st.divider()
    st.subheader("🔮 Expense Prediction")

    con = db()

    expense_history = con.execute(
        """
        SELECT date, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date
        """,
        (user_id,)
    ).fetchall()

    con.close()

    if expense_history:

        # Group expenses by month
        monthly_expenses = {}

        for expense_date, amount in expense_history:
            month_key = str(expense_date)[:7]   # YYYY-MM

            if month_key not in monthly_expenses:
                monthly_expenses[month_key] = 0

            monthly_expenses[month_key] += float(amount)

        sorted_months = sorted(monthly_expenses.keys())

        # Display historical data
        st.markdown("### 📊 Historical Monthly Spending")

        history_data = {
        "Month": sorted_months,
            "Spending": [
                monthly_expenses[month]
                for month in sorted_months
            ]
        }

                history_df = pd.DataFrame(history_data)

                st.line_chart(
                   data=history_df,
                   x="Month",
                   y="Spending"
                )

        # Need at least 2 months for trend prediction
        if len(sorted_months) >= 2:

            y_values = [
                monthly_expenses[month]
                for month in sorted_months
            ]

            # X values: 1, 2, 3...
            x_values = list(range(1, len(y_values) + 1))

            n = len(x_values)

            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(
                x * y
                for x, y in zip(x_values, y_values)
            )
            sum_x_squared = sum(
                x * x
                for x in x_values
            )

            denominator = (
                n * sum_x_squared - sum_x ** 2
            )

            if denominator != 0:

                # Linear regression:
                # y = slope*x + intercept

                slope = (
                    (n * sum_xy) -
                    (sum_x * sum_y)
                ) / denominator

                intercept = (
                    sum_y - slope * sum_x
                ) / n

                next_x = n + 1

                predicted_expense = (
                    slope * next_x + intercept
                )

                # Avoid negative predictions
                predicted_expense = max(
                    0,
                    predicted_expense
                )

                st.markdown("### 🔮 Next Month Prediction")

                p1, p2 = st.columns(2)

                p1.metric(
                    "Predicted Spending",
                    f"₹{predicted_expense:,.0f}"
                )

                average_spending = (
                    sum(y_values) / len(y_values)
                )

                p2.metric(
                    "Historical Average",
                    f"₹{average_spending:,.0f}"
                )

                difference = (
                    predicted_expense -
                    average_spending
                )

                if difference > 0:
                    st.warning(
                        f"📈 FinSight predicts spending may "
                        f"increase by approximately "
                        f"₹{difference:,.0f} compared with "
                        f"your historical average."
                    )

                elif difference < 0:
                    st.success(
                        f"📉 FinSight predicts spending may "
                        f"decrease by approximately "
                        f"₹{abs(difference):,.0f} compared "
                        f"with your historical average."
                    )

                else:
                    st.info(
                        "📊 Predicted spending is close to "
                        "your historical average."
                    )

                st.caption(
                    "Prediction is based on the trend in your "
                    "recorded monthly expenses."
                )

            else:
                st.info(
                    "Not enough variation in the historical "
                    "data to calculate a trend."
                )

        else:

            st.info(
                "🔮 Add expenses across at least 2 different "
                "months to unlock spending prediction."
            )

    else:

        st.info(
            "🔮 Add some expenses to start building your "
            "spending prediction model."
        )

        # Intelligent Insights
    st.divider()

    st.subheader("🧠 FinSight Intelligent Insights")
    

    if category_data:
        highest_category = category_data[0][0]
        highest_amount = category_data[0][1]

        spending_percentage = (
            (total_spending / total_income) * 100
            if total_income > 0 else 0
        )

        savings_percentage = (
            (savings / total_income) * 100
            if total_income > 0 else 0
        )

        investment_percentage = (
            (investments / total_income) * 100
            if total_income > 0 else 0
        )

        st.markdown(
            f"💳 **Highest Spending Category:** "
            f"{highest_category} — ₹{highest_amount:,.0f}"
        )

        if spending_percentage > 70:
            st.warning(
                f"⚠️ Your recorded expenses are "
                f"{spending_percentage:.1f}% of your total income. "
                "Consider reviewing your largest spending categories."
            )
        elif spending_percentage > 50:
            st.info(
                f"💡 Your recorded expenses are "
                f"{spending_percentage:.1f}% of your total income."
            )
        else:
            st.success(
                f"✅ Your recorded expenses are "
                f"{spending_percentage:.1f}% of your total income."
            )

        st.markdown(
            f"🏦 **Savings:** {savings_percentage:.1f}% of income"
        )

        st.markdown(
            f"📈 **Investments:** {investment_percentage:.1f}% of income"
        )

        if remaining_after_expenses < 0:
            st.error(
                "🚨 Your expenses currently exceed your available income."
            )
        elif remaining_after_expenses == 0:
            st.warning(
                "⚠️ Your recorded expenses use your entire available balance."
            )
        else:
            st.success(
                f"💰 You currently have ₹{remaining_after_expenses:,.0f} "
                "remaining after recorded expenses."
            )

    else:
        st.info(
            "💡 Add some expenses to unlock personalized financial insights."
        )
# =========================================
# SMART BUDGET RECOMMENDATIONS
# =========================================

    st.divider()
    st.subheader("💡 Smart Budget Recommendations")

    if category_data:

        top_category = category_data[0][0]
        top_amount = float(category_data[0][1])

        st.markdown(
            f"📌 **{top_category}** is your highest spending category "
            f"at **₹{top_amount:,.0f}**."
        )

        st.info(
            "💡 Consider setting a monthly limit for your highest "
            "spending category and monitoring it regularly."
        )

    else:

        st.info(
            "💡 Add expenses to receive personalized budget recommendations."
        )


    # Savings recommendation

    if total_income > 0:

        current_savings_rate = (
            savings / total_income
        ) * 100

        if current_savings_rate < 10:

            st.warning(
                f"💰 Your current savings rate is "
                f"{current_savings_rate:.1f}%. "
                "Consider gradually increasing your savings."
            )

        elif current_savings_rate < 20:

            st.info(
                f"💰 Your current savings rate is "
                f"{current_savings_rate:.1f}%. "
                "Continue tracking your savings consistently."
            )

        else:

            st.success(
                f"💰 Your current savings rate is "
                f"{current_savings_rate:.1f}%. "
                "Keep maintaining your savings habit."
            )


    # Spending recommendation

    if total_income > 0:

        current_spending_rate = (
            total_spending / total_income
        ) * 100

        if current_spending_rate > 70:

            st.warning(
                f"📊 Recorded spending is "
                f"{current_spending_rate:.1f}% of your income. "
                "Review your largest spending categories."
            )

        elif current_spending_rate > 50:

            st.info(
                f"📊 Recorded spending is "
                f"{current_spending_rate:.1f}% of your income. "
                "Keep monitoring your expenses."
            )

        else:

            st.success(
                f"📊 Recorded spending is "
                f"{current_spending_rate:.1f}% of your income. "
                "Your recorded spending is currently below 50% of income."
            )

    st.write("")
        # Monthly Financial Trends
    st.divider()

    st.subheader("📈 Monthly Financial Trends")

    con = db()

    monthly_data = con.execute(
        """
        SELECT month, salary, other_income,
               fixed_expenses, savings, investments
        FROM financial_data
        WHERE user_id = ?
        ORDER BY id
        """,
        (user_id,)
    ).fetchall()

    con.close()

    if monthly_data:
        trend_data = {
            "Month": [row[0] for row in monthly_data],
            "Income": [row[1] + row[2] for row in monthly_data],
            "Fixed Expenses": [row[3] for row in monthly_data],
            "Savings": [row[4] for row in monthly_data],
            "Investments": [row[5] for row in monthly_data]
        }

        st.line_chart(
            trend_data,
            x="Month",
            y=[
                "Income",
                "Fixed Expenses",
                "Savings",
                "Investments"
            ]
        )

        st.markdown("### 📋 Monthly Overview")

        for row in monthly_data:
            month_name, salary_value, other_income_value, fixed_value, savings_value, investment_value = row

            total_month_income = salary_value + other_income_value

            st.write(
                f"**{month_name}** · "
                f"Income: ₹{total_month_income:,.0f} · "
                f"Expenses: ₹{fixed_value:,.0f} · "
                f"Savings: ₹{savings_value:,.0f} · "
                f"Investments: ₹{investment_value:,.0f}"
            )

    else:
        st.info(
            "💡 Save monthly financial data to start seeing trends."
        )
        # Expense Tracker
    st.divider()

    st.subheader("🧾 Add an Expense")
    st.write("Record your daily expenses to help FinSight analyze your spending.")

    expense_col1, expense_col2 = st.columns(2)

    with expense_col1:
        expense_date = st.date_input("📅 Date")

        expense_category = st.selectbox(
            "🏷️ Category",
            [
                "Food",
                "Transport",
                "Shopping",
                "Bills",
                "Education",
                "Entertainment",
                "Healthcare",
                "Travel",
                "Subscriptions",
                "Other"
            ]
        )

    with expense_col2:
        expense_amount = st.number_input(
            "💰 Amount",
            min_value=0.0,
            step=50.0,
            format="%.2f"
        )

        expense_description = st.text_input(
            "📝 Description",
            placeholder="Example: Lunch, bus ticket, books..."
        )

    if st.button(
        "➕ Add Expense",
        type="primary",
        use_container_width=True
    ):
        if expense_amount <= 0:
            st.error("Please enter an expense amount greater than ₹0.")
        else:
            con = db()

            con.execute(
                """
                INSERT INTO expenses
                (user_id, date, category, description, amount)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    str(expense_date),
                    expense_category,
                    expense_description.strip(),
                    expense_amount
                )
            )

            con.commit()
            con.close()

            st.success("Expense added successfully! ✅")
            st.rerun()

    # Expense History
    st.divider()

    st.subheader("📋 Recent Expenses")

    con = db()

    expenses = con.execute(
        """
        SELECT date, category, description, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (user_id,)
    ).fetchall()

    con.close()

    if expenses:
        for date, category, description, amount in expenses:
            st.write(
                f"**{date}** · {category} · "
                f"{description or 'No description'} · "
                f"**₹{amount:,.2f}**"
            )
    else:
        st.info("No expenses recorded yet.")

    # Logout
    st.divider()

    if st.button("Logout", use_container_width=True):
        token = st.query_params.get("session")

        delete_session(token)

        st.query_params.clear()

        st.session_state.logged_in = False
        st.session_state.user = None

        st.rerun()


def auth():
    branding()
    st.markdown('<div class="card">', unsafe_allow_html=True)

    if st.session_state.mode == "login":
        st.markdown(
            '<div class="welcome">Welcome back</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="hint">Sign in to continue to your financial dashboard</div>',
            unsafe_allow_html=True
        )

        email = st.text_input(
            "Email",
            placeholder="Enter your email",
            key="login_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )

        if st.button(
            "Login",
            type="primary",
            use_container_width=True
        ):
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                user = login_user(email, password)

                if user:
                   token = create_session(user[0])

                   st.query_params["session"] = token

                   st.session_state.logged_in = True
                   st.session_state.user = user

                   st.rerun()
                else:
                    st.error("Invalid email or password.")

        st.write("")

        if st.button(
            "Create a new account",
            use_container_width=True
        ):
            st.session_state.mode = "signup"
            st.rerun()

    else:
        st.markdown(
            '<div class="welcome">Create your account</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="hint">Start managing your personal finances intelligently</div>',
            unsafe_allow_html=True
        )

        name = st.text_input(
            "Full Name",
            placeholder="Enter your name",
            key="signup_name"
        )

        email = st.text_input(
            "Email",
            placeholder="Enter your email",
            key="signup_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Create a password",
            key="signup_password"
        )

        confirm = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Re-enter your password",
            key="signup_confirm_password"
        )

        if st.button(
            "Create Account",
            type="primary",
            use_container_width=True
        ):
            if not all([name, email, password, confirm]):
                st.error("Please fill in all fields.")

            elif "@" not in email or "." not in email:
                st.error("Please enter a valid email address.")

            elif len(password) < 6:
                st.error("Password must contain at least 6 characters.")

            elif password != confirm:
                st.error("Passwords do not match.")

            elif create_user(name, email, password):
                st.success("Account created successfully!")
                st.session_state.mode = "login"
                st.rerun()

            else:
                st.error("An account with this email already exists.")

        st.write("")

        if st.button(
            "Back to Login",
            use_container_width=True
        ):
            st.session_state.mode = "login"
            st.rerun()

    st.markdown(
        '<div class="small">Data-driven • Student Project Prototype • DAE</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)


if st.session_state.logged_in:
    dashboard()
else:
    auth()
 
