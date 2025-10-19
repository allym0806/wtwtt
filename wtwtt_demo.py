import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
import uuid
from datetime import datetime, timezone, timedelta
import json
import os
import pandas as pd

CSV_PATH = "/Users/ally/Documents/wtwtt/demo_amount.csv"
COLUMNS = ["user_id", "first_seen", "last_seen", "visits", "amount"]

def _ensure_csv(csv_path=CSV_PATH):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.exists(csv_path):
        pd.DataFrame(columns=COLUMNS).to_csv(csv_path, index=False)

def _load_df(csv_path=CSV_PATH) -> pd.DataFrame:
    _ensure_csv(csv_path)
    return pd.read_csv(csv_path)

def upsert_profile_csv(profile: dict, amount: float, csv_path=CSV_PATH):
    """
    Insert or update the row for profile['user_id'] with latest fields + amount.
    """
    df = _load_df(csv_path)

    row = {
        "user_id": profile["user_id"],
        "first_seen": profile["first_seen"],
        "last_seen": profile["last_seen"],
        "visits": int(profile.get("visits", 1)),
        "amount": float(amount),
    }

    if not df.empty and "user_id" in df.columns:
        mask = df["user_id"] == row["user_id"]
        if mask.any():
            df.loc[mask, COLUMNS] = [
                row["user_id"],
                row["first_seen"],
                row["last_seen"],
                row["visits"],
                row["amount"],
            ]
        else:
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row], columns=COLUMNS)

    df.to_csv(csv_path, index=False)

def get_tomorrow_pretty():
    tomorrow = datetime.now() + timedelta(days=1)
    # Format like "October 20"
    day = tomorrow.day
    # Add ordinal suffix
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    return tomorrow.strftime(f"%B {day}{suffix}, %Y")

# Center Align text
st.markdown(
    """
    <style>
        .stApp {
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Cookies set up
COOKIE_PREFIX = st.secrets["cookies"]["prefix"]
COOKIE_PASSWORD = st.secrets["cookies"]["password"]

# --- 2) Initialize cookies (encrypted) ---
cookies = EncryptedCookieManager(prefix=COOKIE_PREFIX, password=COOKIE_PASSWORD)

# Important: cookies need one render to be ready on a brand-new client.
# If not ready, stop here and let the page reload once.
if not cookies.ready():
    st.stop()

# --- 3) Helper: read a JSON blob cookie safely ---
def read_json_cookie(key: str, default=None):
    val = cookies.get(key)
    if not val:
        return default
    try:
        return json.loads(val)
    except Exception:
        return default

# --- 4) Helper: write a JSON blob cookie and persist ---
def write_json_cookie(key: str, obj):
    cookies[key] = json.dumps(obj)
    cookies.save()  # persist to browser

# --- 5) Get or create user cookie ---
now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

profile = read_json_cookie("user_profile")
first_time = False

if "visit_logged" not in st.session_state:
    st.session_state.visit_logged = False  # Track if we've already counted this visit

if profile is None:
    # First-time visitor → create profile
    profile = {
        "user_id": str(uuid.uuid4()),
        "first_seen": now_iso,
        "last_seen": now_iso,
        "visits": 1
    }
    write_json_cookie("user_profile", profile)
    first_time = True
    st.session_state.visit_logged = True  # Mark visit counted
else:
    # Returning visitor
    if not st.session_state.visit_logged:
        # Only increment once per new session load, not every re-run
        profile["visits"] = int(profile.get("visits", 0)) + 1
        profile["last_seen"] = now_iso
        write_json_cookie("user_profile", profile)
        st.session_state.visit_logged = True  # Prevent further increments

# Read Cookie
if first_time:
    st.success("Welcome, first-time visitor! 🎉 Play against the world and win!")
else:
    st.info("Welcome back player!")


# Streamlit App

st.header("What's the World Thinking Today?")

@st.dialog("Yesterday's Results")
def view_results():
    st.success(f"You won against the world! 🎉")
    with st.container(border=True):
        st.subheader("The Greed Line")

        st.write('Pick any dollar amount — from $0 to as high as you want.\n\nYou only win if you’re below the average — but not too far below. \n\nFind the sweet spot and cash in.')
        st.write('')
        st.success(f"You entered: __.")
        st.write('Display world results here')
        st.write('')
    

with st.container(border=False):
    if st.button("Yesterday's Results", width='stretch'):
        view_results()

# Amount set up
# Try to read a previously saved amount (separate cookie key).
amount = read_json_cookie("amount", default=None)

# For when no answer is given
if amount is None:

    with st.container(border=True):
        st.subheader("The Greed Line")

        st.write('Pick any dollar amount — from $0 to as high as you want.\n\nYou only win if you’re below the average — but not too far below. \n\nFind the sweet spot and cash in.')
        st.write('')
        user_amount = st.number_input('Select an amount:', 0, icon=":material/attach_money:",help="For those obsessed with statistics, we're taking 1 standard deviation below the average.")
        st.write('')
        st.write('')

    with st.container(border=False):
        if st.button('Submit', width='stretch'):
            write_json_cookie("amount", float(user_amount))
            upsert_profile_csv(profile, float(user_amount))
            
            date_tomorrow = get_tomorrow_pretty()
            st.success(f"You entered: {user_amount:.2f}. Check results at {date_tomorrow} 12:00 EDT!")

# For when user already submitted
else:
    # Amount exists → just display it
    with st.container(border=True):
        st.subheader("The Greed Line")

        st.write('Pick any dollar amount — from $0 to as high as you want.\n\nYou only win if you’re below the average — but not too far below. \n\nFind the sweet spot and cash in.')
        st.write('')
        date_tomorrow = get_tomorrow_pretty()
        st.success(f"You entered: {amount:.2f}. Check results at {date_tomorrow} 12:00 EDT!")
        st.write('')
        st.write('')
