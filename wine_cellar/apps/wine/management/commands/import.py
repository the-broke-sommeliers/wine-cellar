from django.core.management.base import BaseCommand

from wine_cellar.apps.wine.models import (
    FoodPairing,
    Grape,
    Region,
    Vintage,
    Wine,
    Winery,
)


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str)

    def handle(self, *args, **options):
        import csv

        with open(options["file"]) as csvfile:
            reader = csv.DictReader(
                csvfile, delimiter=",", quotechar='"', skipinitialspace=True
            )

            regions = []
            regions_by_id = {}
            grapes = []
            grapes_per_wine = {}
            food_pairings = []
            food_pairings_per_wine = {}
            vintages = []
            vintages_per_wine = {}
            wineries = []
            wineries_by_id = {}
            wines = []
            i = 0
            for row in reader:
                wine_id = row["WineID"]
                region = Region(
                    region_id=row["RegionID"],
                    name=row["RegionName"],
                    country=row["Country"],
                )
                regions_by_id[wine_id] = region
                regions.append(region)
                winery = Winery(
                    winery_id=row["WineryID"],
                    name=row["WineryName"],
                    website=row["Website"],
                )
                wineries.append(winery)
                v_buf = []
                for vintage in row["Vintages"].strip("[]").split(", "):
                    vintage = vintage.strip("'")
                    if vintage == "N.V.":
                        print("vintage_nv")
                        continue
                    vintage_obj = Vintage(name=vintage)
                    v_buf.append(vintage_obj)
                vintages_per_wine[row["WineID"]] = v_buf
                vintages = vintages + v_buf

                food_pairings_buf = []
                for pairing in row["Harmonize"].strip("[]").split(", "):
                    pairing = pairing.strip("'")
                    if pairing == "N.V.":
                        print("pairing_nv")
                        continue
                    pairing_obj = FoodPairing(name=pairing)
                    food_pairings_buf.append(pairing_obj)
                food_pairings_per_wine[wine_id] = food_pairings_buf
                food_pairings = food_pairings + food_pairings_buf

                wine = Wine(
                    wine_id=row["WineID"],
                    name=row["WineName"],
                    wine_type=row["Type"],
                    elaborate=row["Elaborate"],
                    abv=float(row["ABV"]),
                    body=row["Body"],
                    acidity=row["Acidity"],
                )
                wines.append(wine)

                grape_buf = []
                for grape in row["Grapes"].strip("[]").split(", "):
                    grape = grape.strip("'")
                    if grape == "N.V.":
                        print("grape_nv")
                        continue
                    grape_obj = Grape(name=grape)
                    grape_buf.append(grape_obj)
                grapes_per_wine[wine_id] = grape_buf
                grapes = grapes + grape_buf
                i += 1
            Region.objects.bulk_create(regions, ignore_conflicts=True)
            Grape.objects.bulk_create(grapes, ignore_conflicts=True)
            Vintage.objects.bulk_create(vintages, ignore_conflicts=True)
            FoodPairing.objects.bulk_create(food_pairings, ignore_conflicts=True)
            Winery.objects.bulk_create(wineries, ignore_conflicts=True)
            Wine.objects.bulk_create(wines, ignore_conflicts=True)
            wines_update = []
            for wine in Wine.objects.all():
                w_id = str(wine.wine_id)
                region = regions_by_id.get(w_id, None)
                winery = wineries_by_id.get(w_id, None)
                pairing = food_pairings_per_wine.get(w_id, None)
                vintage = vintages_per_wine.get(w_id, None)
                grape = grapes_per_wine.get(w_id, None)
                if pairing:
                    p = FoodPairing.objects.filter(name__in=[o.name for o in pairing])
                    wine.food_pairings.add(*p)
                if vintage:
                    v = Vintage.objects.filter(name__in=[o.name for o in vintage])
                    wine.vintage.add(*v)
                if grape:
                    g = Grape.objects.filter(name__in=[g.name for g in grape])
                    wine.grapes.add(*g)
                w = None
                r = None
                if winery:
                    w = Winery.objects.get(
                        winery_id=winery.winery_id,
                    )
                if region:
                    r = Region.objects.get(region_id=region.region_id)
                if r:
                    if w:
                        winery.region = r
                    wine.region = r
                if w:
                    wine.winery = w
                wines_update.append(wine)
            Wine.objects.bulk_update(wines_update, ["region", "winery"])

            self.stdout.write(self.style.SUCCESS('Wines added: "%s"\n' % i))
