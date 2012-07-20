from django.core.management.base import BaseCommand

from linz2osm.data_dict.models import Dataset

class Command(BaseCommand):
    help = "Populates the datasets and dataset-to-layer mappings from the databases configured in your settings_site.py file"

    def handle(self, **options):
        Dataset.objects.generate_datasets()
        print "%d datasets" % Dataset.objects.count()
