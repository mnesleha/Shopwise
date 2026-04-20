from __future__ import annotations


DEMO_USERS = [
    {
        "key": "superuser",
        "email": "admin@shopwise.test",
        "password": "DemoAdmin123!",
        "first_name": "Marta",
        "last_name": "Kralova",
        "is_staff": True,
        "is_superuser": True,
        "email_verified": True,
    },
    {
        "key": "staff",
        "email": "staff@shopwise.test",
        "password": "DemoStaff123!",
        "first_name": "David",
        "last_name": "Urban",
        "is_staff": True,
        "is_superuser": False,
        "email_verified": True,
    },
    {
        "key": "customer_1",
        "email": "alice.walker@shopwise.test",
        "password": "DemoCustomer123!",
        "first_name": "Alice",
        "last_name": "Walker",
        "is_staff": False,
        "is_superuser": False,
        "email_verified": True,
    },
    {
        "key": "customer_2",
        "email": "martin.novak@shopwise.test",
        "password": "DemoCustomer123!",
        "first_name": "Martin",
        "last_name": "Novak",
        "is_staff": False,
        "is_superuser": False,
        "email_verified": True,
    },
]


DEMO_TAX_CLASSES = [
    {
        "key": "vat_21",
        "code": "vat-21",
        "name": "VAT 21%",
        "description": "Standard VAT rate for showcase catalog items.",
        "rate": "21.0000",
    },
    {
        "key": "vat_12",
        "code": "vat-12",
        "name": "VAT 12%",
        "description": "Reduced VAT rate for selected showcase catalog items.",
        "rate": "12.0000",
    },
    {
        "key": "vat_0",
        "code": "vat-0",
        "name": "VAT 0%",
        "description": "Zero VAT rate for tax-exempt showcase catalog items.",
        "rate": "0.0000",
    },
]


DEMO_SUPPLIER = {
    "key": "default_supplier",
    "lookup": {"company_id": "SHOPWISE-DEMO-001"},
    "defaults": {
        "name": "Shopwise Demo Supply",
        "company_id": "SHOPWISE-DEMO-001",
        "vat_id": "CZSHOPWISE001",
        "email": "supply@shopwise.test",
        "phone": "+420555123456",
        "is_active": True,
    },
    "addresses": [
        {
            "key": "billing_hq",
            "label": "Billing HQ",
            "street_line_1": "Demo Avenue 12",
            "street_line_2": "Holesovice",
            "city": "Prague",
            "postal_code": "17000",
            "country": "CZ",
            "is_default_for_orders": True,
        },
        {
            "key": "operations",
            "label": "Operations",
            "street_line_1": "Warehouse Park 7",
            "street_line_2": "",
            "city": "Brno",
            "postal_code": "60200",
            "country": "CZ",
            "is_default_for_orders": False,
        },
    ],
    "payment_details": [
        {
            "key": "primary_account",
            "label": "Primary CZK Account",
            "bank_name": "Ceska sporitelna",
            "account_number": "123456789/0800",
            "iban": "CZ6508000000001234567899",
            "swift": "GIBACZPX",
            "is_default_for_orders": True,
        }
    ],
}


DEMO_CATEGORIES = [
    {"key": "electronics", "name": "Electronics"},
    {"key": "grocery", "name": "Grocery"},
    {"key": "pets", "name": "Pets"},
]