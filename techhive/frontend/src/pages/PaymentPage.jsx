import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import paymentAPI from "../services/paymentService";
import "../styles/payment.css";

export default function PaymentPage() {
  const location = useLocation();
  const { orderId, total } = location.state || {};

  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null);

  if (!orderId) {
    return (
      <div className="payment-page">
        <h1>No order information</h1>
        <Link to="/cart">Go back to cart</Link>
      </div>
    );
  }

  const handlePay = async (e) => {
    e.preventDefault();
    setError(null);

    if (!/^2547\d{8}$/.test(phone)) {
      setError("Enter phone as 2547XXXXXXXX");
      return;
    }

    setSubmitting(true);
    try {
      const res = await paymentAPI.createPayment({
        order_id: orderId,
        amount: total,
        phone_number: phone,
        provider: "mpesa",
        currency: "KES",
      });
      setStatus("STK push sent. Check your phone.");
      console.log("Payment created:", res.data);
    } catch (err) {
      console.error("Payment failed:", err.response?.data || err);
      setError(
        err.response?.data?.error?.message || "Payment request failed. Try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="payment-page">
      <h1>Pay with M-Pesa</h1>

      <div className="payment-summary">
        <p className="payment-order-id">Order #{orderId}</p>
        <p className="payment-total">KES {total}</p>
      </div>

      <form onSubmit={handlePay} className="payment-form">
        <label htmlFor="phone">M-Pesa phone number</label>
        <input
          id="phone"
          placeholder="2547XXXXXXXX"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />

        {error && <p className="payment-error">{error}</p>}
        {status && <p className="payment-status">{status}</p>}

        <button type="submit" className="pay-btn" disabled={submitting}>
          {submitting ? "Sending..." : "Pay Now"}
        </button>
      </form>
    </div>
  );
}
