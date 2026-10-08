from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.apps import apps
from django.db import connection
from django.core.exceptions import ValidationError
from bank.models import Branch, Customer, AccountType, Account
from bank.services import execute_transfer


class UnmanagedModelTestRunner(DiscoverRunner):
    """Forces unmanaged models (managed=False) to create tables in the test DB."""
    def setup_databases(self, **kwargs):
        unmanaged_models = []
        for model in apps.get_models():
            if not model._meta.managed:
                model._meta.managed = True
                unmanaged_models.append(model)

        old_config = super().setup_databases(**kwargs)

        with connection.schema_editor() as schema_editor:
            for model in unmanaged_models:
                schema_editor.create_model(model)

        return old_config


class BankingServiceTests(TestCase):
    def setUp(self):
        """Sets up test accounts with all required non-null fields before each test runs."""
        branch = Branch.objects.create(
            branch_name='Test Branch',
            branch_code='TB01',
            city='Kabul',
            address='123 Bank Street',
            phone='0700000000'
        )
        customer = Customer.objects.create(
            first_name='Test',
            last_name='User',
            email='test@example.com',
            date_of_birth=date(1995, 1, 1),
            phone='0700000000',
            address='123 Main Street',
            registration_date=date(2026, 1, 1)
        )
        acc_type = AccountType.objects.create(
            type_name='Savings',
            minimum_balance=Decimal('100.00'),
            interest_rate=Decimal('2.50')
        )

        self.account_a = Account.objects.create(
            account_number='ACC-101',
            customer=customer,
            branch=branch,
            account_type=acc_type,
            opening_date=date(2026, 1, 1),
            balance=Decimal('500.00'),
            status='Active'
        )
        self.account_b = Account.objects.create(
            account_number='ACC-102',
            customer=customer,
            branch=branch,
            account_type=acc_type,
            opening_date=date(2026, 1, 1),
            balance=Decimal('200.00'),
            status='Active'
        )

    def test_successful_transfer(self):
        """Tests a valid funds transfer between two accounts."""
        execute_transfer(
            source_account_id=self.account_a.account_id,
            destination_account_id=self.account_b.account_id,
            amount=Decimal('100.00'),
            reference_number='TRF-UNIT-01'
        )
        self.account_a.refresh_from_db()
        self.account_b.refresh_from_db()

        self.assertEqual(self.account_a.balance, Decimal('400.00'))
        self.assertEqual(self.account_b.balance, Decimal('300.00'))

    def test_insufficient_funds_raises_error(self):
        """Tests that transfers exceeding account balance fail and roll back."""
        with self.assertRaises(ValidationError):
            execute_transfer(
                source_account_id=self.account_a.account_id,
                destination_account_id=self.account_b.account_id,
                amount=Decimal('1000.00'),
                reference_number='TRF-UNIT-02'
            )

    def test_negative_amount_raises_error(self):
        """Tests that negative transfer amounts are rejected."""
        with self.assertRaises(ValidationError):
            execute_transfer(
                source_account_id=self.account_a.account_id,
                destination_account_id=self.account_b.account_id,
                amount=Decimal('-50.00'),
                reference_number='TRF-UNIT-03'
            )