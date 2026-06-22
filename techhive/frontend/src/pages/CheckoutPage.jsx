import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCheckoutOrder, quoteCheckoutOrder } from "../services/orderService";
import "../styles/checkout.css";

export default function CheckoutPage({ cart, setCart }) {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [quoting, setQuoting] = useState(false);
  const [error, setError] = useState("");
  const [quoteError, setQuoteError] = useState("");
  const [quote, setQuote] = useState(null);
  const [locationStatus, setLocationStatus] = useState("");
  const [deliveryLocation, setDeliveryLocation] = useState(null);
  const [form, setForm] = useState({
    email: "",
    name: "",
    phone_number: "",
    country: "Kenya",
    city: "Nairobi",
    state_or_county: "",
    postal_code: "",
    address_line_1: "",
    address_line_2: "",
    notes: "",
  });

  const subtotal = useMemo(
    () => cart.reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0), 0),
    [cart]
  );

  if (!cart.length) {
    return (
      <div className="checkout-page">
        <div className="checkout-card">
          <h1>Your cart is empty</h1>
          <p>Add products before continuing to checkout.</p>
          <button className="checkout-primary" onClick={() => navigate("/products")}>
            Browse products
          </button>
        </div>
      </div>
    );
  }

  function updateField(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  useEffect(() => {
    let cancelled = false;

    async function fetchQuote() {
      if (!form.email || !form.name || !form.phone_number || !form.city || !form.address_line_1 || !cart.length) {
        setQuote(null);
        setQuoteError("");
        return;
      }

      try {
        setQuoting(true);
        setQuoteError("");
        const result = await quoteCheckoutOrder({
          customer: {
            email: form.email,
            name: form.name,
            phone_number: form.phone_number,
          },
          address: {
            recipient_name: form.name,
            phone_number: form.phone_number,
            country: form.country,
            city: form.city,
            state_or_county: form.state_or_county,
            postal_code: form.postal_code,
            address_line_1: form.address_line_1,
            address_line_2: form.address_line_2,
          },
          delivery_location: deliveryLocation || undefined,
          items: cart.map((product) => ({
            product_id: product.id,
            quantity: Number(product.quantity || 1),
          })),
          notes: form.notes || undefined,
        });
        if (!cancelled) {
          setQuote(result);
        }
      } catch (requestError) {
        if (!cancelled) {
          setQuote(null);
          const responseErrors = requestError?.response?.data?.error?.details;
          setQuoteError(
            (responseErrors && Object.values(responseErrors)[0])
            || requestError?.response?.data?.error?.message
            || requestError?.message
            || "Could not calculate delivery."
          );
        }
      } finally {
        if (!cancelled) {
          setQuoting(false);
        }
      }
    }

    fetchQuote();
    return () => {
      cancelled = true;
    };
  }, [cart, deliveryLocation, form.address_line_1, form.address_line_2, form.city, form.country, form.email, form.name, form.notes, form.phone_number, form.postal_code, form.state_or_county]);

  function useLiveLocation() {
    if (!navigator.geolocation) {
      setLocationStatus("This browser does not support live location.");
      return;
    }

    setLocationStatus("Detecting your location...");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setDeliveryLocation({
          latitude: Number(position.coords.latitude.toFixed(7)),
          longitude: Number(position.coords.longitude.toFixed(7)),
          label: `${form.address_line_1 || form.city || "Pinned delivery point"}`,
        });
        setLocationStatus("Live delivery location captured.");
      },
      (geoError) => {
        setLocationStatus(geoError.message || "Could not access your location.");
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setSubmitting(true);
      setError("");

      const item = await createCheckoutOrder({
        customer: {
          email: form.email,
          name: form.name,
          phone_number: form.phone_number,
        },
        address: {
          recipient_name: form.name,
          phone_number: form.phone_number,
          country: form.country,
          city: form.city,
          state_or_county: form.state_or_county,
          postal_code: form.postal_code,
          address_line_1: form.address_line_1,
          address_line_2: form.address_line_2,
        },
        delivery_location: deliveryLocation || undefined,
        items: cart.map((product) => ({
          product_id: product.id,
          quantity: Number(product.quantity || 1),
        })),
        notes: form.notes || undefined,
      });

      setCart([]);
      navigate(`/payment?order_id=${item.id}&tracking_token=${encodeURIComponent(item.tracking_token)}`);
    } catch (requestError) {
      const responseErrors = requestError?.response?.data?.error?.details;
      const firstValidationMessage = responseErrors
        ? Object.values(responseErrors)[0]
        : null;

      setError(
        firstValidationMessage
        || requestError?.response?.data?.error?.message
        || requestError?.message
        || "Could not create your order."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="checkout-page">
      <div className="checkout-layout">
        <form className="checkout-card" onSubmit={handleSubmit}>
          <p className="checkout-eyebrow">Guest checkout</p>
          <h1>Delivery details</h1>
          <p className="checkout-copy">
            This checkout sends your cart directly to the backend order service, so
            we avoid duplicate cart syncs before payment.
          </p>

          <div className="checkout-location-card">
            <div>
              <strong>Delivery location</strong>
              <p className="checkout-note">
                Use your live location so the backend can calculate distance from dispatch and add the delivery fee before payment.
              </p>
            </div>
            <div className="checkout-location-actions">
              <button type="button" className="checkout-secondary" onClick={useLiveLocation}>
                Use live location
              </button>
            </div>
            {deliveryLocation && (
              <div className="checkout-location-pill">
                <span>Lat {deliveryLocation.latitude}</span>
                <span>Lng {deliveryLocation.longitude}</span>
              </div>
            )}
            {locationStatus && <p className="checkout-note">{locationStatus}</p>}
          </div>

          <div className="checkout-grid">
            <label>
              Email
              <input name="email" type="email" value={form.email} onChange={updateField} required />
            </label>
            <label>
              Full name
              <input name="name" value={form.name} onChange={updateField} required />
            </label>
            <label>
              Phone number
              <input name="phone_number" value={form.phone_number} onChange={updateField} required />
            </label>
            <label>
              Country
              <input name="country" value={form.country} onChange={updateField} required />
            </label>
            <label>
              City
              <input name="city" value={form.city} onChange={updateField} required />
            </label>
            <label>
              State / County
              <input name="state_or_county" value={form.state_or_county} onChange={updateField} />
            </label>
            <label>
              Postal code
              <input name="postal_code" value={form.postal_code} onChange={updateField} />
            </label>
            <label className="checkout-span-2">
              Address line 1
              <input name="address_line_1" value={form.address_line_1} onChange={updateField} required />
            </label>
            <label className="checkout-span-2">
              Address line 2
              <input name="address_line_2" value={form.address_line_2} onChange={updateField} />
            </label>
            <label className="checkout-span-2">
              Notes
              <textarea name="notes" rows="4" value={form.notes} onChange={updateField} />
            </label>
          </div>

          {error && <p className="checkout-error">{error}</p>}

          <div className="checkout-actions">
            <button type="button" className="checkout-secondary" onClick={() => navigate("/cart")}>
              Back to cart
            </button>
            <button type="submit" className="checkout-primary" disabled={submitting}>
              {submitting ? "Creating order..." : "Continue to payment"}
            </button>
          </div>
        </form>

        <aside className="checkout-card checkout-summary">
          <h2>Your order</h2>
          <div className="checkout-items">
            {cart.map((item) => (
              <div key={item.id} className="checkout-item">
                <img src={item.primary_image} alt={item.name} />
                <div>
                  <strong>{item.name}</strong>
                  <span>Qty {item.quantity}</span>
                </div>
                <strong>KES {(Number(item.price || 0) * Number(item.quantity || 0)).toLocaleString()}</strong>
              </div>
            ))}
          </div>

          <div className="checkout-total-row">
            <span>Subtotal</span>
            <strong>KES {subtotal.toLocaleString()}</strong>
          </div>
          <div className="checkout-total-row">
            <span>Delivery fee</span>
            <strong>{quote ? `KES ${Number(quote.shipping_amount || 0).toLocaleString()}` : (quoting ? "Calculating..." : "Pending")}</strong>
          </div>
          <div className="checkout-total-row">
            <span>Total</span>
            <strong>{quote ? `KES ${Number(quote.total_amount || 0).toLocaleString()}` : `KES ${subtotal.toLocaleString()}`}</strong>
          </div>
          {quote && (
            <div className="checkout-quote-meta">
              <p>Weight: {quote.shipping_weight_grams || 0} g</p>
              <p>
                Distance: {quote.delivery_location?.distance_km != null
                  ? `${quote.delivery_location.distance_km} km`
                  : (quote.delivery_zone_name || "Zone based")}
              </p>
            </div>
          )}
          {quoteError && <p className="checkout-error">{quoteError}</p>}
        </aside>
      </div>
    </div>
  );
}
