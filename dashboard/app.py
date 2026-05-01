import importlib.util
from pathlib import Path
import requests
import sys
import streamlit as st
import time

# Add repo root to Python path so dashboard can import backend/data/logic modules.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load dashboard.py as an explicit module to avoid import-name conflicts.
DASHBOARD_MODULE_PATH = Path(__file__).resolve().with_name("dashboard.py")
spec = importlib.util.spec_from_file_location("indra_grid_dashboard", DASHBOARD_MODULE_PATH)
dashboard = importlib.util.module_from_spec(spec)
sys.modules["indra_grid_dashboard"] = dashboard
spec.loader.exec_module(dashboard)


API = "http://127.0.0.1:8001"

# Main Streamlit page settings for the authenticated app.
st.set_page_config(
    page_title="Indra-Grid",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Session state keeps login/user data across Streamlit reruns.
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = "Operator"
if "post_login_loading" not in st.session_state:
    st.session_state.post_login_loading = False


def loading_screen():
    # Short branded transition shown immediately after login.
    logo_html = dashboard.brand_logo_html("loading-logo", 72)
    st.markdown(
        """
        <style>
        .stApp { background:#0F0D0A; }
        .loading-card {
            max-width:460px;
            margin:18vh auto 0;
            padding:30px 32px;
            border:1px solid #2E2A22;
            border-radius:8px;
            background:#1C1A16;
            font-family:Barlow,Arial,sans-serif;
            box-shadow:0 18px 45px rgba(0,0,0,.32);
            text-align:center;
        }
        .loading-logo {
            width:72px;
            height:72px;
            object-fit:cover;
            border-radius:8px;
            border:1px solid #2E2A22;
            margin-bottom:12px;
        }
        .loading-brand {
            font-size:28px;
            font-weight:800;
            letter-spacing:3px;
            color:#C87000;
            text-transform:uppercase;
        }
        .loading-sub {
            margin-top:6px;
            font-size:12px;
            color:#9A8568;
            letter-spacing:1.6px;
            text-transform:uppercase;
        }
        .loading-bar {
            height:5px;
            margin-top:22px;
            border-radius:4px;
            overflow:hidden;
            background:#2E2A22;
        }
        .loading-bar span {
            display:block;
            width:42%;
            height:100%;
            background:#C87000;
            animation:load 1.1s ease-in-out infinite;
        }
        @keyframes load {
            0% { transform:translateX(-110%); }
            100% { transform:translateX(260%); }
        }
        </style>
        """
        + f"""
        <div class="loading-card">
            {logo_html}
            <div class="loading-brand">Indra-Grid</div>
            <div class="loading-sub">Loading optimizer, plant state and dispatch controls</div>
            <div class="loading-bar"><span></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def login():
    # Login/register screen calls the FastAPI backend and stores the JWT token.
    logo_html = dashboard.brand_logo_html("login-logo", 86)
    st.markdown(
        """
        <style>
        .stApp { background:#0F0D0A; }
        .login-card {
            max-width:420px;
            margin:8vh auto 0;
            padding:28px;
            border:1px solid #2E2A22;
            border-radius:8px;
            background:#1C1A16;
            font-family:Barlow,Arial,sans-serif;
            text-align:center;
            box-shadow:0 18px 45px rgba(0,0,0,.32);
        }
        .login-logo {
            width:86px;
            height:86px;
            object-fit:cover;
            border-radius:8px;
            border:1px solid #2E2A22;
            margin-bottom:12px;
        }
        .login-brand {
            font-size:24px;
            font-weight:800;
            letter-spacing:2px;
            color:#C87000;
            text-transform:uppercase;
        }
        .login-sub {
            font-size:12px;
            color:#9A8568;
            margin-top:4px;
        }
        </style>
        """
        + f"""
        <div class="login-card">
            {logo_html}
            <div class="login-brand">Indra-Grid</div>
            <div class="login-sub">Smart Energy Login</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Owner", "Operator"])
    col1, col2 = st.columns(2)

    if col1.button("Login", use_container_width=True):
        try:
            with st.spinner("Verifying credentials..."):
                # Authenticate against backend /login and receive a JWT token.
                res = requests.post(
                    f"{API}/login",
                    json={"username": username, "password": password, "role": role},
                    timeout=4,
                ).json()
            if res.get("status") == "success":
                st.session_state.token = res["token"]
                st.session_state.user = username
                st.session_state.role = res.get("role", "Operator")
                st.session_state.post_login_loading = True
                st.rerun()
            else:
                st.error(res.get("message", "Login failed"))
        except Exception:
            st.error("Backend not running. Start it with: python -m uvicorn backend.api:app --port 8001 --reload")

    if col2.button("Register", use_container_width=True):
        try:
            with st.spinner("Creating secure user profile..."):
                # Create a user in the backend, then user can log in.
                res = requests.post(
                    f"{API}/register",
                    json={"username": username, "password": password, "role": role},
                    timeout=4,
                ).json()
            if res.get("status") == "success":
                st.success("User created. Now login.")
            else:
                st.error(res.get("message", "Registration failed"))
        except Exception:
            st.error("Backend not running.")


def app():
    # Hand off to the full dashboard once authentication is complete.
    dashboard.run(st.session_state.user, st.session_state.role)


# Router: unauthenticated users see login; authenticated users see dashboard.
if not st.session_state.token:
    login()
elif st.session_state.post_login_loading:
    loading_screen()
    time.sleep(1.1)
    st.session_state.post_login_loading = False
    st.rerun()
else:
    app()
