"""Live check for the agent skill (R24): the client reaches the deployed API and the facts the eval graders rely on still hold.

    python scripts/skill_live_check.py [--base URL]
"""
import json
import subprocess
import sys
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1] / "skills/well-log-lithology/scripts/wll.py"
base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "https://well-log-lithology.vercel.app"


def call(*args):
    r = subprocess.run([sys.executable, str(CLIENT), "--base", base, *args], capture_output=True, text=True, timeout=180, check=False)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


assert call("about")["kansas_lithology_validated"] is False
lit = call("lithology", "15/9-23")
assert lit["split"] == "hidden" and lit["blind_score"] == -0.395 and lit["doubtful_m"] == 45 and round(lit["rock_shares"]["Shale"], 3) == 0.722, lit
q = call("quality", "1001184201")
assert q["curves"] == ["GR", "NPHI", "RDEP", "CALI"] and q["coverage_gr_neutron_density"] == 0.0 and round(q["out_of_range_share"], 2) == 0.33, q
he, hu = call("unit", "Heebner"), call("unit", "Hutchinson Salt")
assert (he["median_agreement"], he["lift"], he["passed"]) == (0.9, 1.57, False) and (hu["median_agreement"], hu["lift"]) == (0.0, 1.44), (he, hu)
assert call("lithology", "6507/7-2").get("not_found") is True
print(f"skill live check passed against {base}")
