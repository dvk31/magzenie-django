from django.core.management.base import BaseCommand
from server.utils.kube_utils import KubernetesUtility


class Command(BaseCommand):
    help = "Installs tmux in a specified Kubernetes pod"

    def add_arguments(self, parser):
        parser.add_argument(
            "pod_name",
            type=str,
            help="Name of the pod where tmux should be installed",
        )

    def handle(self, *args, **options):
        pod_name = options["pod_name"]
        kube_util = KubernetesUtility()

        # Fetch the pod's details
        pod_details = kube_util.get_pod(pod_name)

        if not pod_details:
            self.stderr.write(f"Unable to retrieve details for pod {pod_name}.")
            return

        # Display the base image of the pod
        try:
            container_image = pod_details.spec.containers[0].image
            self.stdout.write(f"Base image of pod {pod_name}: {container_image}")
        except (AttributeError, IndexError):
            self.stderr.write(f"Unable to determine the base image of pod {pod_name}.")
            return

        # Check if the base image is Debian or Ubuntu based
        if (
            "debian" not in container_image.lower()
            and "ubuntu" not in container_image.lower()
        ):
            self.stderr.write(
                f"Pod {pod_name} does not seem to have a Debian or Ubuntu based image. Installation might fail."
            )
            # You might want to return here or proceed with a warning

        # Proceed with tmux installation
        install_command = "apt-get update && apt-get install -y tmux"
        output = kube_util.execute_command(pod_name, install_command)

        if output:
            if "E: " in output:  # 'E: ' often indicates an error in apt-get
                self.stderr.write(f"Error during installation:\n{output}")
            else:
                self.stdout.write(f"tmux installation output:\n{output}")
        else:
            self.stderr.write(
                f"Failed to capture output from the command: {install_command} in pod: {pod_name}"
            )
