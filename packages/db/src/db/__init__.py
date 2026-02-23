__version__ = "0.0.0"

# Export main database classes and functions
from .database import DatabaseService, get_db_service, get_db, Base
from .models import Dog

__all__ = ["DatabaseService", "get_db_service", "get_db", "Base", "Dog", "__version__"]
