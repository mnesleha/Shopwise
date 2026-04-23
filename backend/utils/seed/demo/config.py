from __future__ import annotations


def _md(title: str, intro: str, highlights: list[str], demo_note: str) -> str:
    highlight_lines = "\n".join(f"- {item}" for item in highlights)
    return (
        f"## {title}\n\n"
        f"{intro}\n\n"
        "### Highlights\n"
        f"{highlight_lines}\n\n"
        "### Demo Notes\n"
        f"{demo_note}"
    )


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


DEMO_PRODUCTS = [
    {
        "key": "wireless_headphones",
        "name": "Wireless Headphones",
        "slug": "wireless-headphones",
        "category_name": "Electronics",
        "tax_class_name": "VAT 21%",
        "price": "2490.00",
        "stock_quantity": 50,
        "short_description": "Over-ear wireless headphones with all-day comfort and travel-ready noise isolation.",
        "full_description": _md(
            "Wireless Headphones",
            "Balanced wireless headphones tuned for long work sessions, focused commuting, and clean storefront demos.",
            [
                "Soft over-ear cushions designed for extended listening.",
                "Reliable Bluetooth connection for laptop and mobile pairing.",
                "Fold-flat construction that packs cleanly into a backpack.",
            ],
            "Use this product to demonstrate gallery media, category discounts, and the selected-products promotion override.",
        ),
    },
    {
        "key": "mechanical_keyboard",
        "name": "Mechanical Keyboard",
        "slug": "mechanical-keyboard",
        "category_name": "Electronics",
        "tax_class_name": "VAT 21%",
        "price": "3190.00",
        "stock_quantity": 50,
        "short_description": "Compact mechanical keyboard with tactile switches and a sturdy aluminum top plate.",
        "full_description": _md(
            "Mechanical Keyboard",
            "A compact desktop upgrade for customers who want satisfying key feel without giving up desk space.",
            [
                "Tactile mechanical switches for crisp feedback.",
                "Detachable USB-C cable for cleaner setups.",
                "PBT keycaps sized for daily office and gaming use.",
            ],
            "This item is targeted only by the electronics-wide promotion, which makes it useful for priority demos.",
        ),
    },
    {
        "key": "usb_c_dock",
        "name": "USB-C Dock",
        "slug": "usb-c-dock",
        "category_name": "Electronics",
        "tax_class_name": "VAT 21%",
        "price": "1890.00",
        "stock_quantity": 0,
        "short_description": "Desk dock that turns one USB-C cable into display, power, and peripheral connectivity.",
        "full_description": _md(
            "USB-C Dock",
            "A practical workstation dock for hybrid teams that need fewer cables and faster desk setup.",
            [
                "Single-cable docking for monitor and accessories.",
                "Multiple USB ports for mouse, keyboard, and storage.",
                "Stable desktop footprint suited for product photography.",
            ],
            "Included in the selected-products promotion so demos can show a stronger line discount on specific SKUs.",
        ),
    },
    {
        "key": "smart_speaker",
        "name": "Smart Speaker",
        "slug": "smart-speaker",
        "category_name": "Electronics",
        "tax_class_name": "VAT 21%",
        "price": "1590.00",
        "stock_quantity": 0,
        "short_description": "Voice-enabled smart speaker with room-friendly design and quick setup for connected homes.",
        "full_description": _md(
            "Smart Speaker",
            "A compact speaker meant to make the electronics section feel lifestyle-oriented instead of purely utilitarian.",
            [
                "Clean fabric exterior that photographs well on neutral backgrounds.",
                "Fast setup flow for voice assistant demos.",
                "Compact footprint suited for shelves, kitchens, and desks.",
            ],
            "Keeps the electronics category diverse while remaining covered by the category-level discount only.",
        ),
    },
    {
        "key": "portable_ssd",
        "name": "Portable SSD",
        "slug": "portable-ssd",
        "category_name": "Electronics",
        "tax_class_name": "VAT 21%",
        "price": "2190.00",
        "stock_quantity": 4,
        "short_description": "Pocket-size portable SSD for fast backups, field work, and content handoff between devices.",
        "full_description": _md(
            "Portable SSD",
            "High-speed external storage positioned as a premium accessory for creators and mobile professionals.",
            [
                "Solid-state performance for large file transfers.",
                "Compact enclosure that fits in every gear pouch.",
                "Useful anchor product for premium bundle storytelling.",
            ],
            "Also participates in the stronger product-specific promotion to demonstrate target precedence over category rules.",
        ),
    },
    {
        "key": "organic_pasta",
        "name": "Organic Pasta",
        "slug": "organic-pasta",
        "category_name": "Grocery",
        "tax_class_name": "VAT 12%",
        "price": "79.00",
        "stock_quantity": 50,
        "short_description": "Organic durum wheat pasta for pantry staples, meal kits, and reduced-rate tax examples.",
        "full_description": _md(
            "Organic Pasta",
            "Simple pantry item that keeps the grocery section grounded in everyday repeat-purchase products.",
            [
                "Dry pasta format with broad household appeal.",
                "Reduced-rate tax example for pricing calculations.",
                "Compact price point that complements higher-ticket electronics.",
            ],
            "Useful in demos that need mixed-tax carts without introducing any line-level promotion overlap.",
        ),
    },
    {
        "key": "olive_oil",
        "name": "Olive Oil",
        "slug": "olive-oil",
        "category_name": "Grocery",
        "tax_class_name": "VAT 12%",
        "price": "189.00",
        "stock_quantity": 50,
        "short_description": "Cold-pressed olive oil positioned as a premium pantry item with clean culinary imagery.",
        "full_description": _md(
            "Olive Oil",
            "Premium grocery item that broadens the shelf from staples into gifting and quality-led food products.",
            [
                "Cold-pressed style positioning for premium perception.",
                "Bottle format works well in image galleries.",
                "Reduced-rate tax example for non-electronics pricing.",
            ],
            "Keeps grocery products outside the electronics promotions, making price behavior easy to explain during demos.",
        ),
    },
    {
        "key": "granola_mix",
        "name": "Granola Mix",
        "slug": "granola-mix",
        "category_name": "Grocery",
        "tax_class_name": "VAT 12%",
        "price": "129.00",
        "stock_quantity": 0,
        "short_description": "Crunchy granola blend for breakfast and snack merchandising on grocery landing pages.",
        "full_description": _md(
            "Granola Mix",
            "A versatile breakfast product that keeps the grocery assortment modern and lifestyle-friendly.",
            [
                "Shelf-stable packaging for repeatable demo inventory.",
                "Mid-tier price point between staples and premium oils.",
                "Works well in search and category filtering demos.",
            ],
            "Use it when showcasing mixed-category carts that should not trigger electronics-specific promotions.",
        ),
    },
    {
        "key": "green_tea",
        "name": "Green Tea",
        "slug": "green-tea",
        "category_name": "Grocery",
        "tax_class_name": "VAT 12%",
        "price": "99.00",
        "stock_quantity": 0,
        "short_description": "Everyday green tea that adds a low-ticket beverage SKU to the grocery assortment.",
        "full_description": _md(
            "Green Tea",
            "A lightweight beverage SKU that helps the catalogue feel complete without introducing complexity.",
            [
                "Low-ticket item for basket-building scenarios.",
                "Reduced-rate tax treatment for pricing contrast.",
                "Simple packaging that fits thumbnail and detail layouts.",
            ],
            "Often useful as filler in threshold-order demos where you want to reach an order promotion with a small add-on.",
        ),
    },
    {
        "key": "dark_chocolate",
        "name": "Dark Chocolate",
        "slug": "dark-chocolate",
        "category_name": "Grocery",
        "tax_class_name": "VAT 12%",
        "price": "69.00",
        "stock_quantity": 4,
        "short_description": "Small premium chocolate bar that rounds out the grocery range with an impulse purchase item.",
        "full_description": _md(
            "Dark Chocolate",
            "Impulse-price grocery item for demos that need a realistic low-cost add-on product.",
            [
                "Low unit price suited for basket top-ups.",
                "Premium positioning without requiring complex options.",
                "Reduced-rate tax example that stays outside promotions.",
            ],
            "A good candidate for threshold-progress demos because it changes totals without overshadowing the main items.",
        ),
    },
    {
        "key": "dog_food_premium",
        "name": "Dog Food Premium",
        "slug": "dog-food-premium",
        "category_name": "Pets",
        "tax_class_name": "VAT 12%",
        "price": "799.00",
        "stock_quantity": 50,
        "short_description": "Large premium dog food bag for recurring-purchase pet care orders and subscription-style demos.",
        "full_description": _md(
            "Dog Food Premium",
            "Core pet-care staple that makes the pets category feel commercially credible and replenishment-oriented.",
            [
                "High-repeat purchase profile suited for loyalty discussion.",
                "Reduced-rate tax handling distinct from accessories.",
                "Larger basket contribution than small pet consumables.",
            ],
            "Useful when demonstrating that not every category participates in promotional messaging.",
        ),
    },
    {
        "key": "cat_litter_pro",
        "name": "Cat Litter Pro",
        "slug": "cat-litter-pro",
        "category_name": "Pets",
        "tax_class_name": "VAT 12%",
        "price": "249.00",
        "stock_quantity": 50,
        "short_description": "Low-dust cat litter positioned as a dependable household replenishment product.",
        "full_description": _md(
            "Cat Litter Pro",
            "Practical household item that anchors the pets section in realistic weekly and monthly reorders.",
            [
                "Dependable mid-price replenishment product.",
                "Pairs naturally with bowls, toys, and hygiene items.",
                "Reduced-rate tax example for pet essentials.",
            ],
            "Helps demonstrate mixed pet baskets that are unaffected by the electronics commercial layer.",
        ),
    },
    {
        "key": "pet_shampoo",
        "name": "Pet Shampoo",
        "slug": "pet-shampoo",
        "category_name": "Pets",
        "tax_class_name": "VAT 21%",
        "price": "159.00",
        "stock_quantity": 0,
        "short_description": "Gentle pet shampoo for grooming demos and cross-category tax-rate coverage.",
        "full_description": _md(
            "Pet Shampoo",
            "Small grooming product that keeps the pets assortment broader than pure food and utility goods.",
            [
                "21 percent tax example inside the pets category.",
                "Compact packaging suited for close-up product imagery.",
                "Useful accessory item for mixed baskets.",
            ],
            "Keeps the demo catalogue from collapsing into single-rate categories and supports pricing QA.",
        ),
    },
    {
        "key": "chew_toy_rope",
        "name": "Chew Toy Rope",
        "slug": "chew-toy-rope",
        "category_name": "Pets",
        "tax_class_name": "VAT 0%",
        "price": "119.00",
        "stock_quantity": 4,
        "short_description": "Durable rope toy that provides a clear zero-rate tax example in the pet accessories range.",
        "full_description": _md(
            "Chew Toy Rope",
            "Pet accessory used mainly to exercise the zero-rate tax path in a still-realistic product catalogue.",
            [
                "Zero-rate tax class for pricing and tax validation.",
                "Low-price accessory suited for add-on behavior.",
                "Simple visual product for gallery asset coverage.",
            ],
            "This SKU is intentionally promotion-free so tax behavior stays easy to validate in isolation.",
        ),
    },
    {
        "key": "pet_bowl_set",
        "name": "Pet Bowl Set",
        "slug": "pet-bowl-set",
        "category_name": "Pets",
        "tax_class_name": "VAT 0%",
        "price": "299.00",
        "stock_quantity": 0,
        "short_description": "Two-piece bowl set for feeding stations, gifting, and zero-rate catalogue coverage.",
        "full_description": _md(
            "Pet Bowl Set",
            "Simple accessory product that balances the pet assortment with a home-oriented, non-consumable item.",
            [
                "Zero-rate tax example with a higher accessory price point.",
                "Durable merchandising item for pet bundles.",
                "Useful for detail-page layout demos with multiple images.",
            ],
            "Another clean no-promotion SKU used to contrast against the discounted electronics showcase items.",
        ),
    },
]


DEMO_LINE_PROMOTIONS = [
    {
        "key": "electronics_discount",
        "name": "Electronics Discount",
        "code": "demo-electronics-discount",
        "type": "PERCENT",
        "value": "10.00",
        "amount_scope": "GROSS",
        "priority": 20,
        "description": "Category-wide 10 percent promotion for all electronics products in the demo catalogue.",
        "category_names": ["Electronics"],
        "product_slugs": [],
    },
    {
        "key": "selected_products_15_off",
        "name": "Selected Products 15% Off",
        "code": "demo-selected-products-15-off",
        "type": "PERCENT",
        "value": "15.00",
        "amount_scope": "GROSS",
        "priority": 30,
        "description": "Higher-priority showcase promotion for three flagship electronics products.",
        "category_names": [],
        "product_slugs": [
            "wireless-headphones",
            "usb-c-dock",
            "portable-ssd",
        ],
    },
]


DEMO_ORDER_PROMOTIONS = [
    {
        "key": "demo_order_discount",
        "name": "Demo Order Discount",
        "code": "demo-order-discount",
        "type": "FIXED",
        "value": "250.00",
        "acquisition_mode": "AUTO_APPLY",
        "stacking_policy": "STACKABLE_WITH_LINE",
        "priority": 40,
        "minimum_order_value": "3500.00",
        "is_discoverable": True,
        "description": "Auto-applied fixed discount for larger demo baskets after line promotions are resolved.",
    },
    {
        "key": "campaign_welcome_offer_promotion",
        "name": "Campaign Welcome Offer",
        "code": "campaign-welcome-offer",
        "type": "FIXED",
        "value": "300.00",
        "acquisition_mode": "CAMPAIGN_APPLY",
        "stacking_policy": "EXCLUSIVE",
        "priority": 60,
        "minimum_order_value": "1500.00",
        "is_discoverable": False,
        "description": "Claimable campaign-linked welcome discount represented in the current domain as an order promotion plus offer token.",
    },
]


DEMO_OFFERS = [
    {
        "key": "campaign_welcome_offer",
        "promotion_code": "campaign-welcome-offer",
        "token": "DEMO-WELCOME-2025",
        "status": "DELIVERED",
        "is_active": True,
        "description": "Stable campaign token for demos, QA, and manual storefront walkthroughs.",
    }
]


DEMO_HISTORY_CUSTOMER_EMAIL = "alice.walker@shopwise.test"


DEMO_ORDER_HISTORY = [
    {
        "key": "active_order",
        "reference": "demo-history-active-order",
        "products": [
            {"slug": "wireless-headphones", "quantity": 1},
            {"slug": "green-tea", "quantity": 1},
        ],
        "payment_method": "CARD",
        "provider_payment_id": "demo-active-card-payment",
        "payment_redirect_url": "https://acquiremock.test/checkout/demo-active-card-payment",
        "webhook_statuses": ["PAID"],
        "cancel": None,
        "description": "Active paid order with an existing shipment label, still in the current orders bucket.",
    },
    {
        "key": "delivered_order",
        "reference": "demo-history-delivered-order",
        "products": [
            {"slug": "dog-food-premium", "quantity": 1},
            {"slug": "organic-pasta", "quantity": 1},
        ],
        "payment_method": "CARD",
        "provider_payment_id": "demo-delivered-card-payment",
        "payment_redirect_url": "https://acquiremock.test/checkout/demo-delivered-card-payment",
        "webhook_statuses": ["PAID", "IN_TRANSIT", "DELIVERED"],
        "cancel": None,
        "description": "Completed delivered order with a paid card payment and shipment timeline events.",
    },
    {
        "key": "cancelled_order",
        "reference": "demo-history-cancelled-order",
        "products": [
            {"slug": "mechanical-keyboard", "quantity": 1},
        ],
        "payment_method": None,
        "provider_payment_id": None,
        "payment_redirect_url": None,
        "webhook_statuses": [],
        "cancel": {
            "release_reason": "ADMIN_CANCEL",
            "cancelled_by": "ADMIN",
            "cancel_reason": "ADMIN_CANCELLED",
        },
        "description": "Cancelled pre-payment order with released reservations and no shipment.",
    },
]


DEMO_PRODUCT_SLUGS = [product["slug"] for product in DEMO_PRODUCTS]