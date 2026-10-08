from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Account, Transfer


def execute_transfer(
    source_account_id: int, 
    destination_account_id: int, 
    amount: Decimal, 
    reference_number: str
) -> Transfer:
    # 1. Parameter Validations
    if amount <= Decimal("0.00"):
        raise ValidationError("Transfer amount must be greater than zero.")

    if source_account_id == destination_account_id:
        raise ValidationError("Source and destination accounts must be different.")

    # 2. Prevent Deadlocks by Locking in Ascending Primary Key Order
    account_ids = sorted([source_account_id, destination_account_id])

    with transaction.atomic():
        # Fetch and lock both accounts using ordered IDs
        locked_accounts = {
            acc.pk: acc 
            for acc in Account.objects.select_for_update().filter(pk__in=account_ids)
        }

        # Verify Account Existence
        if source_account_id not in locked_accounts:
            raise ValidationError(f"Source account (ID: {source_account_id}) does not exist.")
        if destination_account_id not in locked_accounts:
            raise ValidationError(f"Destination account (ID: {destination_account_id}) does not exist.")

        source = locked_accounts[source_account_id]
        destination = locked_accounts[destination_account_id]

        # Verify Active Account Status
        if source.status.upper() != 'ACTIVE':
            raise ValidationError(f"Source account {source.account_number} is not active.")
        if destination.status.upper() != 'ACTIVE':
            raise ValidationError(f"Destination account {destination.account_number} is not active.")

        # Balance Check
        if source.balance < amount:
            raise ValidationError(f"Insufficient funds. Available balance is ${source.balance:,.2f}.")

        # Execute Balance Updates
        source.balance -= amount
        destination.balance += amount

        source.save()
        destination.save()

        # Audit Ledger Record Creation
        transfer_record = Transfer.objects.create(
            source_account=source,
            destination_account=destination,
            amount=amount,
            reference_number=reference_number,
            status='COMPLETED',
            transfer_date=timezone.now()
        )

        return transfer_record