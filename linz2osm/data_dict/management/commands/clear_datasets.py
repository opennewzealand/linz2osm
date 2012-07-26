from django.core.management.base import BaseCommand

from linz2osm.data_dict.models import Dataset

class Command(BaseCommand):
    help = "Clears the datasets and dataset-to-layer mappings."

    def handle(self, **options):
        Dataset.objects.clear_datasets()
