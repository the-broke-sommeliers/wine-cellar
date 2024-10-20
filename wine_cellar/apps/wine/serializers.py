from rest_framework import serializers

from wine_cellar.apps.wine.models import Wine


class WineSerializer(serializers.ModelSerializer):
    grapes = serializers.StringRelatedField(many=True)
    region = serializers.StringRelatedField()
    vineyard = serializers.StringRelatedField()
    food_pairings = serializers.StringRelatedField(many=True)
    source = serializers.StringRelatedField(many=True)
    classification = serializers.StringRelatedField(many=True)
    vintage = serializers.StringRelatedField(many=True)

    class Meta:
        model = Wine
        fields = [
            "name",
            "wine_type",
            "grapes",
            "abv",
            "capacity",
            "vintage",
            "classification",
            "food_pairings",
            "source",
            "region",
            "vineyard",
        ]
