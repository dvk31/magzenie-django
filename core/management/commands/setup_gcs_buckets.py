from django.core.management.base import BaseCommand, CommandError
from google.cloud import storage
from google.cloud.storage import Bucket, Client

class Command(BaseCommand):
    help = 'Sets up Google Cloud Storage buckets for different access levels'

    def handle(self, *args, **options):
        try:
            client = storage.Client()

            buckets_info = {
                'tryoutbot-public-bucket': 'publicRead',
                'tryoutbot-authenticated-bucket': None,  # No predefined ACLs; use signed URLs
                'tryoutbot-private-bucket': None  # No predefined ACLs; manage access programmatically
                
            }

            for bucket_name, acl in buckets_info.items():
                self.create_bucket(client, bucket_name, acl)

                self.stdout.write(self.style.SUCCESS(f'Successfully configured bucket: {bucket_name}'))

        except Exception as e:
            raise CommandError(f'Error setting up GCS buckets: {str(e)}')


    def create_bucket(self, client: Client, bucket_name: str, acl_type: str = None) -> Bucket:
        """Creates a GCS bucket if it does not exist and sets the ACL based on the type."""
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            bucket.create(location='US')
            self.stdout.write(self.style.SUCCESS(f'Bucket created: {bucket_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Bucket already exists: {bucket_name}'))

        # Apply ACL if specified
        if acl_type == 'publicRead':
            bucket.acl.reload()
            bucket.acl.all().grant_read()
            bucket.acl.save()
            self.stdout.write(self.style.SUCCESS(f'Public read access granted to bucket: {bucket_name}'))
        elif acl_type is None:
            # No ACL modification: control access through your application logic
            self.stdout.write(self.style.SUCCESS(f'Access to bucket {bucket_name} will be managed programmatically.'))

        return bucket