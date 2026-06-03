from src.services.notification_filter import get_events_in_group, compose_group_message

def test_get_events_in_group(db_session, sample_events, sample_user, sample_settings):
    """
    Тест: в группу должны попасть события, начинающиеся в пределах 2 часов от первого события.
    """
    first_event = sample_events[0]  # начало через 2 часа
    group = get_events_in_group(db_session, first_event, sample_settings.grouping_window)
    # Ожидаем, что в группе будут события 0,1 (начинаются в интервале [2ч, 4ч)), но не 2,3 (начинаются через 5ч)
    assert len(group) == 2
    assert first_event in group
    assert sample_events[1] in group
    assert sample_events[2] not in group
    assert sample_events[3] not in group

def test_compose_group_message(sample_events):
    """
    Проверка форматирования сводного сообщения.
    """
    events = [sample_events[0], sample_events[1]]
    msg = compose_group_message(events)
    assert "У вас несколько событий" in msg
    assert "Встреча с врачом" in msg
    assert "Срочный созвон" in msg
    # проверка наличия времени
    assert sample_events[0].start_time.strftime('%H:%M') in msg
    assert sample_events[1].start_time.strftime('%H:%M') in msg