from session_manager import SessionManager
from visualisation.dashboard_server import create_app

session_manager = SessionManager()
app = create_app(session_manager=session_manager)
