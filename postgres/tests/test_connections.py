# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


def test_connection_settings_defaults(integration_check, pg_instance):
    """
    Tests the default session settings are properly configured for all new connections made by the datadog user
    to the database.
    """
    check = integration_check(pg_instance)

    with check._new_connection("postgres") as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, setting FROM pg_settings")
            settings = cursor.fetchall()
            settings = {name: value for name, value in settings}

            assert 'statement_timeout' in settings
            assert settings['statement_timeout'] == str(check._config.query_timeout) != 0

            assert 'idle_in_transaction_session_timeout' in settings
            assert (
                settings['idle_in_transaction_session_timeout']
                == str(check._config.idle_in_transaction_session_timeout)
                != 0
            )
