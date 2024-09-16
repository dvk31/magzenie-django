from django.contrib.sites.models import Site
new_site = Site.objects.create(domain='humanai.me', name='humanai.me')