import streamlit as st
import requests
import dashboard

st.set_page_config(page_title="Indra-Grid", layout="wide")

API_URL = "http://127.0.0.1:8000"

# ─── SESSION ─────────────────
if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

# ─── LOGIN UI ─────────────────
def login():
    st.title("🔐 Indra-Grid Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    # LOGIN
    if col1.button("Login"):
        try:
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
    with st.sidebar:
        st.success(f"👤 {st.session_state.user}")

        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()

    dashboard.run()

# ─── ROUTER ─────────────────
if not st.session_state.token:
    login()
else:
    app()