import calendar
from datetime import date, datetime


def date_to_epoch(d):
    return int(calendar.timegm(d.timetuple()) * 1000000)


def year_transform(connection, value):
    value = connection.ops.value_from_db_date(value)
    return date_to_epoch(date(value.year, 1, 1)) if value else None


def month_transform(connection, value):
    value = connection.ops.value_from_db_date(value)
    return date_to_epoch(date(value.year, value.month, 1)) if value else None


def day_transform(connection, value):
    value = connection.ops.value_from_db_date(value)
    return date_to_epoch(value) if value else None


def hour_transform(connection, value):
    value = connection.ops.value_from_db_datetime(value)
    return date_to_epoch(
        datetime(
            value.year, value.month, value.day,
            value.hour, 1, 1
        )
    )


def minute_transform(connection, value):
    value = connection.ops.value_from_db_datetime(value)
    return date_to_epoch(
        datetime(
            value.year, value.month, value.day,
            value.hour, value.minute, 1
        )
    )


def second_transform(connection, value):
    value = connection.ops.value_from_db_datetime(value)
    return date_to_epoch(
        datetime(
            value.year, value.month, value.day,
            value.hour, value.minute, value.second
        )
    )