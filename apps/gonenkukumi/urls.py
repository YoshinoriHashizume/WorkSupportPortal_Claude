from django.urls import path

from . import views

app_name = "gonenkukumi"

urlpatterns = [
    path("app/production/five-year-nine", views.search_page, name="search_page"),
    path("app/production/five-year-nine/result", views.result_page, name="result_page"),
    path("api/gonenkukumi/search", views.api_search, name="api_search"),
    path("api/gonenkukumi/customers", views.api_customers, name="api_customers"),
    path("api/gonenkukumi/history", views.api_history, name="api_history"),
    path("api/gonenkukumi/oracle-result", views.api_oracle_result, name="api_oracle_result"),
    path("api/gonenkukumi/cust-items", views.api_cust_items, name="api_cust_items"),
    path("api/gonenkukumi/export", views.api_export, name="api_export"),
]
