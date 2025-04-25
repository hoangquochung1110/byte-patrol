import pytest
from byte_patrol.main import main

def test_main_runs(capsys):
    main()
    captured = capsys.readouterr()
    assert "Byte Patrol starting..." in captured.out
