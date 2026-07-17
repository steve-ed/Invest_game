# Force all transitive kernel imports at gunicorn worker startup so the first
# player's game doesn't pay the 12-16 second cold-import cost.
import importlib
for _mod in [
    "kernel", "ai", "actors", "property_model", "scoring",
    "void_maintenance", "data.uk_macro_history",
    "narrative.branching", "narrative.scenario_events",
    "player.choices", "shocks", "scenarios",
]:
    try:
        importlib.import_module(_mod)
    except Exception:
        pass

from session_manager import SessionManager
from visualisation.dashboard_server import create_app

session_manager = SessionManager()
app = create_app(session_manager=session_manager)
