import sys
import os

# Garantit que les imports src.agents, src.db, etc. fonctionnent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Lance le dashboard Streamlit depuis src/app.py
import runpy
runpy.run_path(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "app.py"),
    run_name="__main__",
)
