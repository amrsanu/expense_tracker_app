"""To create a form
Take statement input from user"""

from django import forms


class UploadFileForm(forms.Form):
    """Class to create form object"""

    file = forms.FileField()
