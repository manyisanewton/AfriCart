// src/pages/NotFoundPage.jsx
import { Link, useNavigate } from "react-router-dom";
import "../styles/notFound.css";

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="not-found-page">
      <div className="not-found-card">

        <div className="not-found-code">404</div>

        <h1 className="not-found-title">Page Not Found</h1>

        <p className="not-found-message">
          The page you're looking for doesn't exist or has been moved.
        </p>

        <div className="not-found-actions">
          <Link to="/" className="nf-btn-primary">
            Go to Homepage
          </Link>
          <Link to="/products" className="nf-btn-secondary">
            Browse Products
          </Link>
          <button className="nf-btn-ghost" onClick={() => navigate(-1)}>
            ← Go Back
          </button>
        </div>

        <div className="not-found-suggestions">
          <p>You might be looking for:</p>
          <div className="nf-links">
            <Link to="/products?category=smartphones">Smartphones</Link>
            <Link to="/products?category=laptops">Laptops</Link>
            <Link to="/products?category=accessories">Accessories</Link>
            <Link to="/cart">My Cart</Link>
            <Link to="/account">My Account</Link>
          </div>
        </div>

      </div>
    </div>
  );
}