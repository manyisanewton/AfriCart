def create_customer_headers(client, *, email="address-user@example.com", phone="+254733000111"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "first_name": "Address",
            "last_name": "User",
            "phone_number": phone,
        },
    )
    token = response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def address_payload(**overrides):
    payload = {
        "label": "Home",
        "recipient_name": "Address User",
        "phone_number": "+254733000111",
        "country": "Kenya",
        "city": "Nairobi",
        "state_or_county": "Nairobi County",
        "postal_code": "00100",
        "address_line_1": "Moi Avenue",
        "address_line_2": "2nd Floor",
        "is_default": False,
    }
    payload.update(overrides)
    return payload


def test_create_and_list_addresses(client):
    headers = create_customer_headers(client)

    create_response = client.post(
        "/api/v1/addresses",
        json=address_payload(),
        headers=headers,
    )
    list_response = client.get("/api/v1/addresses", headers=headers)

    assert create_response.status_code == 201
    assert create_response.get_json()["item"]["is_default"] is True
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1


def test_set_default_address(client):
    headers = create_customer_headers(client)
    first = client.post("/api/v1/addresses", json=address_payload(label="Home"), headers=headers)
    second = client.post(
        "/api/v1/addresses",
        json=address_payload(label="Office", phone_number="+254733000112"),
        headers=headers,
    )

    response = client.post(
        f"/api/v1/addresses/{second.get_json()['item']['id']}/default",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["label"] == "Office"
    assert response.get_json()["item"]["is_default"] is True

    list_response = client.get("/api/v1/addresses", headers=headers)
    items = list_response.get_json()["items"]
    assert items[0]["label"] == "Office"
    assert any(item["label"] == "Home" and item["is_default"] is False for item in items)


def test_delete_default_address_promotes_latest_remaining_address(client):
    headers = create_customer_headers(client)
    first = client.post("/api/v1/addresses", json=address_payload(label="Home"), headers=headers)
    second = client.post(
        "/api/v1/addresses",
        json=address_payload(label="Office", phone_number="+254733000112"),
        headers=headers,
    )

    delete_response = client.delete(
        f"/api/v1/addresses/{first.get_json()['item']['id']}",
        headers=headers,
    )
    list_response = client.get("/api/v1/addresses", headers=headers)

    assert delete_response.status_code == 200
    items = list_response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["label"] == "Office"
    assert items[0]["is_default"] is True


def test_user_cannot_access_another_users_address(client):
    first_headers = create_customer_headers(client)
    second_headers = create_customer_headers(
        client,
        email="another-address@example.com",
        phone="+254733000999",
    )
    create_response = client.post(
        "/api/v1/addresses",
        json=address_payload(),
        headers=first_headers,
    )

    response = client.patch(
        f"/api/v1/addresses/{create_response.get_json()['item']['id']}",
        json=address_payload(label="Changed"),
        headers=second_headers,
    )

    assert response.status_code == 404
