from app.extensions import db
from datetime import datetime, timedelta, timezone

from app.models import Address, Brand, Category, Product, ProductView, RecommendationEvent, User, UserRole, Vendor, VendorStatus, WishlistItem
from app.utils.security import hash_password


def create_customer_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "recommend-user@example.com",
            "password": "SecurePass123",
            "first_name": "Recommend",
            "last_name": "User",
            "phone_number": "+254799000111",
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_recommendation_catalog():
    vendor_user = User(
        email="recommend-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Signals",
        phone_number="+254799000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Recommendation Tech",
        slug="recommendation-tech",
        phone_number="+254799000222",
        support_email="support@recommendationtech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    phones = Category(name="Phones", slug="phones")
    accessories = Category(name="Accessories", slug="accessories")
    samsung = Brand(name="Samsung", slug="samsung-rec")
    anker = Brand(name="Anker", slug="anker-rec")

    seed_phone = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Samsung Galaxy Seed",
        slug="samsung-galaxy-seed",
        sku="SAMSUNG-SEED",
        price=60000,
        stock_quantity=4,
        is_featured=False,
    )
    recommended_phone = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Samsung Galaxy Match",
        slug="samsung-galaxy-match",
        sku="SAMSUNG-MATCH",
        price=70000,
        stock_quantity=6,
        is_featured=True,
    )
    fallback_product = Product(
        vendor=vendor,
        category=accessories,
        brand=anker,
        name="Anker Charger Pro",
        slug="anker-charger-pro",
        sku="ANKER-PRO",
        price=4500,
        stock_quantity=10,
        is_featured=True,
    )
    db.session.add_all(
        [
            vendor_user,
            vendor,
            phones,
            accessories,
            samsung,
            anker,
            seed_phone,
            recommended_phone,
            fallback_product,
        ]
    )
    db.session.commit()
    return seed_phone, recommended_phone, fallback_product


def test_recommendations_fallback_for_new_user(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 3
    assert items[0]["slug"] in {recommended_phone.slug, fallback_product.slug}


def test_recommendations_use_user_signals_and_exclude_seed_product(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    add_response = client.post(
        "/api/v1/wishlist/items",
        json={"product_id": seed_phone.id},
        headers=headers,
    )
    assert add_response.status_code == 201

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items[0]["slug"] == recommended_phone.slug
    assert items[0]["reason_code"] == "similar_brand_preference"
    assert items[0]["reason_label"]
    assert all(item["slug"] != seed_phone.slug for item in items)


def test_product_view_signal_is_recorded_and_used_for_recommendations(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    view_response = client.post(
        f"/api/v1/products/{seed_phone.slug}/view",
        headers=headers,
    )

    assert view_response.status_code == 200
    assert view_response.get_json()["item"]["view_count"] == 1
    product_view = ProductView.query.filter_by(product_id=seed_phone.id).first()
    assert product_view is not None

    recommendations_response = client.get("/api/v1/products/recommendations", headers=headers)

    assert recommendations_response.status_code == 200
    items = recommendations_response.get_json()["items"]
    assert items[0]["slug"] == recommended_phone.slug
    assert all(item["slug"] != seed_phone.slug for item in items)


def test_recently_viewed_products_are_returned_in_latest_first_order(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    first_response = client.post(f"/api/v1/products/{seed_phone.slug}/view", headers=headers)
    assert first_response.status_code == 200
    second_response = client.post(f"/api/v1/products/{fallback_product.slug}/view", headers=headers)
    assert second_response.status_code == 200
    third_response = client.post(f"/api/v1/products/{seed_phone.slug}/view", headers=headers)
    assert third_response.status_code == 200

    response = client.get("/api/v1/products/recently-viewed", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items[0]["product"]["slug"] == seed_phone.slug
    assert items[0]["view_count"] == 2
    assert items[1]["product"]["slug"] == fallback_product.slug


def test_recent_signals_outweigh_old_signals_in_recommendations(client):
    headers = create_customer_headers(client)

    vendor_user = User(
        email="recommend-recency-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Recency",
        phone_number="+254799000333",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Recommendation Recency Tech",
        slug="recommendation-recency-tech",
        phone_number="+254799000333",
        support_email="support@recommendationrecencytech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    phones = Category(name="Recency Phones", slug="recency-phones")
    audio = Category(name="Recency Audio", slug="recency-audio")
    samsung = Brand(name="Samsung Recency", slug="samsung-recency")
    sony = Brand(name="Sony Recency", slug="sony-recency")

    old_seed = Product(
        vendor=vendor,
        category=audio,
        brand=sony,
        name="Old Signal Seed",
        slug="old-signal-seed",
        sku="OLD-SIGNAL-SEED",
        price=9000,
        stock_quantity=4,
        is_active=True,
    )
    old_candidate = Product(
        vendor=vendor,
        category=audio,
        brand=sony,
        name="Old Signal Candidate",
        slug="old-signal-candidate",
        sku="OLD-SIGNAL-CANDIDATE",
        price=9500,
        stock_quantity=5,
        is_active=True,
    )
    recent_seed = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Recent Signal Seed",
        slug="recent-signal-seed",
        sku="RECENT-SIGNAL-SEED",
        price=65000,
        stock_quantity=3,
        is_active=True,
    )
    recent_candidate = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Recent Signal Candidate",
        slug="recent-signal-candidate",
        sku="RECENT-SIGNAL-CANDIDATE",
        price=72000,
        stock_quantity=6,
        is_active=True,
    )
    db.session.add_all(
        [
            vendor_user,
            vendor,
            phones,
            audio,
            samsung,
            sony,
            old_seed,
            old_candidate,
            recent_seed,
            recent_candidate,
        ]
    )
    db.session.commit()

    user = User.query.filter_by(email="recommend-user@example.com").first()
    db.session.add_all(
        [
            ProductView(
                user_id=user.id,
                product_id=old_seed.id,
                view_count=1,
                first_viewed_at=datetime.now(timezone.utc) - timedelta(days=90),
                last_viewed_at=datetime.now(timezone.utc) - timedelta(days=90),
            ),
            ProductView(
                user_id=user.id,
                product_id=recent_seed.id,
                view_count=1,
                first_viewed_at=datetime.now(timezone.utc) - timedelta(days=2),
                last_viewed_at=datetime.now(timezone.utc) - timedelta(days=2),
            ),
        ]
    )
    db.session.commit()

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items[0]["slug"] == recent_candidate.slug
    assert any(item["slug"] == old_candidate.slug for item in items)


def test_price_affinity_prefers_closer_price_candidates(client):
    headers = create_customer_headers(client)

    vendor_user = User(
        email="recommend-price-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Price",
        phone_number="+254799000444",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Recommendation Price Tech",
        slug="recommendation-price-tech",
        phone_number="+254799000444",
        support_email="support@recommendationpricetech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Price Laptops", slug="price-laptops")
    brand = Brand(name="Lenovo Price", slug="lenovo-price")

    seed_product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Price Signal Seed",
        slug="price-signal-seed",
        sku="PRICE-SIGNAL-SEED",
        price=10000,
        stock_quantity=4,
        is_active=True,
    )
    close_price_candidate = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Close Price Candidate",
        slug="close-price-candidate",
        sku="CLOSE-PRICE-CANDIDATE",
        price=11000,
        stock_quantity=4,
        is_active=True,
    )
    far_price_candidate = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="Far Price Candidate",
        slug="far-price-candidate",
        sku="FAR-PRICE-CANDIDATE",
        price=50000,
        stock_quantity=4,
        is_active=True,
    )
    db.session.add_all(
        [
            vendor_user,
            vendor,
            category,
            brand,
            seed_product,
            close_price_candidate,
            far_price_candidate,
        ]
    )
    db.session.commit()

    add_response = client.post(
        "/api/v1/wishlist/items",
        json={"product_id": seed_product.id},
        headers=headers,
    )
    assert add_response.status_code == 201

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items[0]["slug"] == close_price_candidate.slug
    assert any(item["slug"] == far_price_candidate.slug for item in items)


def test_recommendations_apply_diversity_caps_before_filling_remaining_slots(client):
    headers = create_customer_headers(client)

    vendor_user = User(
        email="recommend-diversity-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Diversity",
        phone_number="+254799000555",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Recommendation Diversity Tech",
        slug="recommendation-diversity-tech",
        phone_number="+254799000555",
        support_email="support@recommendationdiversitytech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    phones = Category(name="Diversity Phones", slug="diversity-phones")
    accessories = Category(name="Diversity Accessories", slug="diversity-accessories")
    samsung = Brand(name="Samsung Diversity", slug="samsung-diversity")
    anker = Brand(name="Anker Diversity", slug="anker-diversity")

    seed_product = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Diversity Seed",
        slug="diversity-seed",
        sku="DIVERSITY-SEED",
        price=60000,
        stock_quantity=3,
        is_active=True,
    )
    same_brand_one = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Same Brand One",
        slug="same-brand-one",
        sku="SAME-BRAND-ONE",
        price=61000,
        stock_quantity=5,
        is_active=True,
        is_featured=True,
    )
    same_brand_two = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Same Brand Two",
        slug="same-brand-two",
        sku="SAME-BRAND-TWO",
        price=62000,
        stock_quantity=5,
        is_active=True,
        is_featured=True,
    )
    same_brand_three = Product(
        vendor=vendor,
        category=phones,
        brand=samsung,
        name="Same Brand Three",
        slug="same-brand-three",
        sku="SAME-BRAND-THREE",
        price=63000,
        stock_quantity=5,
        is_active=True,
        is_featured=True,
    )
    different_brand = Product(
        vendor=vendor,
        category=phones,
        brand=anker,
        name="Different Brand Match",
        slug="different-brand-match",
        sku="DIFFERENT-BRAND-MATCH",
        price=59000,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all(
        [
            vendor_user,
            vendor,
            phones,
            accessories,
            samsung,
            anker,
            seed_product,
            same_brand_one,
            same_brand_two,
            same_brand_three,
            different_brand,
        ]
    )
    db.session.commit()

    add_response = client.post(
        "/api/v1/wishlist/items",
        json={"product_id": seed_product.id},
        headers=headers,
    )
    assert add_response.status_code == 201

    response = client.get("/api/v1/products/recommendations?limit=4", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    slugs = [item["slug"] for item in items]
    same_brand_slugs = {"same-brand-one", "same-brand-two", "same-brand-three"}
    assert len([slug for slug in slugs if slug in same_brand_slugs]) == 2
    assert "different-brand-match" in slugs


def test_recommendations_blend_popularity_and_trending_for_new_users(client):
    headers = create_customer_headers(client)

    vendor_user = User(
        email="recommend-trending-vendor@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Trending",
        phone_number="+254799000666",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Recommendation Trending Tech",
        slug="recommendation-trending-tech",
        phone_number="+254799000666",
        support_email="support@recommendationtrendingtech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Trending Tablets", slug="trending-tablets")
    trending_brand = Brand(name="Trending Brand", slug="trending-brand")
    featured_brand = Brand(name="Featured Brand", slug="featured-brand")

    trending_product = Product(
        vendor=vendor,
        category=category,
        brand=trending_brand,
        name="Trending Momentum Pick",
        slug="trending-momentum-pick",
        sku="TRENDING-MOMENTUM-PICK",
        price=35000,
        stock_quantity=8,
        is_active=True,
    )
    featured_product = Product(
        vendor=vendor,
        category=category,
        brand=featured_brand,
        name="Featured Backup Pick",
        slug="featured-backup-pick",
        sku="FEATURED-BACKUP-PICK",
        price=34000,
        stock_quantity=8,
        is_active=True,
        is_featured=True,
    )
    quiet_product = Product(
        vendor=vendor,
        category=category,
        brand=featured_brand,
        name="Quiet Catalog Pick",
        slug="quiet-catalog-pick",
        sku="QUIET-CATALOG-PICK",
        price=33000,
        stock_quantity=8,
        is_active=True,
    )
    db.session.add_all(
        [
            vendor_user,
            vendor,
            category,
            trending_brand,
            featured_brand,
            trending_product,
            featured_product,
            quiet_product,
        ]
    )
    db.session.commit()

    recent_customers = []
    for index in range(3):
        user = User(
            email=f"trend-user-{index}@example.com",
            password_hash=hash_password("SecurePass123"),
            first_name="Trend",
            last_name=f"User{index}",
            phone_number=f"+25479910066{index}",
            role=UserRole.CUSTOMER,
        )
        recent_customers.append(user)
    db.session.add_all(recent_customers)
    db.session.commit()

    now = datetime.now(timezone.utc)
    for user in recent_customers:
        db.session.add(
            ProductView(
                user_id=user.id,
                product_id=trending_product.id,
                view_count=3,
                first_viewed_at=now - timedelta(days=1),
                last_viewed_at=now - timedelta(days=1),
            )
        )
        db.session.add(
            WishlistItem(
                user_id=user.id,
                product_id=trending_product.id,
                created_at=now - timedelta(days=2),
            )
        )
    db.session.commit()

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert items[0]["slug"] == trending_product.slug
    assert items[0]["reason_code"] == "trending_now"
    assert items[0]["reason_label"] == "Trending now"


def test_recommendations_support_trending_mode(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    response = client.get(
        "/api/v1/products/recommendations?mode=trending_now",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "trending_now"
    assert payload["items"]
    assert all(item["reason_code"] in {"trending_now", "popular_now"} for item in payload["items"])


def test_recommendations_support_similar_products_mode(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    response = client.get(
        f"/api/v1/products/recommendations?mode=similar_products&product_slug={seed_phone.slug}",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "similar_products"
    assert payload["items"][0]["slug"] == recommended_phone.slug
    assert all(item["reason_code"] == "similar_to_product" for item in payload["items"])


def test_recommendations_support_buy_again_mode(client):
    headers = create_customer_headers(client)
    customer = User.query.filter_by(email="recommend-user@example.com").first()
    address = Address(
        user_id=customer.id,
        label="Home",
        recipient_name="Recommend User",
        phone_number="+254799000111",
        country="Kenya",
        city="Nairobi",
        address_line_1="Moi Avenue",
        is_default=True,
    )
    db.session.add(address)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()
    db.session.commit()

    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": seed_phone.id, "quantity": 2},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    assert order_response.status_code == 201

    response = client.get(
        "/api/v1/products/recommendations?mode=buy_again",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "buy_again"
    assert payload["items"][0]["slug"] == seed_phone.slug
    assert payload["items"][0]["reason_code"] == "buy_again"


def test_recommendations_reject_invalid_mode(client):
    headers = create_customer_headers(client)

    response = client.get(
        "/api/v1/products/recommendations?mode=unknown_mode",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_mode"


def test_recommendations_record_impression_and_click_events(client):
    headers = create_customer_headers(client)
    seed_phone, recommended_phone, fallback_product = seed_recommendation_catalog()

    response = client.get("/api/v1/products/recommendations", headers=headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert RecommendationEvent.query.filter_by(event_type="impression").count() == len(items)

    click_response = client.post(
        "/api/v1/products/recommendations/click",
        json={
            "product_id": items[0]["id"],
            "mode": response.get_json()["mode"],
            "reason_code": items[0]["reason_code"],
        },
        headers=headers,
    )

    assert click_response.status_code == 200
    click_event = RecommendationEvent.query.filter_by(event_type="click").first()
    assert click_event is not None
    assert click_event.product_id == items[0]["id"]
