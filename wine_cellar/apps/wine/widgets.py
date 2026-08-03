from django.core.exceptions import ImproperlyConfigured
from django.forms import ClearableFileInput, Media
from django.forms.widgets import Widget
from django.template import loader
from webpack_loader.utils import get_files


class NoFilenameClearableFileInput(ClearableFileInput):
    template_name = "widgets/clearable_file_input_no_filename.html"


class MapChoosePointWidget(Widget):
    geo_json_properties = {}
    bundle_name = "react_choose_point"

    def __init__(self, polygon, attrs=None):
        self.polygon = polygon
        super().__init__(attrs)

    @property
    def media(self):
        return Media(
            js=[f["name"] for f in get_files(self.bundle_name, extension="js")],
            css={
                "all": [f["name"] for f in get_files(self.bundle_name, extension="css")]
            },
        )

    def render(self, name, value, attrs, renderer=None):
        if not get_files(self.bundle_name, extension="js"):
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
