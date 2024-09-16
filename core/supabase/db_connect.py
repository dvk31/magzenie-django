# db_connection.py
# db_connect.py

import logging
from django.db import connection

from django.conf import settings
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self):
        self.conn = None

    def get_connection(self):
        if not self.conn or self.conn.closed:
            try:
                self.conn = connections['default']
                logger.info(f"Successfully connected to database")
            except Exception as e:
                logger.error(f"Failed to connect to database: {str(e)}")
                raise
        return self.conn




class DatabaseConnection:
    @staticmethod
    def execute_query(query, params=None):
        try:
            with connection.cursor() as cursor:
                logger.info(f"Executing query: {query}")
                if params:
                    logger.info(f"Query parameters: {params}")
                cursor.execute(query, params)
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                logger.info("Query executed successfully")
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            logger.error(f"Query: {query}")
            raise
        return None

    def close_connection(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")