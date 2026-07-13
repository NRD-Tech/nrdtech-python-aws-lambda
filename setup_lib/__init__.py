"""Project setup library — re-exports symbols used by tests and setup.py."""

import shutil  # noqa: F401 — re-exported for test monkeypatching

from setup_lib import github_gating as github_gating  # noqa: F401
from setup_lib.apply_templates import *  # noqa: F401,F403
from setup_lib.aws_creds import *  # noqa: F401,F403
from setup_lib.aws_discovery import *  # noqa: F401,F403
from setup_lib.cli import main  # noqa: F401
from setup_lib.config_io import *  # noqa: F401,F403
from setup_lib.constants import *  # noqa: F401,F403
from setup_lib.github_gating import *  # noqa: F401,F403
from setup_lib.prompts import *  # noqa: F401,F403
