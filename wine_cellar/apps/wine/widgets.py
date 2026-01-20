from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.forms import ClearableFileInput
from django.forms.widgets import Widget
from django.template import loader


class NoFilenameClearableFileInput(ClearableFileInput):
    template_name = "widgets/clearable_file_input_no_filename.html"


class MapChoosePointWidget(Widget):
    geo_json_properties = {}

    def __init__(self, polygon, attrs=None):
        self.polygon = polygon
        super().__init__(attrs)

    class Media:
        js = ("react_choose_point.js",)

        css = {"all": ["react_choose_point.css"]}

    def render(self, name, value, attrs, renderer=None):
        if not finders.find("react_choose_point.js"):
            raise ImproperlyConfigured(
                "Configure your frontend build tool to generate react_choose_point.js."
            )

        context = {
            "name": name,
            "polygon": self.polygon,
        }

        if value != "null" and value:
            point = value
            context["point"] = point

        return loader.render_to_string("widgets/map_choose_point_widget.html", context)
