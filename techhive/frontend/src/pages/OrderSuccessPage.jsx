import { useLocation, Link } from 'react-router-dom';
import '../styles/orderSuccess.css';

export default function OrderSuccessPage() {
  const location = useLocation();
  const orderId = location.state?.orderId;

  return (
    <div className="success-page">
      <div className="success-card">
        <div className="success-icon">✓</div>
        <h1>Order Placed!</h1>
        {orderId && (
          <p className="order-number">Order #{orderId}</p>
        )}
        <p className="success-message">
          Your payment was received. We'll send you a confirmation shortly.
        </p>
        <div className="success-actions">
          <Link to="/products" className="continue-btn">Continue Shopping</Link>
          <Link to="/account" className="orders-btn">View Orders</Link>
        </div>
      </div>
    </div>
  );
}