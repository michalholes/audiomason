import pytest
from audiomason.verify import READ_ONLY_VERIFY

def test_verify_is_read_only():
    assert READ_ONLY_VERIFY is True
