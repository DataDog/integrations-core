# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
This is a standalone test module for debugging XE session collection.
Not intended for production use.
"""

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
                
                if exists:
                    # Query ring buffer
                    xml_data = handler._query_ring_buffer()
                    handler_result["has_data"] = xml_data is not None
                    
                    if xml_data:
                        # Process events
                        events = handler._process_events(xml_data)
                        handler_result["event_count"] = len(events)
                        
                        # Include a few sample events
                        max_sample_events = 3
                        handler_result["events"] = events[:max_sample_events] if events else []
            except Exception as e:
                handler_result["error"] = str(e)
            
            results[handler.session_name] = handler_result
        
        return results
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # This can be run directly for testing
    from datadog_checks.sqlserver.sqlserver import SQLServer
    
    # Sample instance configuration
    instance = {
        'host': 'localhost',
        'username': 'datadog',
        'password': 'password',
        'database': 'master'
    }
    
    # Create a check instance
    check = SQLServer('sqlserver', {}, [instance])
    
    # Run check once to initialize connections
    check.check(None)
    
    # Test XE sessions
    results = test_xe_sessions(check)
    
    # Print results
    import json
    print(json.dumps(results, indent=2)) 