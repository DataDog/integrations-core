# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
This is a standalone test module for debugging XE session collection.
Not intended for production use.
"""

import json
from datadog_checks.sqlserver.xe_sessions.registry import get_xe_session_handlers

def test_xe_sessions(check):
    """Test XE session collection with a given check instance"""
    try:
        from datadog_checks.sqlserver.config import SQLServerConfig

        # Create dummy config for testing
        config = SQLServerConfig(check.instance)

        # Get handlers
        handlers = get_xe_session_handlers(check, config)

        results = {}

        # Test each handler
        for handler in handlers:
            handler_result = {
                "session_name": handler.session_name,
                "exists": False,
                "has_data": False,
                "events": []
            }

            # Check if session exists
            try:
                exists = handler.session_exists()
                handler_result["exists"] = exists
                check.log.info(f"XE Session {handler.session_name}: {'EXISTS' if exists else 'DOES NOT EXIST'}")

                if exists:
                    # Query ring buffer
                    xml_data = handler._query_ring_buffer()
                    handler_result["has_data"] = xml_data is not None

                    if xml_data:
                        # Process events
                        check.log.info(f"Found data in ring buffer for {handler.session_name}")
                        events = handler._process_events(xml_data)
                        handler_result["event_count"] = len(events)
                        check.log.info(f"Processed {len(events)} events from {handler.session_name}")
                        
                        # Include a few sample events
                        max_sample_events = 3
                        sample_events = []
                        for i, event in enumerate(events[:max_sample_events]):
                            # Format events for better readability
                            formatted_event = handler._format_event_for_log(event)
                            sample_events.append(formatted_event)

                        handler_result["events"] = sample_events

                        if sample_events:
                            check.log.info(f"Sample events from {handler.session_name}:\n{json.dumps(sample_events, indent=2, default=str)}")
                    else:
                        check.log.info(f"No data found in ring buffer for {handler.session_name}")
            except Exception as e:
                error_msg = f"Error testing {handler.session_name}: {str(e)}"
                check.log.error(error_msg)
                handler_result["error"] = error_msg

            results[handler.session_name] = handler_result

        check.log.info("XE Session test summary:")
        for session_name, result in results.items():
            status = "✓" if result["exists"] else "✗"
            event_count = result.get("event_count", 0)
            check.log.info(f"  {status} {session_name}: {event_count} events")

        return results
    except Exception as e:
        error_msg = f"Error in test_xe_sessions: {str(e)}"
        check.log.error(error_msg)
        return {"error": error_msg}


def run_standalone_test(host, username, password, database="master"):
    """Run a standalone test with the given connection parameters"""
    try:
        from datadog_checks.sqlserver.sqlserver import SQLServer

        # Sample instance configuration
        instance = {
            'host': host,
            'username': username,
            'password': password,
            'database': database
        }

        # Create a check instance
        check = SQLServer('sqlserver', {}, [instance])

        # Run check once to initialize connections
        check.check(None)

        # Test XE sessions
        results = test_xe_sessions(check)

        # Print results
        print(json.dumps(results, indent=2, default=str))

        return results
    except Exception as e:
        print(f"Error in run_standalone_test: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    # This can be run directly for testing
    # Default values - change these for your environment
    host = "localhost"
    username = "datadog"
    password = "password"
    database = "master"

    # For command line arguments
    import sys
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        username = sys.argv[2]
    if len(sys.argv) > 3:
        password = sys.argv[3]
    if len(sys.argv) > 4:
        database = sys.argv[4]

    print(f"Testing XE sessions on {host} with user {username}")
    run_standalone_test(host, username, password, database) 