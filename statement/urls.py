"""Url for statement"""

from django.urls import path
from . import views

urlpatterns = [
    path(route="", view=views.starting_page, name="starting-page"),
    path(route="upload/", view=views.upload_file, name="upload-file"),
    path(route="no-statement/", view=views.no_statement, name="no-statement"),
    path(route="bank-statement/", view=views.bank_statement, name="bank-statement"),
    path(route="help/", view=views.generate_app_password, name="help"),
]
