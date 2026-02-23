"""
SQLAdmin configuration for database administration UI

Access the admin panel at: http://localhost:8000/admin
"""

from db import Dog
from sqladmin import Admin, ModelView
from sqlalchemy import create_engine

# Create sync engine for SQLAdmin (it requires a sync engine internally)
DATABASE_URL = "postgresql://user:password@localhost:5432/ai-quickstart-template"
engine = create_engine(DATABASE_URL, echo=False)


class DogAdmin(ModelView, model=Dog):
    """
    Example admin view - feel free to delete this when you remove the Dog model.

    This demonstrates:
    - column_list: Which columns to show in the list view
    - column_searchable_list: Which columns can be searched
    - column_sortable_list: Which columns can be sorted
    - column_default_sort: Default sort order
    """
    column_list = [Dog.id, Dog.name, Dog.breed, Dog.age, Dog.created_at]
    column_searchable_list = [Dog.name, Dog.breed]
    column_sortable_list = [Dog.id, Dog.name, Dog.breed, Dog.age]
    column_default_sort = [(Dog.created_at, True)]
    name = "Dog"
    name_plural = "Dogs"
    icon = "fa-solid fa-dog"


def setup_admin(app):
    """
    Set up SQLAdmin and mount it to the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    admin = Admin(app, engine, title="AI QuickStart Admin")

    # Example model - delete this when you remove the Dog model
    admin.add_view(DogAdmin)

    # Register your model admins here:
    #
    # class YourModelAdmin(ModelView, model=YourModel):
    #     column_list = [YourModel.id, YourModel.name]
    #
    # admin.add_view(YourModelAdmin)

    return admin
