import pytest

from core.execution_safety import exclusive_runtime


def test_runtime_lock_rejects_second_owner_and_releases(tmp_path):
    lock_path = str(tmp_path / 'trader.lock')
    with exclusive_runtime(lock_path):
        with pytest.raises(RuntimeError, match='Another trader owns'):
            with exclusive_runtime(lock_path):
                pass

    with exclusive_runtime(lock_path):
        pass
