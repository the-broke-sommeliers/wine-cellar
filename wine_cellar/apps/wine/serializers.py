from rest_framework import serializers

from wine_cellar.apps.wine.models import Wine


class WineSerializer(serializers.ModelSerializer):
    grapes = serializers.StringRelatedField(many=True)
    region = serializers.StringRelatedField()
    winery = serializers.StringRelatedField()
    food_pairings = serializers.StringRelatedField(many=True)
    classification = serializers.StringRelatedField(many=True)
    vintage = serializers.StringRelatedField(many=True)

    class Meta:
        model = Wine
        fields = [
            "name",
            "wine_type",
            "elaborate",
            "grapes",
            "body",
            "acidity",
            "abv",
            "capacity",
            "vintage",
            "classification",
            "food_pairings",
            "region",
            "winery",
        ]
