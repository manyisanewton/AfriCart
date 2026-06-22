import api from "./api";

function getAccessToken() {
  const candidates = [
    window.localStorage.getItem("access_token"),
    window.localStorage.getItem("authToken"),
    window.localStorage.getItem("token"),
    window.localStorage.getItem("techhive_access_token"),
  ].filter(Boolean);

  if (candidates.length) {
    return candidates[0];
  }

  const serializedAuth = window.localStorage.getItem("auth");
  if (!serializedAuth) {
    return null;
  }

  try {
    const parsed = JSON.parse(serializedAuth);
    return parsed?.tokens?.access_token || parsed?.access_token || null;
  } catch (error) {
    return null;
  }
}

function buildHeaders() {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getCheckoutOrder(trackingToken) {
  const response = await api.get(`/checkout/orders/${trackingToken}`, {
    headers: buildHeaders(),
  });
  return response.data.item;
}

export async function createCheckoutPayment(payload) {
  const response = await api.post("/checkout/payments", payload, {
    headers: buildHeaders(),
  });
  return response.data.item;
}
