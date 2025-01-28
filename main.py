import streamlit as st
import json
import logging
import sys
from datetime import datetime
from ig_api import IGClient
from utils import format_positions
from options_processor import OptionsProcessor

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''
    if 'positions' not in st.session_state:
        st.session_state.positions = None
    if 'client' not in st.session_state:
        st.session_state.client = None
    if 'stream' not in st.session_state:
        st.session_state.stream = False
    if 'options_processor' not in st.session_state:
        st.session_state.options_processor = None


def logout():
    st.session_state.logged_in = False
    st.session_state.positions = None
    st.session_state.client = None
    st.session_state.options_processor = None
    st.rerun()


def toggle_streaming():
    st.session_state.stream = not st.session_state.stream


def main():
    st.set_page_config(page_title="IG Trading API Client",
                       page_icon="📈",
                       layout="centered")

    init_session_state()

    st.title("IG Trading API Client")

    # Sidebar for credentials
    with st.sidebar:
        st.header("Credentials")

        if not st.session_state.logged_in:
            api_key = st.text_input("API Key",
                                    type="password",
                                    value=st.session_state.api_key)
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.checkbox("Save API Key"):
                st.session_state.api_key = api_key

            if st.button("Login", use_container_width=True):
                try:
                    client = IGClient(api_key, username, password)
                    success = client.login()
                    if success:
                        st.session_state.client = client
                        st.session_state.options_processor = OptionsProcessor(client)
                        st.session_state.logged_in = True
                        st.success("Successfully logged in!")
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your credentials.")
                except Exception as e:
                    st.error(f"Error during login: {str(e)}")
        else:
            st.success("Logged in successfully!")

            # Add streaming controls
            st.header("Data Streaming")
            st.slider("Refresh interval (seconds)", 1.0, 30.0, value=10.0, key="run_every")

            # Streaming buttons
            st.button("Start streaming", disabled=st.session_state.stream, on_click=toggle_streaming)
            st.button("Stop streaming", disabled=not st.session_state.stream, on_click=toggle_streaming)

            # Logout button
            st.button("Logout", on_click=logout, use_container_width=True)

    # Main content area
    if st.session_state.logged_in and st.session_state.client:
        # Set up the streaming fragment
        if st.session_state.stream:
            run_every = st.session_state.run_every
        else:
            run_every = None

        @st.fragment(run_every=run_every)
        def show_positions():
            try:
                positions = st.session_state.client.get_positions()
                if positions:
                    # Process positions with options calculations
                    processed_positions = st.session_state.options_processor.process_positions(positions)

                    st.subheader("Current Positions")
                    # Add update timestamp
                    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    formatted_positions = format_positions(processed_positions)
                    st.json(formatted_positions)
                    if st.session_state.stream:
                        logger.info("Positions updated via streaming")
            except Exception as e:
                st.error(f"Error fetching positions: {str(e)}")
                # If the error is due to authentication, log out the user
                if "Not logged in" in str(e):
                    logout()

        # Call the fragment
        show_positions()

    else:
        st.info("Please log in using your credentials in the sidebar.")


if __name__ == "__main__":
    main()