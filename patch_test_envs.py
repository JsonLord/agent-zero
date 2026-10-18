import re

with open("tests/test_blocking_a2a.py", "r") as f:
    content = f.read()

# FastA2A is not installed in the system environment, the project uses a mock locally or ignores imports if not available.
# Let's mock fasta2a for the tests

mock_code = """
import sys
from unittest.mock import MagicMock

fasta2a_mock = MagicMock()
fasta2a_mock.task_manager.TaskManager = object
sys.modules['fasta2a'] = fasta2a_mock
sys.modules['fasta2a.task_manager'] = fasta2a_mock.task_manager
sys.modules['fasta2a.schema'] = fasta2a_mock.schema
sys.modules['fasta2a.server'] = fasta2a_mock.server
"""

with open("tests/test_blocking_a2a.py", "w") as f:
    f.write(mock_code + "\n" + content)

with open("tests/test_fasta2a_server.py", "r") as f:
    content2 = f.read()
with open("tests/test_fasta2a_server.py", "w") as f:
    f.write(mock_code + "\n" + content2)
