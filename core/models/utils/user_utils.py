import logging
from django.utils import timezone
from system_agents.models import (
    Role,
    UserRole,
    DataBase,
    Record,
    Platform,
    Table,
    Parameter,
)
from django.contrib.auth import get_user_model


from django.db import transaction

from django.core.exceptions import ObjectDoesNotExist

# Set up logging
logger = logging.getLogger(__name__)

User = get_user_model()


@transaction.atomic
def assign_role_to_new_user(user, role_name=None):
    """
    Assigns a specified role to a user, or a default global role if no role is specified.

    Parameters:
    - user: The user to whom the role will be assigned
    - role_name: The name of the role to assign (optional)
    """
    try:
        if role_name:
            role = Role.objects.get(name=role_name)
        else:
            role = Role.objects.get(name="Default Global Role", is_global=True)

        UserRole.objects.create(user=user, role=role)
    except ObjectDoesNotExist:
        # Handle the case where the role does not exist
        raise Exception("The specified role does not exist.")


@transaction.atomic
def create_platform(user: User, name: str) -> Platform:
    """
    Creates a Platform instance for a given user.
    """
    try:
        platform = Platform.objects.create(name=name, owner=user)
        logger.info(f"Successfully created Platform {name} for user {user.username}")
        return platform
    except Exception as e:
        logger.error(f"Failed to create Platform for user {user.username}: {str(e)}")
        raise


@transaction.atomic
def create_user_agent_database(user: User, platform: Platform) -> DataBase:
    """
    Creates a private database for a UserAgent inside a Platform.
    The name of the database is set as "<username's> database".
    """
    db_name = f"{user.username}'s database"
    try:
        database = DataBase.objects.create(
            name=db_name, platform=platform, agent=user.user_agent
        )
        logger.info(f"Successfully created Database {db_name} for User {user.username}")
        return database
    except Exception as e:
        logger.error(f"Failed to create Database for User {user.username}: {str(e)}")
        raise


@transaction.atomic
def create_table_for_useragent_database(
    database: DataBase, user: User, fields: dict
) -> Table:
    """
    Creates a user-specific table inside the UserAgent's database.
    This table will store records related to that particular user.

    Parameters:
    - fields: A dictionary where keys are field names and values are data types (e.g., {'name': 'string', 'age': 'int'})
    """
    table_name = f"User_{user.id}_Table"
    try:
        table = Table.objects.create(
            name=table_name,
            database=database,
            agent=database.agent,
            description=f"User Specific Table for User {user.username}",
        )
        logger.info(
            f"Successfully created User Specific Table {table_name} for User {user.username}"
        )

        # Create Parameter instances for each field in the table
        for field_name, data_type in fields.items():
            Parameter.objects.create(
                name=field_name,
                type=data_type,
                agent=database.agent,
                action=None,
                group=None,
                record=None,
                data_endpoint=None,
            )

        return table

    except Exception as e:
        logger.error(
            f"Failed to create User Specific Table for User {user.username}: {str(e)}"
        )
        raise


@transaction.atomic
def create_record_for_useragent_table(
    table: Table, data: dict, metadata: dict = None
) -> Record:
    """
    Creates a new Record instance associated with a specific user-specific table.

    Parameters:
    - data: A dictionary containing the data to be stored in the Record.
    """
    try:
        # Validate that the keys in the data dictionary match the Parameters defined for the table
        parameters = Parameter.objects.filter(agent=table.agent)
        valid_fields = {param.name for param in parameters}
        data_fields = set(data.keys())

        if data_fields != valid_fields:
            raise Exception(
                "Data fields do not match the defined Parameters for this table."
            )

        # Create a new Record instance associated with the table's database
        record = Record.objects.create(
            storage=table.database, data=data, metadata=metadata
        )
        logger.info(f"Successfully created Record for Table {table.name}")

        return record

    except Exception as e:
        logger.error(f"Failed to create Record for Table {table.name}: {str(e)}")
        raise


@transaction.atomic
def create_system_table_for_platform(database: DataBase, platform_id: int) -> Table:
    """
    Creates a System Table inside the given Database.
    This table will store records that map User IDs to external Platform IDs.

    Parameters:
    - database: The Database instance where this System Table will be created.
    - platform_id: The ID of the external Platform that users might join.
    """
    table_name = f"System_Table_for_Platform_{platform_id}"
    system_fields = {
        "user_id": "int",  # To store the User ID from the User model
        "platform_id": "int",  # To store the ID of the external Platform
        "metadata": "json",  # To store additional info (e.g., join date, roles, etc.)
    }

    try:
        # Creating the System Table
        system_table = Table.objects.create(
            name=table_name,
            database=database,
            agent=database.agent,
            description=f"System Table for Platform {platform_id}",
        )
        logger.info(f"Successfully created System Table {table_name}")

        # Create Parameter instances for each field in the table
        for field_name, data_type in system_fields.items():
            Parameter.objects.create(
                name=field_name,
                type=data_type,
                agent=database.agent,
                action=None,
                group=None,
                record=None,
                data_endpoint=None,
            )

        return system_table

    except Exception as e:
        logger.error(
            f"Failed to create System Table for Platform {platform_id}: {str(e)}"
        )
        raise


@transaction.atomic
def add_user_to_platform(
    system_table: Table, user_id: int, platform_id: int, metadata: dict = None
) -> Record:
    """
    Adds a new record to the System Table when a user joins an external Platform.

    Parameters:
    - system_table: The System Table instance where this record will be stored.
    - user_id: The User ID from the User model.
    - platform_id: The ID of the external Platform that the user is joining.
    - metadata: A dictionary containing additional metadata or context about the user joining the platform (optional).
    """

    # Record data
    record_data = {"user_id": user_id, "platform_id": platform_id, "metadata": metadata}

    # Storing a parameterized record for the user joining the platform
    platform_record = create_record_for_useragent_table(system_table, data=record_data)

    return platform_record
