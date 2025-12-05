from django.forms import ClearableFileInput


class NoFilenameClearableFileInput(ClearableFileInput):
    template_name = "widgets/clearable_file_input_no_filename.html"
