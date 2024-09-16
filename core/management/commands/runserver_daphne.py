# management/commands/runserver_daphne.py
from django.core.management.base import BaseCommand
from django.core.servers.basehttp import run
from daphne.server import Server
from daphne.endpoints import build_endpoint_description_strings

class Command(BaseCommand):
    help = 'Runs the server with Daphne, with auto-reload capability'

    def handle(self, *args, **options):
        run(self.inner_run, addrport='127.0.0.1:8000', use_reloader=True, use_threading=False)

    def inner_run(self, *args, **options):
        endpoints = build_endpoint_description_strings(['127.0.0.1:8000'])
        Server(application=self.get_application(), endpoints=endpoints).run()

    def get_application(self):
        from hellogpt.asgi import application
        return application