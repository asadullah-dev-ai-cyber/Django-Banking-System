from django.urls import path

from . import views


urlpatterns = [

    # ================= DASHBOARD =================

    path('', views.dashboard_view, name='dashboard'),

    # ================= CUSTOMER ROUTES =================

    path('customers/', views.customers_list_view, name='customer_list'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/api/create/', views.add_customer, name='create_customer'),
    path(
        'customers/<int:customer_id>/',
        views.customer_detail_view,
        name='customer_detail'
    ),

    # ================= ACCOUNT ROUTES =================

    path('accounts/', views.accounts_list_view, name='account_list'),
    path('accounts/add/', views.add_account, name='add_account'),
    path('accounts/api/create/', views.add_account, name='create_account'),
    path(
        'accounts/<int:account_id>/',
        views.account_detail_view,
        name='account_detail'
    ),
    path(
        'accounts/api/<int:account_id>/',
        views.get_account_detail,
        name='get_account_detail_api'
    ),

    # ================= TRANSFER ROUTES =================

    path('transfers/', views.transfers_list_view, name='transfer_list'),
    path('transfers/new/', views.transfer_form_view, name='transfer_create'),
    path('transfers/process/', views.transfer_funds, name='transfer_funds'),
    path(
        'api/transfers/process/',
        views.transfer_funds,
        name='api_transfer_funds'
    ),
]