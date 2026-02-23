"""
Test helper functions
"""


def find_service(services: list, name: str) -> dict | None:
    """Find a service by name in health check response.

    Args:
        services: List of service dicts from health endpoint
        name: Service name to find (e.g., "API", "Database")

    Returns:
        Service dict if found, None otherwise
    """
    return next((s for s in services if s["name"] == name), None)


def assert_service_exists(services: list, name: str) -> dict:
    """Assert a service exists and return it.

    Args:
        services: List of service dicts from health endpoint
        name: Service name to find

    Returns:
        Service dict

    Raises:
        AssertionError: If service not found
    """
    service = find_service(services, name)
    assert service is not None, f"Service '{name}' not found in response"
    return service
