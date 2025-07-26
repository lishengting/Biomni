#!/usr/bin/env python3
"""
Test script to verify the logging functionality for network requests.
"""

import logging
from biomni.tool.database import set_debug_mode, _query_rest_api
from biomni.tool.literature import set_debug_mode as set_literature_debug_mode
from biomni.utils import set_debug_mode as set_utils_debug_mode, execute_graphql_query

def test_debug_mode():
    """Test the debug mode functionality."""
    print("Testing debug mode functionality...")
    
    # Enable debug mode for all modules
    set_debug_mode(True)
    set_literature_debug_mode(True)
    set_utils_debug_mode(True)
    
    print("Debug mode enabled for all modules.")
    
    # Test a simple REST API call
    print("\nTesting REST API call...")
    try:
        result = _query_rest_api(
            endpoint="https://httpbin.org/get",
            method="GET",
            description="Test request to httpbin.org"
        )
        print(f"REST API call result: {result['success']}")
    except Exception as e:
        print(f"Error in REST API call: {e}")
    
    # Test GraphQL query (this might fail if the service is not available, which is expected)
    print("\nTesting GraphQL query...")
    try:
        result = execute_graphql_query(
            query="{ meta { name } }",
            variables={},
            api_address="https://api.genetics.opentargets.org/graphql"
        )
        print(f"GraphQL query result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    except Exception as e:
        print(f"Expected error in GraphQL query (service may be unavailable): {e}")
    
    # Disable debug mode
    set_debug_mode(False)
    set_literature_debug_mode(False)
    set_utils_debug_mode(False)
    
    print("\nDebug mode disabled.")
    print("Test completed.")

if __name__ == "__main__":
    # Configure basic logging to see the debug output
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    test_debug_mode()