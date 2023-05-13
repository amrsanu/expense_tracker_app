"""Url for statement"""

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path(route="", view=views.starting_page, name="starting-page"),
    path(route="upload/", view=views.upload_file, name="upload-file"),
    path(route="no-statement/", view=views.no_statement, name="no-statement"),
    path(route="bank-statement/", view=views.bank_statement, name="bank-statement"),
    path(route="help/", view=views.help_page, name="help"),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
