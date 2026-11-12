from typing import Dict, Optional
from app.models.seller import MerchantCommercialProfile

# Simulated Commercial Database for NEGOZA Products
# In production, this data is retrieved from merchant ERP / inventory systems.
SIMULATED_MERCHANT_PROFILES: Dict[str, MerchantCommercialProfile] = {
    # Product 1: Smartwatch
    "prod-1": MerchantCommercialProfile(
        merchant_id="merchant-chronos",
        merchant_name="Chronos Official",
        product_id="prod-1",
        listed_price=299.0,
        preferred_price=275.0,
        minimum_acceptable_price=235.0,
        available_inventory=15,
        maximum_permitted_discount=64.0,  # Max discount: $64 ($299 -> $235)
        delivery_cost=15.0,
        free_delivery_allowed=True,
        promotional_rules=[
            "Free standard delivery permitted for proposals at or above $235.00",
            "Express courier available with $15.00 surcharge",
            "Official 1-year warranty included on all sales"
        ]
    ),
    # Product 2: Headphones
    "prod-2": MerchantCommercialProfile(
        merchant_id="merchant-soundwave",
        merchant_name="SoundWave Direct",
        product_id="prod-2",
        listed_price=349.0,
        preferred_price=320.0,
        minimum_acceptable_price=280.0,
        available_inventory=8,
        maximum_permitted_discount=69.0,  # Max discount: $69 ($349 -> $280)
        delivery_cost=20.0,
        free_delivery_allowed=True,
        promotional_rules=[
            "Free delivery permitted for proposals >= $290.00",
            "Must maintain minimum gross margin",
            "30-day trial policy included"
        ]
    ),
    # Product 3: Sneakers (Strict delivery fee - free delivery NOT allowed)
    "prod-3": MerchantCommercialProfile(
        merchant_id="merchant-kickslab",
        merchant_name="KicksLab Prime",
        product_id="prod-3",
        listed_price=180.0,
        preferred_price=168.0,
        minimum_acceptable_price=150.0,
        available_inventory=25,
        maximum_permitted_discount=30.0,  # Max discount: $30 ($180 -> $150)
        delivery_cost=12.0,
        free_delivery_allowed=False,  # Policy forbids free shipping on discounted footwear
        promotional_rules=[
            "Strict logistics surcharge: $12.00 delivery fee applies to all orders",
            "Free delivery is prohibited on discounted footwear"
        ]
    ),
    # Product 4: Handbag
    "prod-4": MerchantCommercialProfile(
        merchant_id="merchant-maison",
        merchant_name="Maison & Co.",
        product_id="prod-4",
        listed_price=420.0,
        preferred_price=390.0,
        minimum_acceptable_price=350.0,
        available_inventory=6,
        maximum_permitted_discount=70.0,
        delivery_cost=25.0,
        free_delivery_allowed=True,
        promotional_rules=[
            "Complimentary gift packaging included for final deals >= $360.00",
            "Free white-glove delivery eligible"
        ]
    ),
    # Product 5: Coffee Machine
    "prod-5": MerchantCommercialProfile(
        merchant_id="merchant-cremacraft",
        merchant_name="CremaCraft Tech",
        product_id="prod-5",
        listed_price=599.0,
        preferred_price=555.0,
        minimum_acceptable_price=490.0,
        available_inventory=10,
        maximum_permitted_discount=109.0,
        delivery_cost=30.0,
        free_delivery_allowed=True,
        promotional_rules=[
            "Free freight delivery on all orders above $490.00",
            "Starter espresso bean sample pack included"
        ]
    ),
    # Product 6: Smartphone (Special courier fee required - free delivery NOT allowed)
    "prod-6": MerchantCommercialProfile(
        merchant_id="merchant-apex",
        merchant_name="Apex Mobile Store",
        product_id="prod-6",
        listed_price=899.0,
        preferred_price=845.0,
        minimum_acceptable_price=780.0,
        available_inventory=4,
        maximum_permitted_discount=119.0,
        delivery_cost=20.0,
        free_delivery_allowed=False,  # High-value electronic insurance mandatory
        promotional_rules=[
            "Mandatory insured courier transit fee: $20.00",
            "No free shipping permitted due to device transit insurance mandate"
        ]
    ),
}


def get_merchant_profile(
    product_id: str,
    merchant_id: Optional[str] = None,
    advertised_price: Optional[float] = None
) -> MerchantCommercialProfile:
    """
    Retrieves the merchant commercial profile for a given product or merchant ID.
    Synchronizes listed_price, preferred_price, and minimum_acceptable_price with the actual advertised_price
    so the seller agent never evaluates against a mismatched catalog price.
    """
    clean_id = str(product_id).strip()
    profile: Optional[MerchantCommercialProfile] = None

    # Check by product ID
    if clean_id in SIMULATED_MERCHANT_PROFILES:
        profile = SIMULATED_MERCHANT_PROFILES[clean_id].model_copy(deep=True)
    else:
        # Check by matching product_id suffix (e.g. 'smartwatch-1' -> 'prod-1')
        for key, p in SIMULATED_MERCHANT_PROFILES.items():
            if key in clean_id or clean_id in key:
                profile = p.model_copy(deep=True)
                break

    # If matching profile was found
    if profile is not None:
        if advertised_price is not None and advertised_price > 0:
            actual_list = round(float(advertised_price), 2)
            # Calculate discount margin proportion from profile
            orig_list = profile.listed_price
            orig_min = profile.minimum_acceptable_price
            orig_pref = profile.preferred_price or (orig_min + (orig_list - orig_min) * 0.70)
            
            discount_ratio = max(0.05, min(0.35, (orig_list - orig_min) / orig_list)) if orig_list > 0 else 0.20
            new_min = round(actual_list * (1.0 - discount_ratio), 2)

            pref_ratio = (orig_pref - orig_min) / (orig_list - orig_min) if orig_list > orig_min else 0.70
            new_pref = round(new_min + (actual_list - new_min) * pref_ratio, 2)

            profile.listed_price = actual_list
            profile.minimum_acceptable_price = new_min
            profile.preferred_price = new_pref
            profile.maximum_permitted_discount = round(actual_list - new_min, 2)
        return profile

    # Fallback safe default profile calibrated to the actual advertised price
    actual_list = round(float(advertised_price), 2) if (advertised_price is not None and advertised_price > 0) else 200.0
    min_price = round(actual_list * 0.80, 2)  # Standard 20% max discount floor
    pref_price = round(min_price + (actual_list - min_price) * 0.70, 2)
    max_discount = round(actual_list - min_price, 2)

    return MerchantCommercialProfile(
        merchant_id=merchant_id or f"merchant-{clean_id}",
        merchant_name="Verified Merchant Partner",
        product_id=clean_id,
        listed_price=actual_list,
        preferred_price=pref_price,
        minimum_acceptable_price=min_price,
        available_inventory=10,
        maximum_permitted_discount=max_discount,
        delivery_cost=15.0,
        free_delivery_allowed=True,
        promotional_rules=[
            "Standard merchant commercial guidelines apply",
            "Price cannot fall below cost floor",
            f"Maximum allowable discount is ${max_discount:.2f} below listed price"
        ]
    )
