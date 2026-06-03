from src.services.snooze_handler import parse_snooze_command

def test_parse_cancel():
    cmd = parse_snooze_command("отмена")
    assert cmd == {'action': 'cancel'}

def test_parse_tomorrow():
    cmd = parse_snooze_command("завтра")
    assert cmd == {'action': 'tomorrow'}

def test_parse_minutes():
    cmd = parse_snooze_command("+10")
    assert cmd == {'action': 'minutes', 'value': 10}
    cmd = parse_snooze_command("+60")
    assert cmd == {'action': 'minutes', 'value': 60}

def test_parse_hours():
    cmd = parse_snooze_command("+1ч")
    assert cmd == {'action': 'hours', 'value': 1}
    cmd = parse_snooze_command("+5ч")
    assert cmd == {'action': 'hours', 'value': 5}

def test_invalid_command():
    assert parse_snooze_command("привет") is None
    assert parse_snooze_command("+10часов") is None
    assert parse_snooze_command("отмена123") is None