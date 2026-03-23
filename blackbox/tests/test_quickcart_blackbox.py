import os
import uuid
from datetime import datetime, timezone

import pytest
import requests


BASE_URL = os.getenv("QUICKCART_BASE_URL", "http://localhost:8080/api/v1").rstrip("/")
ROLL_NUMBER = os.getenv("QUICKCART_ROLL", "2024001")
TIMEOUT = float(os.getenv("QUICKCART_TIMEOUT", "15"))


class APIClient:
    def __init__(self, base_url: str, roll_number: str, user_id: int | None = None):
        self.base_url = base_url
        self.roll_number = str(roll_number)
        self.user_id = user_id
        self.session = requests.Session()

    def headers(
        self,
        include_roll: bool = True,
        include_user: bool = True,
        roll_value: str | None = None,
        user_value: str | int | None = None,
    ) -> dict:
        h = {}
        if include_roll:
            h["X-Roll-Number"] = str(roll_value if roll_value is not None else self.roll_number)
        if include_user:
            uid = user_value if user_value is not None else self.user_id
            if uid is not None:
                h["X-User-ID"] = str(uid)
        return h

    def request(
        self,
        method: str,
        path: str,
        *,
        include_roll: bool = True,
        include_user: bool = True,
        roll_value: str | None = None,
        user_value: str | int | None = None,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        return self.session.request(
            method=method,
            url=url,
            headers=self.headers(
                include_roll=include_roll,
                include_user=include_user,
                roll_value=roll_value,
                user_value=user_value,
            ),
            json=json_body,
            params=params,
            timeout=TIMEOUT,
        )


def assert_status(resp: requests.Response, expected: int) -> None:
    assert resp.status_code == expected, (
        f"Expected {expected}, got {resp.status_code}. Body: {resp.text[:800]}"
    )


def safe_json(resp: requests.Response):
    try:
        return resp.json()
    except Exception:
        return None


def extract_list(payload, preferred_keys: tuple[str, ...] = ()) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in preferred_keys:
            v = payload.get(k)
            if isinstance(v, list):
                return v
        for v in payload.values():
            if isinstance(v, list):
                return v
    return []


def cart_items(cart_payload: dict) -> list:
    if not isinstance(cart_payload, dict):
        return []
    if isinstance(cart_payload.get("items"), list):
        return cart_payload["items"]
    if isinstance(cart_payload.get("cart_items"), list):
        return cart_payload["cart_items"]
    return []


def cart_total(cart_payload: dict) -> float:
    if not isinstance(cart_payload, dict):
        return 0.0
    if "total" in cart_payload:
        return float(cart_payload["total"])
    if "cart_total" in cart_payload:
        return float(cart_payload["cart_total"])
    return 0.0


def find_coupon_code(coupons: list, predicate) -> str | None:
    for c in coupons:
        code = c.get("code") or c.get("coupon_code")
        if code and predicate(c):
            return code
    return None


@pytest.fixture(scope="session")
def admin_client() -> APIClient:
    return APIClient(BASE_URL, ROLL_NUMBER)


@pytest.fixture(scope="session")
def user_id(admin_client: APIClient) -> int:
    resp = admin_client.request("GET", "/admin/users", include_user=False)
    assert_status(resp, 200)
    payload = safe_json(resp)
    users = extract_list(payload, ("users",))
    assert users, "No users available from admin endpoint"

    first = users[0]
    uid = first.get("user_id") or first.get("id")
    assert uid is not None, "Could not determine user_id field in admin users payload"
    return int(uid)


@pytest.fixture
def api(user_id: int) -> APIClient:
    return APIClient(BASE_URL, ROLL_NUMBER, user_id=user_id)


@pytest.fixture
def admin_products(admin_client: APIClient) -> list:
    resp = admin_client.request("GET", "/admin/products", include_user=False)
    assert_status(resp, 200)
    payload = safe_json(resp)
    products = extract_list(payload, ("products",))
    return products


@pytest.fixture
def active_product(admin_products: list) -> dict:
    for p in admin_products:
        if p.get("is_active") is True:
            return p
    assert False, "No active product available"


@pytest.fixture
def inactive_product(admin_products: list) -> dict:
    for p in admin_products:
        if p.get("is_active") is False:
            return p
    assert False, "No inactive product available"


@pytest.fixture
def stock_product(admin_products: list) -> dict:
    for p in admin_products:
        if p.get("is_active") is True and int(p.get("stock_quantity", 0)) > 10:
            return p
    assert False, "No sufficiently stocked active product available"


@pytest.fixture(autouse=True)
def clear_cart_before_and_after(api: APIClient):
    api.request("DELETE", "/cart/clear")
    yield
    api.request("DELETE", "/cart/clear")


# -------------------------------
# Headers and authentication
# -------------------------------

def test_header_missing_roll_returns_401(api: APIClient):
    resp = api.request("GET", "/admin/users", include_roll=False, include_user=False)
    assert_status(resp, 401)


def test_header_invalid_roll_returns_400(api: APIClient):
    resp = api.request(
        "GET",
        "/admin/users",
        include_user=False,
        roll_value="abc123",
    )
    assert_status(resp, 400)


def test_header_missing_user_on_user_endpoint_returns_400(api: APIClient):
    resp = api.request("GET", "/profile", include_user=False)
    assert_status(resp, 400)


def test_header_non_integer_user_returns_400(api: APIClient):
    resp = api.request("GET", "/profile", user_value="bad")
    assert_status(resp, 400)


def test_header_negative_user_returns_400(api: APIClient):
    resp = api.request("GET", "/profile", user_value="-9")
    assert_status(resp, 400)


def test_header_non_existing_positive_user_returns_400(api: APIClient):
    resp = api.request("GET", "/profile", user_value="9999999")
    assert_status(resp, 400)


# -------------------------------
# Profile
# -------------------------------

def test_profile_get_success_and_shape(api: APIClient):
    resp = api.request("GET", "/profile")
    assert_status(resp, 200)
    payload = safe_json(resp)
    assert isinstance(payload, dict)


@pytest.mark.parametrize(
    "name,phone,expected",
    [
        ("A", "9999999999", 400),
        ("A" * 51, "9999999999", 400),
        ("Valid Name", "123456789", 400),
        ("Valid Name", "12345678901", 400),
        ("Valid Name", "12345abcde", 400),
    ],
)
def test_profile_put_validation(api: APIClient, name: str, phone: str, expected: int):
    resp = api.request("PUT", "/profile", json_body={"name": name, "phone": phone})
    assert_status(resp, expected)


def test_profile_put_valid_data_success(api: APIClient):
    new_name = f"Test User {uuid.uuid4().hex[:6]}"
    resp = api.request(
        "PUT",
        "/profile",
        json_body={"name": new_name, "phone": "9876543210"},
    )
    assert_status(resp, 200)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": "Valid Name"},
        {"phone": "9876543210"},
    ],
)
def test_profile_put_missing_fields(api: APIClient, body: dict):
    resp = api.request("PUT", "/profile", json_body=body)
    assert_status(resp, 400)


# -------------------------------
# Addresses
# -------------------------------

def create_address(api: APIClient, label="HOME", street=None, city="Hyderabad", pincode="500001", is_default=False):
    if street is None:
        street = f"{uuid.uuid4().hex[:6]} Mango Street"
    return api.request(
        "POST",
        "/addresses",
        json_body={
            "label": label,
            "street": street,
            "city": city,
            "pincode": pincode,
            "is_default": is_default,
        },
    )


def get_address_id(resp: requests.Response) -> int | None:
    payload = safe_json(resp)
    if not isinstance(payload, dict):
        return None
    addr = payload.get("address") if isinstance(payload.get("address"), dict) else payload
    return addr.get("address_id") if isinstance(addr, dict) else None


def test_addresses_get_success(api: APIClient):
    resp = api.request("GET", "/addresses")
    assert_status(resp, 200)


def test_addresses_post_valid_success(api: APIClient):
    resp = create_address(api, label="HOME", city="Hyderabad", pincode="500001")
    assert_status(resp, 200)
    aid = get_address_id(resp)
    assert aid is not None


@pytest.mark.parametrize(
    "body,expected",
    [
        ({"label": "HOUSE", "street": "12345 Main Street", "city": "Hyd", "pincode": "500001", "is_default": False}, 400),
        ({"label": "HOME", "street": "1234", "city": "Hyd", "pincode": "500001", "is_default": False}, 400),
        ({"label": "HOME", "street": "X" * 101, "city": "Hyd", "pincode": "500001", "is_default": False}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "H", "pincode": "500001", "is_default": False}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "X" * 51, "pincode": "500001", "is_default": False}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "Hyd", "pincode": "50000", "is_default": False}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "Hyd", "pincode": "5000001", "is_default": False}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "Hyd", "pincode": "50AB01", "is_default": False}, 400),
    ],
)
def test_addresses_post_validation(api: APIClient, body: dict, expected: int):
    resp = api.request("POST", "/addresses", json_body=body)
    assert_status(resp, expected)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"street": "12345 Main Street", "city": "Hyd", "pincode": "500001", "is_default": False},
        {"label": "HOME", "city": "Hyd", "pincode": "500001", "is_default": False},
        {"label": "HOME", "street": "12345 Main Street", "pincode": "500001", "is_default": False},
        {"label": "HOME", "street": "12345 Main Street", "city": "Hyd", "is_default": False},
    ],
)
def test_addresses_post_missing_fields(api: APIClient, body: dict):
    resp = api.request("POST", "/addresses", json_body=body)
    assert_status(resp, 400)


def test_addresses_default_uniqueness(api: APIClient):
    r1 = create_address(api, label="HOME", is_default=True)
    assert_status(r1, 200)
    r2 = create_address(api, label="OFFICE", is_default=True)
    assert_status(r2, 200)

    resp = api.request("GET", "/addresses")
    assert_status(resp, 200)
    payload = safe_json(resp)
    addresses = extract_list(payload, ("addresses",))
    defaults = [a for a in addresses if a.get("is_default") is True]
    assert len(defaults) <= 1, f"More than one default address found: {defaults}"


def test_addresses_update_only_street_and_default_mutable(api: APIClient):
    create = create_address(api, label="HOME", city="Hyderabad", pincode="500001", is_default=False)
    assert_status(create, 200)
    aid = get_address_id(create)
    assert aid is not None

    update_resp = api.request(
        "PUT",
        f"/addresses/{aid}",
        json_body={
            "label": "OFFICE",
            "street": "99999 Banana Road",
            "city": "Mumbai",
            "pincode": "400001",
            "is_default": True,
        },
    )
    assert_status(update_resp, 200)

    all_resp = api.request("GET", "/addresses")
    assert_status(all_resp, 200)
    addresses = extract_list(safe_json(all_resp), ("addresses",))
    target = next((a for a in addresses if a.get("address_id") == aid), None)
    assert target is not None
    assert target.get("street") == "99999 Banana Road"
    assert target.get("label") == "HOME"
    assert target.get("city") == "Hyderabad"
    assert str(target.get("pincode")) == "500001"


def test_addresses_update_response_shows_new_data(api: APIClient):
    create = create_address(api)
    assert_status(create, 200)
    aid = get_address_id(create)
    assert aid is not None

    updated_street = "77777 Updated Street"
    update = api.request(
        "PUT",
        f"/addresses/{aid}",
        json_body={"street": updated_street, "is_default": False},
    )
    assert_status(update, 200)
    payload = safe_json(update)
    txt = str(payload)
    assert updated_street in txt, f"Updated street not reflected in response: {txt}"


def test_addresses_delete_non_existing_returns_404(api: APIClient):
    resp = api.request("DELETE", "/addresses/99999999")
    assert_status(resp, 404)


# -------------------------------
# Products
# -------------------------------

def test_products_list_only_active(api: APIClient):
    resp = api.request("GET", "/products")
    assert_status(resp, 200)
    products = extract_list(safe_json(resp), ("products",))
    assert products, "Products list should not be empty"
    assert all(p.get("is_active") is True for p in products), f"Inactive product found in list: {products}"


def test_products_get_existing_success(api: APIClient, active_product: dict):
    pid = int(active_product.get("product_id"))
    resp = api.request("GET", f"/products/{pid}")
    assert_status(resp, 200)


def test_products_get_non_existing_returns_404(api: APIClient):
    resp = api.request("GET", "/products/99999999")
    assert_status(resp, 404)


def test_products_get_inactive_should_not_be_visible(api: APIClient, inactive_product: dict):
    pid = int(inactive_product.get("product_id"))
    resp = api.request("GET", f"/products/{pid}")
    assert_status(resp, 404)


def test_products_filter_by_category(api: APIClient):
    base = api.request("GET", "/products")
    assert_status(base, 200)
    products = extract_list(safe_json(base), ("products",))
    assert products, "No active products available"
    category = products[0].get("category")
    resp = api.request("GET", "/products", params={"category": category})
    assert_status(resp, 200)
    filtered = extract_list(safe_json(resp), ("products",))
    assert filtered, "Filtered products should not be empty"
    assert all(p.get("category") == category for p in filtered)


def test_products_search_by_name(api: APIClient):
    base = api.request("GET", "/products")
    assert_status(base, 200)
    products = extract_list(safe_json(base), ("products",))
    assert products, "No products to search"
    keyword = str(products[0].get("name", "")).split(" ")[0]
    resp = api.request("GET", "/products", params={"search": keyword})
    assert_status(resp, 200)
    found = extract_list(safe_json(resp), ("products",))
    assert found, "Search should return at least one product"


@pytest.mark.parametrize(
    "order_key,reverse",
    [("price_asc", False), ("price_desc", True)],
)
def test_products_sort_by_price(api: APIClient, order_key: str, reverse: bool):
    resp = api.request("GET", "/products", params={"sort": order_key})
    assert_status(resp, 200)
    products = extract_list(safe_json(resp), ("products",))
    assert len(products) >= 2, "Not enough products to validate sorting"
    prices = [float(p.get("price", 0)) for p in products]
    assert prices == sorted(prices, reverse=reverse), f"Unexpected sort order for {order_key}: {prices}"


# -------------------------------
# Cart
# -------------------------------

def test_cart_get_success(api: APIClient):
    resp = api.request("GET", "/cart")
    assert_status(resp, 200)


def test_cart_clear_success(api: APIClient):
    resp = api.request("DELETE", "/cart/clear")
    assert_status(resp, 200)


def test_cart_add_valid_success(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    resp = api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1})
    assert_status(resp, 200)


@pytest.mark.parametrize("qty", [0, -1])
def test_cart_add_quantity_must_be_at_least_one(api: APIClient, active_product: dict, qty: int):
    pid = int(active_product["product_id"])
    resp = api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": qty})
    assert_status(resp, 400)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"product_id": 1},
        {"quantity": 1},
    ],
)
def test_cart_add_missing_fields(api: APIClient, body: dict):
    resp = api.request("POST", "/cart/add", json_body=body)
    assert_status(resp, 400)


def test_cart_add_non_existing_product_returns_404(api: APIClient):
    resp = api.request("POST", "/cart/add", json_body={"product_id": 99999999, "quantity": 1})
    assert_status(resp, 404)


def test_cart_add_over_stock_returns_400(api: APIClient, stock_product: dict):
    pid = int(stock_product["product_id"])
    stock = int(stock_product.get("stock_quantity", 0))
    resp = api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": stock + 1})
    assert_status(resp, 400)


def test_cart_add_same_product_accumulates_quantity(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 2}), 200)
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 3}), 200)

    cart_resp = api.request("GET", "/cart")
    assert_status(cart_resp, 200)
    items = cart_items(safe_json(cart_resp))
    item = next((x for x in items if int(x.get("product_id", -1)) == pid), None)
    assert item is not None
    assert int(item.get("quantity", 0)) == 5


def test_cart_update_valid_quantity(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1}), 200)
    update = api.request("POST", "/cart/update", json_body={"product_id": pid, "quantity": 4})
    assert_status(update, 200)


@pytest.mark.parametrize("qty", [0, -5])
def test_cart_update_quantity_must_be_at_least_one(api: APIClient, active_product: dict, qty: int):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1}), 200)
    resp = api.request("POST", "/cart/update", json_body={"product_id": pid, "quantity": qty})
    assert_status(resp, 400)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"product_id": 1},
        {"quantity": 2},
    ],
)
def test_cart_update_missing_fields(api: APIClient, body: dict):
    resp = api.request("POST", "/cart/update", json_body=body)
    assert_status(resp, 400)


def test_cart_remove_missing_product_returns_404(api: APIClient):
    resp = api.request("POST", "/cart/remove", json_body={"product_id": 99999999})
    assert_status(resp, 404)


def test_cart_item_subtotal_is_quantity_times_unit_price(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 4}), 200)
    cart_resp = api.request("GET", "/cart")
    assert_status(cart_resp, 200)
    payload = safe_json(cart_resp)
    items = cart_items(payload)
    item = next((x for x in items if int(x.get("product_id", -1)) == pid), None)
    assert item is not None
    unit = float(item.get("unit_price", item.get("price", 0)))
    qty = float(item.get("quantity", 0))
    subtotal = float(item.get("subtotal", item.get("item_total", 0)))
    assert subtotal == pytest.approx(unit * qty, abs=0.01)


def test_cart_total_is_sum_of_subtotals(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 2}), 200)
    cart_resp = api.request("GET", "/cart")
    assert_status(cart_resp, 200)
    payload = safe_json(cart_resp)
    items = cart_items(payload)
    expected = 0.0
    for item in items:
        expected += float(item.get("subtotal", item.get("item_total", 0)))
    actual = cart_total(payload)
    assert actual == pytest.approx(expected, abs=0.01)


# -------------------------------
# Coupons
# -------------------------------

def test_coupon_apply_missing_code_returns_400(api: APIClient):
    resp = api.request("POST", "/coupon/apply", json_body={})
    assert_status(resp, 400)


def test_coupon_apply_expired_coupon_rejected(api: APIClient, admin_client: APIClient, active_product: dict):
    # Fill cart to meet minimum for many coupons.
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 50}), 200)

    coup_resp = admin_client.request("GET", "/admin/coupons", include_user=False)
    assert_status(coup_resp, 200)
    coupons = extract_list(safe_json(coup_resp), ("coupons",))

    def is_expired(c: dict) -> bool:
        dt = c.get("expiry_date") or c.get("expires_at")
        if not dt:
            return False
        try:
            parsed = datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
        except Exception:
            return False
        return parsed < datetime.now(timezone.utc)

    code = find_coupon_code(coupons, is_expired)
    assert code, "No expired coupon found in admin data"

    resp = api.request("POST", "/coupon/apply", json_body={"code": code})
    assert_status(resp, 400)


def test_coupon_apply_below_minimum_cart_rejected(api: APIClient, admin_client: APIClient):
    coup_resp = admin_client.request("GET", "/admin/coupons", include_user=False)
    assert_status(coup_resp, 200)
    coupons = extract_list(safe_json(coup_resp), ("coupons",))
    code = find_coupon_code(coupons, lambda c: float(c.get("min_cart_value", 0)) >= 500)
    assert code, "No coupon with meaningful min cart value found"

    resp = api.request("POST", "/coupon/apply", json_body={"code": code})
    assert_status(resp, 400)


def test_coupon_remove_success_or_idempotent(api: APIClient):
    resp = api.request("POST", "/coupon/remove", json_body={})
    assert resp.status_code in (200, 400), f"Unexpected status: {resp.status_code}, body={resp.text}"


# -------------------------------
# Checkout
# -------------------------------

def test_checkout_empty_cart_rejected(api: APIClient):
    api.request("DELETE", "/cart/clear")
    resp = api.request("POST", "/checkout", json_body={"payment_method": "COD"})
    assert_status(resp, 400)


@pytest.mark.parametrize("body", [{}, {"method": "COD"}])
def test_checkout_missing_payment_method_rejected(api: APIClient, body: dict):
    resp = api.request("POST", "/checkout", json_body=body)
    assert_status(resp, 400)


def test_checkout_invalid_payment_method_rejected(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1}), 200)
    resp = api.request("POST", "/checkout", json_body={"payment_method": "BITCOIN"})
    assert_status(resp, 400)


def test_checkout_cod_above_5000_rejected(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 50}), 200)
    resp = api.request("POST", "/checkout", json_body={"payment_method": "COD"})
    assert_status(resp, 400)


def test_checkout_card_sets_paid_status(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1}), 200)
    resp = api.request("POST", "/checkout", json_body={"payment_method": "CARD"})
    assert_status(resp, 200)
    payload = safe_json(resp) or {}
    assert str(payload.get("payment_status", "")).upper() == "PAID"


def test_checkout_cod_sets_pending_status(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1}), 200)
    resp = api.request("POST", "/checkout", json_body={"payment_method": "COD"})
    assert_status(resp, 200)
    payload = safe_json(resp) or {}
    assert str(payload.get("payment_status", "")).upper() == "PENDING"


def test_checkout_wallet_sets_pending_status(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1}), 200)
    resp = api.request("POST", "/checkout", json_body={"payment_method": "WALLET"})
    assert_status(resp, 200)
    payload = safe_json(resp) or {}
    assert str(payload.get("payment_status", "")).upper() == "PENDING"


# -------------------------------
# Wallet
# -------------------------------

def read_wallet_balance(api: APIClient) -> float:
    resp = api.request("GET", "/wallet")
    assert_status(resp, 200)
    payload = safe_json(resp) or {}
    if "wallet_balance" in payload:
        return float(payload["wallet_balance"])
    if "balance" in payload:
        return float(payload["balance"])
    assert False, "Wallet response has no recognized balance field"


def test_wallet_get_success(api: APIClient):
    resp = api.request("GET", "/wallet")
    assert_status(resp, 200)


@pytest.mark.parametrize(
    "amount,expected",
    [(0, 400), (-1, 400), (100001, 400)],
)
def test_wallet_add_validation(api: APIClient, amount: int, expected: int):
    resp = api.request("POST", "/wallet/add", json_body={"amount": amount})
    assert_status(resp, expected)


def test_wallet_add_missing_amount_rejected(api: APIClient):
    resp = api.request("POST", "/wallet/add", json_body={})
    assert_status(resp, 400)


@pytest.mark.parametrize("amount", [0, -5])
def test_wallet_pay_validation(api: APIClient, amount: int):
    resp = api.request("POST", "/wallet/pay", json_body={"amount": amount})
    assert_status(resp, 400)


def test_wallet_pay_missing_amount_rejected(api: APIClient):
    resp = api.request("POST", "/wallet/pay", json_body={})
    assert_status(resp, 400)


def test_wallet_pay_insufficient_balance_rejected(api: APIClient):
    bal = read_wallet_balance(api)
    resp = api.request("POST", "/wallet/pay", json_body={"amount": bal + 9999})
    assert_status(resp, 400)


def test_wallet_arithmetic_exact_deduction(api: APIClient):
    before = read_wallet_balance(api)
    assert_status(api.request("POST", "/wallet/add", json_body={"amount": 50}), 200)
    mid = read_wallet_balance(api)
    assert mid == pytest.approx(before + 50, abs=0.01)

    assert_status(api.request("POST", "/wallet/pay", json_body={"amount": 10}), 200)
    after = read_wallet_balance(api)
    assert after == pytest.approx(mid - 10, abs=0.01)


def test_wallet_checkout_insufficient_balance_rejected(api: APIClient, active_product: dict):
    bal = read_wallet_balance(api)
    pid = int(active_product["product_id"])
    # Force a big order likely above wallet balance.
    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 50}), 200)
    checkout = api.request("POST", "/checkout", json_body={"payment_method": "WALLET"})

    if checkout.status_code == 200:
        payload = safe_json(checkout) or {}
        total = float(payload.get("total_amount", 0))
        assert total <= bal, (
            f"WALLET checkout succeeded with insufficient funds. Balance={bal}, total={total}, body={checkout.text}"
        )
    else:
        assert_status(checkout, 400)


# -------------------------------
# Loyalty
# -------------------------------

def test_loyalty_get_success(api: APIClient):
    resp = api.request("GET", "/loyalty")
    assert_status(resp, 200)


def test_loyalty_redeem_zero_rejected(api: APIClient):
    resp = api.request("POST", "/loyalty/redeem", json_body={"points": 0})
    assert_status(resp, 400)


def test_loyalty_redeem_over_balance_rejected(api: APIClient):
    l = api.request("GET", "/loyalty")
    assert_status(l, 200)
    payload = safe_json(l) or {}
    points = int(payload.get("points", payload.get("loyalty_points", 0)))
    resp = api.request("POST", "/loyalty/redeem", json_body={"points": points + 10})
    assert_status(resp, 400)


def test_loyalty_redeem_missing_points_rejected(api: APIClient):
    resp = api.request("POST", "/loyalty/redeem", json_body={})
    assert_status(resp, 400)


# -------------------------------
# Orders
# -------------------------------

def test_orders_list_success(api: APIClient):
    resp = api.request("GET", "/orders")
    assert_status(resp, 200)


def test_orders_get_non_existing_returns_404(api: APIClient):
    resp = api.request("GET", "/orders/99999999")
    assert_status(resp, 404)


def test_orders_invoice_non_existing_returns_404(api: APIClient):
    resp = api.request("GET", "/orders/99999999/invoice")
    assert_status(resp, 404)


def test_orders_cancel_non_existing_returns_404(api: APIClient):
    resp = api.request("POST", "/orders/99999999/cancel")
    assert_status(resp, 404)


def test_orders_cancel_restores_stock(api: APIClient, admin_client: APIClient, stock_product: dict):
    pid = int(stock_product["product_id"])

    before_resp = admin_client.request("GET", "/admin/products", include_user=False)
    assert_status(before_resp, 200)
    before_products = extract_list(safe_json(before_resp), ("products",))
    before_obj = next((p for p in before_products if int(p.get("product_id", -1)) == pid), None)
    assert before_obj is not None
    before_stock = int(before_obj.get("stock_quantity", 0))

    assert_status(api.request("POST", "/cart/add", json_body={"product_id": pid, "quantity": 1}), 200)
    checkout = api.request("POST", "/checkout", json_body={"payment_method": "COD"})
    assert_status(checkout, 200)
    cp = safe_json(checkout) or {}
    order_id = cp.get("order_id")
    assert order_id is not None

    cancel = api.request("POST", f"/orders/{order_id}/cancel")
    assert_status(cancel, 200)

    after_resp = admin_client.request("GET", "/admin/products", include_user=False)
    assert_status(after_resp, 200)
    after_products = extract_list(safe_json(after_resp), ("products",))
    after_obj = next((p for p in after_products if int(p.get("product_id", -1)) == pid), None)
    assert after_obj is not None
    after_stock = int(after_obj.get("stock_quantity", 0))

    assert after_stock == before_stock, (
        f"Stock not restored after cancellation. before={before_stock}, after={after_stock}, order_id={order_id}"
    )


def test_orders_cancel_delivered_returns_400(api: APIClient, admin_client: APIClient):
    orders_resp = admin_client.request("GET", "/admin/orders", include_user=False)
    assert_status(orders_resp, 200)
    orders = extract_list(safe_json(orders_resp), ("orders",))
    delivered = next(
        (
            o
            for o in orders
            if str(o.get("order_status", o.get("status", ""))).upper() == "DELIVERED"
        ),
        None,
    )
    assert delivered is not None, "No delivered order available in admin orders data"

    oid = delivered.get("order_id")
    uid = delivered.get("user_id")
    assert oid is not None, "Delivered order missing order_id"
    assert uid is not None, "Delivered order missing user_id"
    resp = api.request("POST", f"/orders/{oid}/cancel", user_value=uid)
    assert_status(resp, 400)


# -------------------------------
# Reviews
# -------------------------------

def test_reviews_get_existing_product_success(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    resp = api.request("GET", f"/products/{pid}/reviews")
    assert_status(resp, 200)


def test_reviews_post_valid_review_success(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    resp = api.request(
        "POST",
        f"/products/{pid}/reviews",
        json_body={"rating": 5, "comment": "Great product"},
    )
    assert_status(resp, 200)


@pytest.mark.parametrize(
    "body,expected",
    [
        ({"rating": 0, "comment": "bad"}, 400),
        ({"rating": 6, "comment": "bad"}, 400),
        ({"comment": "missing rating"}, 400),
        ({"rating": 5, "comment": ""}, 400),
        ({"rating": 5, "comment": "X" * 201}, 400),
    ],
)
def test_reviews_validation(api: APIClient, active_product: dict, body: dict, expected: int):
    pid = int(active_product["product_id"])
    resp = api.request("POST", f"/products/{pid}/reviews", json_body=body)
    assert_status(resp, expected)


def test_reviews_missing_comment_rejected(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    resp = api.request("POST", f"/products/{pid}/reviews", json_body={"rating": 5})
    assert_status(resp, 400)


def test_reviews_non_existing_product_create_returns_404(api: APIClient):
    resp = api.request(
        "POST",
        "/products/99999999/reviews",
        json_body={"rating": 4, "comment": "ok"},
    )
    assert_status(resp, 404)


def test_reviews_non_existing_product_list_returns_404(api: APIClient):
    resp = api.request("GET", "/products/99999999/reviews")
    assert_status(resp, 404)


def test_reviews_average_in_range(api: APIClient, active_product: dict):
    pid = int(active_product["product_id"])
    resp = api.request("GET", f"/products/{pid}/reviews")
    assert_status(resp, 200)
    payload = safe_json(resp) or {}
    avg = float(payload.get("average_rating", 0))
    assert 0 <= avg <= 5


# -------------------------------
# Support tickets
# -------------------------------

def create_ticket(api: APIClient, subject: str, message: str) -> requests.Response:
    return api.request("POST", "/support/ticket", json_body={"subject": subject, "message": message})


def list_tickets(api: APIClient) -> list:
    resp = api.request("GET", "/support/tickets")
    assert_status(resp, 200)
    return extract_list(safe_json(resp), ("tickets",))


def find_ticket_by_subject(api: APIClient, subject: str) -> dict | None:
    tickets = list_tickets(api)
    for t in tickets:
        if t.get("subject") == subject:
            return t
    return None


def test_support_ticket_create_success_status_open(api: APIClient):
    subject = f"Ticket {uuid.uuid4().hex[:8]}"
    resp = create_ticket(api, subject=subject, message="Need help with checkout")
    assert_status(resp, 200)
    payload = safe_json(resp) or {}
    text = str(payload).upper()
    assert "OPEN" in text


@pytest.mark.parametrize(
    "subject,message,expected",
    [
        ("hey", "valid message", 400),
        ("X" * 101, "valid message", 400),
        ("Valid subject", "", 400),
        ("Valid subject", "X" * 501, 400),
    ],
)
def test_support_ticket_validation(api: APIClient, subject: str, message: str, expected: int):
    resp = create_ticket(api, subject=subject, message=message)
    assert_status(resp, expected)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"subject": "Valid subject"},
        {"message": "Valid message"},
    ],
)
def test_support_ticket_missing_fields(api: APIClient, body: dict):
    resp = api.request("POST", "/support/ticket", json_body=body)
    assert_status(resp, 400)


def test_support_ticket_long_valid_message_preserved(api: APIClient):
    token = uuid.uuid4().hex
    message = ("A" * 490) + token[:10]
    subject = f"LongMsg {uuid.uuid4().hex[:8]}"

    create = create_ticket(api, subject=subject, message=message)
    assert_status(create, 200)

    ticket = find_ticket_by_subject(api, subject)
    assert ticket is not None, "Created ticket not found in ticket list"
    stored = str(ticket.get("message", ""))
    assert stored == message, f"Stored message differs. sent_len={len(message)}, got_len={len(stored)}"


def test_support_ticket_status_transition_constraints(api: APIClient):
    subject = f"Flow {uuid.uuid4().hex[:8]}"
    create = create_ticket(api, subject=subject, message="Please process")
    assert_status(create, 200)

    payload = safe_json(create) or {}
    tid = payload.get("ticket_id")
    if not tid and isinstance(payload.get("ticket"), dict):
        tid = payload["ticket"].get("ticket_id")
    if not tid:
        t = find_ticket_by_subject(api, subject)
        if t:
            tid = t.get("ticket_id")
    assert tid is not None, "Could not identify ticket_id from create/list response"

    # Invalid jump OPEN -> CLOSED should be rejected.
    invalid = api.request("PUT", f"/support/tickets/{tid}", json_body={"status": "CLOSED"})
    assert_status(invalid, 400)

    # Valid transitions should succeed.
    step1 = api.request("PUT", f"/support/tickets/{tid}", json_body={"status": "IN_PROGRESS"})
    assert_status(step1, 200)
    step2 = api.request("PUT", f"/support/tickets/{tid}", json_body={"status": "CLOSED"})
    assert_status(step2, 200)
