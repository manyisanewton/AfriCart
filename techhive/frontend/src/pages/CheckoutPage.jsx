// src/pages/CheckoutPage.jsx
import { useState, useEffect, useRef } from 'react';
import { useCart } from '../context/CartContext';
import { Link, useNavigate } from 'react-router-dom';
import MpesaPayment from '../components/checkout/MpesaPayment';
import { createAddress, syncCartToBackend, createOrder } from '../services/orderService';
import { createPayment, pollPaymentStatus } from '../services/paymentService';
import '../styles/checkout.css';

export default function CheckoutPage() {
  const { cart, cartTotal, clearCart } = useCart();
  const navigate = useNavigate();
  const pollingRef = useRef(null);

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [orderId, setOrderId] = useState(null);

  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    phone: '',
    address: '',
    city: '',
  });

  const subtotal = cartTotal;
  const shipping = subtotal > 50000 ? 0 : 500;
  const total = subtotal + shipping;

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmitDetails = (e) => {
    e.preventDefault();
    if (!formData.fullName || !formData.email || !formData.address || !formData.city) {
      setError('Please fill all required fields');
      return;
    }
    setError('');
    setStep(2);
  };

  async function handlePayment(mpesaPhone) {
    setLoading(true);
    setError('');
    setStatusMessage('Saving delivery address...');

    // Step 1: Create address
    const addressResult = await createAddress(formData);
    if (!addressResult.success) {
      setLoading(false);
      setStatusMessage('');
      setError(addressResult.message);
      return;
    }

    setStatusMessage('Syncing your cart...');

    // Step 2: Sync frontend cart to backend
    const syncResult = await syncCartToBackend(cart);
    if (!syncResult.success) {
      setLoading(false);
      setStatusMessage('');
      setError(syncResult.message);
      return;
    }

    setStatusMessage('Creating your order...');

    // Step 3: Create order
    const orderResult = await createOrder(addressResult.addressId);
    if (!orderResult.success) {
      setLoading(false);
      setStatusMessage('');
      setError(orderResult.message);
      return;
    }

    const newOrderId = orderResult.orderId;
    setOrderId(newOrderId);
    setStatusMessage('Sending M-Pesa prompt to your phone...');

    // Step 4: Create payment and trigger STK push
    const paymentResult = await createPayment(newOrderId, total, mpesaPhone);
    if (!paymentResult.success) {
      setLoading(false);
      setStatusMessage('');
      setError(paymentResult.message);
      return;
    }

    setStatusMessage('Check your phone and enter your M-Pesa PIN...');

    // Step 5: Poll for payment status
    pollingRef.current = pollPaymentStatus(
      paymentResult.paymentId,
      () => {
        setLoading(false);
        setStatusMessage('');
        clearCart();
        navigate('/order-success', { state: { orderId: newOrderId } });
      },
      (msg) => {
        setLoading(false);
        setStatusMessage('');
        setError(msg);
      },
      () => {
        setLoading(false);
        setStatusMessage('');
        setError('Payment timed out. Please try again.');
      }
    );
  }

  if (cart.length === 0) {
    return (
      <div className="checkout-empty">
        <h2>Your cart is empty</h2>
        <Link to="/products">Continue Shopping</Link>
      </div>
    );
  }

  return (
    <div className="checkout-page">
      <div className="checkout-steps">
        <div className={`step ${step >= 1 ? 'active' : ''}`}>1. Details</div>
        <div className={`step ${step >= 2 ? 'active' : ''}`}>2. Payment</div>
      </div>

      <div className="checkout-content">
        {step === 1 && (
          <form onSubmit={handleSubmitDetails} className="details-form">
            <h2>Delivery Information</h2>
            {error && <p className="checkout-error">{error}</p>}
            <input
              type="text"
              name="fullName"
              placeholder="Full Name *"
              value={formData.fullName}
              onChange={handleChange}
              required
            />
            <input
              type="email"
              name="email"
              placeholder="Email *"
              value={formData.email}
              onChange={handleChange}
              required
            />
            <input
              type="tel"
              name="phone"
              placeholder="Phone Number"
              value={formData.phone}
              onChange={handleChange}
            />
            <input
              type="text"
              name="address"
              placeholder="Delivery Address *"
              value={formData.address}
              onChange={handleChange}
              required
            />
            <input
              type="text"
              name="city"
              placeholder="City *"
              value={formData.city}
              onChange={handleChange}
              required
            />
            <button type="submit">Continue to Payment</button>
          </form>
        )}

        {step === 2 && (
          <div className="payment-section">
            <h2>Pay with M-Pesa</h2>
            {error && <p className="checkout-error">{error}</p>}
            <MpesaPayment
              onSubmit={handlePayment}
              loading={loading}
              statusMessage={statusMessage}
            />
            <button
              className="back-btn"
              onClick={() => { setStep(1); setError(''); }}
              disabled={loading}
            >
              ← Back
            </button>
          </div>
        )}
      </div>

      <div className="checkout-sidebar">
        <h3>Order Summary</h3>
        {cart.map(item => (
          <div key={item.id} className="sidebar-item">
            <span>{item.name} x {item.quantity}</span>
            <span>KES {(item.price * item.quantity).toLocaleString()}</span>
          </div>
        ))}
        <hr />
        <div className="sidebar-totals">
          <p>Subtotal: KES {subtotal.toLocaleString()}</p>
          <p>Shipping: {shipping === 0 ? 'Free' : `KES ${shipping.toLocaleString()}`}</p>
          <p><strong>Total: KES {total.toLocaleString()}</strong></p>
        </div>
      </div>
    </div>
  );
}