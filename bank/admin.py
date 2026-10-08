from django.contrib import admin
from .models import (
    Branch,
    Customer,
    AccountType,
    TransactionType,
    Employee,
    Account,
    Transaction,
    Transfer,
)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_id', 'branch_name', 'branch_code', 'city', 'phone')
    search_fields = ('branch_name', 'city', 'branch_code')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'first_name', 'last_name', 'email', 'phone')
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ('account_type_id', 'type_name', 'minimum_balance', 'interest_rate')


@admin.register(TransactionType)
class TransactionTypeAdmin(admin.ModelAdmin):
    list_display = ('transaction_type_id', 'type_name')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'position', 'branch')
    list_filter = ('branch', 'position')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_id', 'account_number', 'customer', 'branch', 'balance', 'status')
    list_filter = ('status', 'branch', 'account_type')
    search_fields = ('account_number', 'customer__first_name', 'customer__last_name')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'reference_number', 'account', 'transaction_type', 'amount', 'transaction_date')
    list_filter = ('transaction_type', 'transaction_date')
    search_fields = ('reference_number', 'account__account_number')


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_id', 'reference_number', 'source_account', 'destination_account', 'amount', 'status', 'transfer_date')
    list_filter = ('status', 'transfer_date')
    search_fields = ('reference_number',)