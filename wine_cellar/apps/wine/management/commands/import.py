from django.core.management.base import BaseCommand, CommandError

from wine_cellar.apps.wine.models import Wine, Region, Winery, Grape


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str)

    def handle(self, *args, **options):
        import csv

        with open(options['file']) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',', quotechar='"', skipinitialspace=True)

            for row in reader:
                region, _ = Region.objects.get_or_create(region_id=row["RegionID"], name=row["RegionName"])
                winery, _ = Winery.objects.get_or_create(winery_id=row["WineryID"], name=row["WineryName"], website=row["Website"], region=region)
                for vintage in row["Vintages"].strip("[]").split(", "):
                    wine = Wine.objects.create(
                        wine_id=row["WineID"],
                        name=row["WineName"],
                        wine_type=row["Type"],
                        elaborate=row["Elaborate"],
                        food_pairing=row["Harmonize"],
                        abv=float(row["ABV"]),
                        body=row["Body"],
                        acidity=row["Acidity"],
                        region=region,
                        winery=winery
                    )
                    if vintage != "'N.V.'":
                        wine.vintage = vintage
                    wine.save()

                    for grape in row["Grapes"].strip("[]").split(", "):
                        grape_obj, _ = Grape.objects.get_or_create(name=grape)
                        wine.grapes.add(grape_obj)



