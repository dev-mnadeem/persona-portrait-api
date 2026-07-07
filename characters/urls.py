from django.urls import path

from characters import views

app_name = "characters"

urlpatterns = [
    path("", views.CharacterListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", views.CharacterDetailView.as_view(), name="detail"),
]
