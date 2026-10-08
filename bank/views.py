import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Account,
    AccountType,
    Branch,
    Customer,
    Transfer,
)
from .services import execute_transfer


# ============================================================
# DASHBOARD
# ============================================================

@login_required
def dashboard_view(request):
    """
    Render the main banking management dashboard with live
    system metrics.
    """

    today_local = timezone.localtime().date()

    all_transfers = (
        Transfer.objects
        .select_related(
            "source_account",
            "source_account__customer",
            "destination_account",
            "destination_account__customer",
        )
        .order_by("-transfer_date")
    )

    today_transfers = [
        transfer
        for transfer in all_transfers
        if (
            timezone.localtime(transfer.transfer_date).date()
            == today_local
            and str(transfer.status).upper()
            in {"COMPLETED", "SUCCESS"}
        )
    ]

    daily_volume = (
        sum(transfer.amount for transfer in today_transfers)
        or Decimal("0.00")
    )

    daily_transfers_count = len(today_transfers)

    total_deposits = (
        Account.objects
        .filter(status="ACTIVE")
        .aggregate(total=Sum("balance"))
        ["total"]
        or Decimal("0.00")
    )

    active_accounts_count = (
        Account.objects
        .filter(status="ACTIVE")
        .count()
    )

    pending_reviews_count = (
        Transfer.objects
        .filter(status__iexact="PENDING")
        .count()
    )

    context = {
        "current_branch": "Main Branch (TB01)",
        "total_deposits": total_deposits,
        "active_accounts_count": active_accounts_count,
        "daily_volume": daily_volume,
        "daily_transfers_count": daily_transfers_count,
        "pending_count": pending_reviews_count,
        "recent_transactions": all_transfers[:5],
    }

    return render(
        request,
        "dashboard.html",
        context,
    )


# ============================================================
# LIST VIEWS
# ============================================================

@login_required
def customers_list_view(request):
    """
    Display all customers.

    Account counts are calculated by the database instead of
    performing one query per customer in the template.
    """

    customers = (
        Customer.objects
        .annotate(
            account_count=Count("account")
        )
        .order_by("-registration_date")
    )

    return render(
        request,
        "customers.html",
        {
            "customers": customers,
        },
    )


@login_required
def accounts_list_view(request):
    accounts = (
        Account.objects
        .select_related(
            "customer",
            "branch",
            "account_type",
        )
        .all()
        .order_by("-opening_date")
    )

    customers = Customer.objects.all()
    account_types = AccountType.objects.all()

    return render(
        request,
        "accounts.html",
        {
            "accounts": accounts,
            "customers": customers,
            "account_types": account_types,
        },
    )


@login_required
def transfers_list_view(request):
    transfers = (
        Transfer.objects
        .select_related(
            "source_account__customer",
            "destination_account__customer",
        )
        .all()
        .order_by("-transfer_date")
    )

    accounts = (
        Account.objects
        .filter(status="ACTIVE")
        .select_related("customer")
    )

    return render(
        request,
        "transfers.html",
        {
            "transfers": transfers,
            "accounts": accounts,
        },
    )


# ============================================================
# DETAIL & FORM VIEWS
# ============================================================

@login_required
def customer_detail_view(request, customer_id: int):
    """
    Render an individual customer profile, owned accounts,
    aggregated balance, and unified transfer history.
    """

    customer = get_object_or_404(
        Customer,
        pk=customer_id,
    )

    accounts = (
        Account.objects
        .filter(customer=customer)
        .select_related("account_type")
    )

    total_balance = (
        accounts
        .aggregate(total=Sum("balance"))
        ["total"]
        or Decimal("0.00")
    )

    transactions = (
        Transfer.objects
        .filter(
            Q(source_account__in=accounts)
            | Q(destination_account__in=accounts)
        )
        .select_related(
            "source_account",
            "destination_account",
            "source_account__customer",
            "destination_account__customer",
        )
        .order_by("-transfer_date")
    )

    active_accounts_count = (
        accounts
        .filter(status="ACTIVE")
        .count()
    )

    context = {
        "customer": customer,
        "accounts": accounts,
        "total_balance": total_balance,
        "active_accounts_count": active_accounts_count,
        "transactions": transactions,
    }

    return render(
        request,
        "customer_detail.html",
        context,
    )


@login_required
def account_detail_view(request, account_id: int):
    """
    Render an individual account and its transfer ledger.
    """

    account = get_object_or_404(
        Account.objects.select_related(
            "customer",
            "branch",
            "account_type",
        ),
        pk=account_id,
    )

    transactions = (
        Transfer.objects
        .filter(
            Q(source_account=account)
            | Q(destination_account=account)
        )
        .select_related(
            "source_account__customer",
            "destination_account__customer",
        )
        .order_by("-transfer_date")
    )

    total_incoming = (
        Transfer.objects
        .filter(
            destination_account=account,
            status__iexact="COMPLETED",
        )
        .aggregate(total=Sum("amount"))
        ["total"]
        or Decimal("0.00")
    )

    total_outgoing = (
        Transfer.objects
        .filter(
            source_account=account,
            status__iexact="COMPLETED",
        )
        .aggregate(total=Sum("amount"))
        ["total"]
        or Decimal("0.00")
    )

    context = {
        "account": account,
        "transactions": transactions,
        "total_incoming": total_incoming,
        "total_outgoing": total_outgoing,
        "transactions_count": transactions.count(),
    }

    return render(
        request,
        "account_detail.html",
        context,
    )


@login_required
def transfer_form_view(request):
    active_accounts = (
        Account.objects
        .filter(status="ACTIVE")
        .select_related("customer")
    )

    return render(
        request,
        "transfer_form.html",
        {
            "accounts": active_accounts,
        },
    )


# ============================================================
# API & ACTION ENDPOINTS
# ============================================================

@login_required
def get_account_detail(request, account_id: int):
    """
    Return account information as JSON.
    """

    try:
        account = (
            Account.objects
            .select_related(
                "account_type",
                "customer",
            )
            .get(pk=account_id)
        )

        return JsonResponse(
            {
                "account_id": account.pk,
                "account_number": account.account_number,
                "customer_name": (
                    f"{account.customer.first_name} "
                    f"{account.customer.last_name}"
                ),
                "account_type": (
                    account.account_type.type_name
                    if account.account_type
                    else "Standard"
                ),
                "balance": str(account.balance),
                "status": account.status,
            }
        )

    except Account.DoesNotExist:
        return JsonResponse(
            {"error": "Account not found."},
            status=404,
        )


# ============================================================
# CREATE CUSTOMER
# ============================================================

@login_required
@require_POST
def add_customer(request):
    """
    Create a new customer from the customer registration modal.
    """

    try:
        data = json.loads(request.body)

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON payload."},
            status=400,
        )


    # --------------------------------------------------------
    # Extract and normalize input
    # --------------------------------------------------------

    first_name = str(
        data.get("first_name", "")
    ).strip()

    last_name = str(
        data.get("last_name", "")
    ).strip()

    date_of_birth = str(
        data.get("date_of_birth", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    phone = str(
        data.get("phone", "")
    ).strip()

    address = str(
        data.get("address", "")
    ).strip()


    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if not first_name:
        return JsonResponse(
            {"error": "First name is required."},
            status=400,
        )

    if not last_name:
        return JsonResponse(
            {"error": "Last name is required."},
            status=400,
        )

    if not date_of_birth:
        return JsonResponse(
            {"error": "Date of birth is required."},
            status=400,
        )

    if not email:
        return JsonResponse(
            {"error": "Email address is required."},
            status=400,
        )


    # --------------------------------------------------------
    # Validate email
    # --------------------------------------------------------

    try:
        validate_email(email)

    except ValidationError:
        return JsonResponse(
            {"error": "Please provide a valid email address."},
            status=400,
        )


    # --------------------------------------------------------
    # Validate date of birth
    # --------------------------------------------------------

    try:
        birth_date = timezone.datetime.strptime(
            date_of_birth,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return JsonResponse(
            {
                "error": (
                    "Invalid date of birth. "
                    "Use the format YYYY-MM-DD."
                )
            },
            status=400,
        )


    # Prevent obviously invalid future birth dates.
    if birth_date > timezone.localdate():
        return JsonResponse(
            {"error": "Date of birth cannot be in the future."},
            status=400,
        )


    # --------------------------------------------------------
    # Create customer
    # --------------------------------------------------------

    try:

        customer = Customer.objects.create(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=birth_date,
            email=email,
            phone=phone,
            address=address,
            registration_date=timezone.localdate(),
        )

    except IntegrityError:
        return JsonResponse(
            {
                "error": (
                    "A customer with this email address "
                    "already exists."
                )
            },
            status=409,
        )

    except Exception:
        return JsonResponse(
            {
                "error": (
                    "Unable to create the customer. "
                    "Please check the submitted information."
                )
            },
            status=400,
        )


    return JsonResponse(
        {
            "message": "Customer registered successfully!",
            "customer_id": customer.pk,
        },
        status=201,
    )


# ============================================================
# CREATE ACCOUNT
# ============================================================

@login_required
@require_POST
def add_account(request):
    try:
        data = json.loads(request.body)

        cust_id = data.get("customer_id")
        account_type_id = data.get("account_type_id")

        balance = Decimal(
            str(
                data.get("initial_balance")
                or data.get("balance")
                or "0.00"
            )
        )

        customer = Customer.objects.get(
            pk=cust_id
        )

        branch = Branch.objects.first()

        if not branch:
            return JsonResponse(
                {"error": "No bank branch is available."},
                status=400,
            )

        if account_type_id:
            account_type = AccountType.objects.get(
                account_type_id=account_type_id
            )
        else:
            account_type = AccountType.objects.first()

        if not account_type:
            return JsonResponse(
                {"error": "No account type is available."},
                status=400,
            )

        account = Account.objects.create(
            customer=customer,
            account_number=data.get("account_number"),
            balance=balance,
            branch=branch,
            account_type=account_type,
            status="ACTIVE",
            opening_date=timezone.localdate(),
        )

        return JsonResponse(
            {
                "message": "Bank account opened successfully!",
                "account_id": account.pk,
            },
            status=201,
        )

    except Customer.DoesNotExist:
        return JsonResponse(
            {"error": "Selected customer does not exist."},
            status=404,
        )

    except AccountType.DoesNotExist:
        return JsonResponse(
            {"error": "Selected account type does not exist."},
            status=404,
        )

    except InvalidOperation:
        return JsonResponse(
            {"error": "Invalid account balance."},
            status=400,
        )

    except Exception:
        return JsonResponse(
            {
                "error": (
                    "Unable to create the bank account. "
                    "Please check the submitted information."
                )
            },
            status=400,
        )


# ============================================================
# TRANSFER FUNDS
# ============================================================

@login_required
@require_POST
def transfer_funds(request):
    try:
        data = json.loads(request.body)

        source_account_id = int(
            data["source_account_id"]
        )

        destination_account_id = int(
            data["destination_account_id"]
        )

        amount = Decimal(
            str(data["amount"])
        )

        reference_number = data["reference_number"]

        transfer = execute_transfer(
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount=amount,
            reference_number=reference_number,
        )

        return JsonResponse(
            {
                "message": "Transfer executed successfully",
                "transfer_id": transfer.pk,
                "status": transfer.status,
                "amount": str(transfer.amount),
                "reference_number": transfer.reference_number,
            },
            status=201,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        InvalidOperation,
    ):
        return JsonResponse(
            {
                "error": (
                    "Invalid payload parameters provided."
                )
            },
            status=400,
        )

    except ValidationError as exc:
        return JsonResponse(
            {
                "error": str(exc),
            },
            status=400,
        )

    except Exception as exc:
        return JsonResponse(
            {
                "error": (
                    "An error occurred while processing "
                    f"the transfer: {str(exc)}"
                )
            },
            status=500,
        )