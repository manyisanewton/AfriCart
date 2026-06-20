import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import orderAPI from "../services/orderService";
import "../styles/checkout.css";

export default function CheckoutPage({ cart }) {
  const navigate = useNavigate();

  const [address, setAddress] = useState({
    recipient_name: "",
    phone_number: "",
    address_line_1: "",
    city: "",
    country: "Kenya",
    label: "Home",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!cart || cart.length === 0) {
    return (
      <div className="checkout-page checkout-empty">
        <h1>Checkout</h1>
        <p>Your cart is empty.</p>
        <Link to="/products">Continue Shopping</Link>
      </div>
    );
  }

  const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);

  const handleChange = (e) => {
    setAddress({ ...address, [e.target.name]: e.target.value });
  };

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    setError(null);

    if (!address.recipient_name || !address.phone_number || !address.address_line_1 || !address.city) {
      setError("Please fill in all delivery details.");
      return;
    }

    setSubmitting(true);
    try {
      const order = await orderAPI.placeOrder({ cart, address });
      navigate("/payment", { state: { orderId: order.id, total: Number(order.total_amount) } });
    } catch (err) {
      console.error("Order creation failed:", err.response?.data || err);
      setError(
        err.response?.data?.error?.message ||
          "Something went wrong placing your order. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="checkout-page">
      <h1>Checkout</h1>

      <div className="checkout-grid">
        {/* LEFT COLUMN: delivery form */}
        <div className="checkout-form-col">
          <h2>Delivery Details</h2>
          <form onSubmit={handlePlaceOrder} className="address-form">
            <label htmlFor="recipient_name">Full name</label>
            <input
              id="recipient_name"
              name="recipient_name"
              placeholder="e.g. Damaris Ngari"
              value={address.recipient_name}
              onChange={handleChange}
            />

            <label htmlFor="phone_number">Phone number</label>
            <input
              id="phone_number"
              name="phone_number"
              placeholder="2547XXXXXXXX"
              value={address.phone_number}
              onChange={handleChange}
            />

            <label htmlFor="address_line_1">Address</label>
            <input
              id="address_line_1"
              name="address_line_1"
              placeholder="Street, building, house no."
              value={address.address_line_1}
              onChange={handleChange}
            />

            <label htmlFor="city">City</label>
            <input
              id="city"
              name="city"
              placeholder="e.g. Nairobi"
              value={address.city}
              onChange={handleChange}
            />

            {error && <p className="checkout-error">{error}</p>}

            <button type="submit" className="place-order-btn" disabled={submitting}>
              {submitting ? "Placing order..." : "Place Order"}
            </button>
          </form>
        </div>

        {/* RIGHT COLUMN: sticky order summary */}
        <div className="checkout-summary-col">
          <div className="checkout-summary">
            <h2>Order Summary</h2>

            <div className="checkout-items">
              {cart.map((item) => (
                <div key={item.id} className="checkout-item">
                  <img
                    src={item.primary_image || "https://placehold.co/60x60"}
                    alt={item.name}
                  />
                  <div className="checkout-item-info">
                    <p className="checkout-item-name">{item.name}</p>
                    <p className="checkout-item-qty">Qty: {item.quantity}</p>
                  </div>
                  <p className="checkout-item-price">KES {item.price * item.quantity}</p>
                </div>
              ))}
            </div>

            <hr />
            <p className="checkout-subtotal-row">
              <span>Subtotal</span>
              <span>KES {subtotal}</span>
            </p>
            <p className="checkout-note">
              Shipping and final total are calculated by the server and shown on the next step.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
