from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = 'Drops the test database if it exists and ensures no other connections are active.'

    def handle(self, *args, **kwargs):
        db_name = 'test_postgres'
        connection = connections['default']

        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{db_name}'
                    AND pid <> pg_backend_pid();
                """)
                self.stdout.write(self.style.SUCCESS(f'Terminated all other connections to {db_name}.'))

                cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
                self.stdout.write(self.style.SUCCESS(f'Dropped test database {db_name}.'))

        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'Error dropping test database: {e}'))