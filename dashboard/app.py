import requests
import streamlit as st

import dashboard


API = "http://127.0.0.1:8001"

st.set_page_config(
    page_title="Indra-Grid | Enterprise EMS",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = "Operator"


def login():
    st.markdown(
        """
        <div style="max-width:420px;margin:9vh auto 0;padding:28px;border:1px solid #E8DDD0;
        border-radius:8px;background:#FFFFFF;font-family:Barlow,Arial,sans-serif;">
            <div style="font-size:24px;font-weight:800;letter-spacing:2px;color:#C87000;
            text-transform:uppercase;">Indra-Grid</div>
            <div style="font-size:12px;color:#7A6A50;margin-top:4px;">Enterprise Energy Management Login</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role for registration", ["Owner", "Operator", "Admin"])
    col1, col2 = st.columns(2)

    if col1.button("Login", use_container_width=True):
        try:
            res = requests.post(
                f"{API}/login",
                json={"username": username, "password": password},
                timeout=4,
            ).json()
            if res.get("status") == "success":
                st.session_state.token = res["token"]
                st.session_state.user = username
                st.session_state.role = res.get("role", "Operator")
                st.rerun()
            else:
                st.error(res.get("message", "Login failed"))
        except Exception:
            st.error("Backend not running. Start it with: python -m uvicorn backend.api:app --port 8001 --reload")

    if col2.button("Register", use_container_width=True):
        try:
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
    dashboard.run(st.session_state.user, st.session_state.role)


if not st.session_state.token:
    login()
else:
    app()
