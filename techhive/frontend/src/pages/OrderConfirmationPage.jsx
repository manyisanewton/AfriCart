import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { createCheckoutPayment, getCheckoutOrder } from "../services/paymentService";
import "../styles/payment.css";

export default function OrderConfirmationPage() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get("order_id");
  const trackingToken = searchParams.get("tracking_token");

  const [order, setOrder] = useState(null);
  const [loadingOrder, setLoadingOrder] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [paymentResult, setPaymentResult] = useState(null);
  const [paymentError, setPaymentError] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [selectedMethod, setSelectedMethod] = useState("mpesa");

  const orderItems = useMemo(() => order?.items || [], [order]);

  useEffect(() => {
    let cancelled = false;

    async function loadOrder() {
      if (!trackingToken) {
        setLoadingOrder(false);
        return;
      }

      try {
        setLoadingOrder(true);
        const item = await getCheckoutOrder(trackingToken);
        if (!cancelled) {
          setOrder(item);
          setPhoneNumber(item?.shipping_address?.phone_number || "");
        }
      } catch (error) {
        if (!cancelled) {
          setPaymentError(
            error?.response?.data?.error?.message
            || error?.message
            || "Could not load order details."
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingOrder(false);
        }
      }
    }

    loadOrder();
    return () => {
      cancelled = true;
    };
  }, [trackingToken]);

  async function handlePayment(event) {
    event.preventDefault();

    if (!orderId || !trackingToken) {
      setPaymentError("This payment session is missing order details.");
      return;
    }

    try {
      setSubmitting(true);
      setPaymentError("");
      const item = await createCheckoutPayment({
        order_id: Number(orderId),
        tracking_token: trackingToken,
        method: selectedMethod,
        phone_number: selectedMethod === "mpesa" ? phoneNumber : undefined,
      });
      setPaymentResult(item);
    } catch (error) {
      setPaymentError(
        error?.response?.data?.error?.message
        || error?.response?.data?.error?.details?.phone_number
        || error?.message
        || "Could not start payment."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingOrder) {
    return <div className="payment-page"><div className="payment-card">Loading order...</div></div>;
  }

  if (!order) {
    return (
      <div className="payment-page">
        <div className="payment-card">
          <h1>Order not found</h1>
          <p>We could not recover this checkout session.</p>
          <Link to="/products" className="payment-link">Continue shopping</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="payment-page">
      <div className="payment-layout">
        <section className="payment-card">
          <p className="payment-eyebrow">Checkout complete</p>
          <h1>Choose how you want to pay</h1>
          <p className="payment-copy">
            Order <strong>{order.order_number}</strong> is ready. This flow supports
            guest checkout, so you can safely reload this page and continue payment.
          </p>

          <div className="payment-status-grid">
            <div className="payment-stat">
              <span>Order total</span>
              <strong>KES {Number(order.total_amount || 0).toLocaleString()}</strong>
            </div>
            <div className="payment-stat">
              <span>Status</span>
              <strong>{order.status}</strong>
            </div>
            <div className="payment-stat">
              <span>Tracking token</span>
              <strong>{trackingToken}</strong>
            </div>
          </div>

          <form className="payment-form" onSubmit={handlePayment}>
            <label>
              Payment method
              <select
                value={selectedMethod}
                onChange={(event) => setSelectedMethod(event.target.value)}
              >
                <option value="mpesa">M-Pesa</option>
                <option value="manual">Manual</option>
                <option value="cash_on_delivery">Cash on delivery</option>
              </select>
            </label>

            {selectedMethod === "mpesa" && (
              <label>
                M-Pesa phone number
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(event) => setPhoneNumber(event.target.value)}
                  placeholder="2547XXXXXXXX"
                  required
                />
              </label>
            )}

            {paymentError && <p className="payment-error">{paymentError}</p>}

            <button className="payment-submit" type="submit" disabled={submitting}>
              {submitting ? "Starting payment..." : "Start payment"}
            </button>
          </form>

          {paymentResult && (
            <div className="payment-result">
              <h2>Payment started</h2>
              <p>Reference: <strong>{paymentResult.reference}</strong></p>
              <p>Status: <strong>{paymentResult.status}</strong></p>
              {paymentResult.redirect_url && (
                <a href={paymentResult.redirect_url} target="_blank" rel="noreferrer">
                  Continue with provider
                </a>
              )}
            </div>
          )}
        </section>

        <aside className="payment-card payment-summary">
          <h2>Order summary</h2>
          <div className="payment-line">
            <span>Email</span>
            <strong>{order.guest_email || "Signed-in checkout"}</strong>
          </div>
          <div className="payment-line">
            <span>Delivery</span>
            <strong>{order.shipping_address?.city}, {order.shipping_address?.country}</strong>
          </div>

          <div className="payment-items">
            {orderItems.map((item) => (
              <div key={item.id} className="payment-item">
                <div>
                  <strong>{item.product_name}</strong>
                  <span>Qty {item.quantity}</span>
                </div>
                <strong>KES {Number(item.line_total || 0).toLocaleString()}</strong>
              </div>
            ))}
          </div>

          <div className="payment-totals">
            <div className="payment-line">
              <span>Subtotal</span>
              <strong>KES {Number(order.subtotal || 0).toLocaleString()}</strong>
            </div>
            <div className="payment-line">
              <span>Shipping</span>
              <strong>KES {Number(order.shipping_amount || 0).toLocaleString()}</strong>
            </div>
            <div className="payment-line total">
              <span>Total</span>
              <strong>KES {Number(order.total_amount || 0).toLocaleString()}</strong>
            </div>
          </div>

          <Link to="/products" className="payment-link">Back to shopping</Link>
        </aside>
      </div>
    </div>
  );
}
