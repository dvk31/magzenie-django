from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Identifies and optionally removes orphaned ProductVideo records'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Identify orphaned records
            cursor.execute("""
                SELECT pv.id, pv.product_id 
                FROM platform_vendor_productvideo pv
                LEFT JOIN platform_vendor_product p ON pv.product_id = p.id
                WHERE p.id IS NULL
            """)
            orphaned_records = cursor.fetchall()

            self.stdout.write(f"Found {len(orphaned_records)} orphaned ProductVideo records.")

            if orphaned_records:
                confirm = input("Do you want to delete these orphaned records? (yes/no): ")
                if confirm.lower() == 'yes':
                    orphaned_ids = [record[0] for record in orphaned_records]
                    placeholders = ','.join(['%s'] * len(orphaned_ids))
                    cursor.execute(f"DELETE FROM platform_vendor_productvideo WHERE id IN ({placeholders})", orphaned_ids)
                    self.stdout.write(self.style.SUCCESS(f"Deleted {cursor.rowcount} orphaned records."))
                else:
                    self.stdout.write("No records deleted.")
            else:
                self.stdout.write("No orphaned records found.")