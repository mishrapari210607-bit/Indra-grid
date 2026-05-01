import streamlit as st
import requests
import dashboard

# Legacy Streamlit login entrypoint kept for older dashboard runs.
st.set_page_config(page_title="Indra-Grid", layout="wide")

API_URL = "http://127.0.0.1:8000"

# ─── SESSION ─────────────────
# Store login token and username across Streamlit reruns.
if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

# ─── LOGIN UI ─────────────────
def login():
    # Simple login/register form for the older backend port.
    st.title("🔐 Indra-Grid Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    # LOGIN
    if col1.button("Login"):
        try:
            # Send credentials to backend and store token on success.
            res = requests.post(
                f"{API_URL}/login",
                json={"username": username, "password": password}
            )

            data = res.json()

            if data["status"] == "success":
                st.session_state.token = data["token"]
                st.session_state.user = username
                st.success("Login successful")
                st.rerun()
            else:
                st.error(data["message"])

        except:
            st.error("Backend not running")

    # REGISTER
    if col2.button("Register"):
        try:
            # Create account through backend register API.
            res = requests.post(
                f"{API_URL}/register",
                json={"username": username, "password": password}
            )

            data = res.json()

            if data["status"] == "success":
                st.success("User created! Now login.")
            else:
                st.error(data["message"])

        except:
            st.error("Backend not running")

# ─── MAIN APP ─────────────────
def app():
    # Authenticated area with logout button and dashboard handoff.
    with st.sidebar:
        st.success(f"👤 {st.session_state.user}")

        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()

    dashboard.run()

# ─── ROUTER ─────────────────
# Route user to login until a token exists.
if not st.session_state.token:
    login()
else:
    app()
