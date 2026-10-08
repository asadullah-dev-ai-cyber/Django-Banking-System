from django.db import models


class Account(models.Model):
    account_id = models.AutoField(primary_key=True)
    account_number = models.CharField(unique=True, max_length=20)
    customer = models.ForeignKey('Customer', models.DO_NOTHING)
    branch = models.ForeignKey('Branch', models.DO_NOTHING)
    account_type = models.ForeignKey('AccountType', models.DO_NOTHING)
    opening_date = models.DateField()
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'account'

    def __str__(self):
        return f"{self.account_number} - {self.customer}"


class AccountType(models.Model):
    account_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(unique=True, max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    minimum_balance = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'account_type'

    def __str__(self):
        return self.type_name


class Branch(models.Model):
    branch_id = models.AutoField(primary_key=True)
    branch_name = models.CharField(max_length=100)
    branch_code = models.CharField(unique=True, max_length=20)
    city = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'branch'

    def __str__(self):
        return self.branch_name


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=20)
    email = models.CharField(unique=True, max_length=100)
    address = models.CharField(max_length=255)
    registration_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'customer'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Employee(models.Model):
    employee_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    position = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.CharField(unique=True, max_length=100)
    hire_date = models.DateField()
    branch = models.ForeignKey(Branch, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'employee'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Transaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(Account, models.DO_NOTHING)
    transaction_type = models.ForeignKey('TransactionType', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_date = models.DateTimeField()
    description = models.CharField(max_length=255, blank=True, null=True)
    reference_number = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'transaction'

    def __str__(self):
        return f"{self.reference_number} - {self.amount}"


class TransactionType(models.Model):
    transaction_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(unique=True, max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'transaction_type'

    def __str__(self):
        return self.type_name


class Transfer(models.Model):
    transfer_id = models.AutoField(primary_key=True)
    source_account = models.ForeignKey(Account, models.DO_NOTHING)
    destination_account = models.ForeignKey(Account, models.DO_NOTHING, related_name='transfer_destination_account_set')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transfer_date = models.DateTimeField()
    reference_number = models.CharField(unique=True, max_length=50)
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'transfer'

    def __str__(self):
        return f"{self.reference_number} - ${self.amount}"