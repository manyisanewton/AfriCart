import { Link } from "react-router-dom";
import "../../styles/productGrid.css";

const FALLBACK_IMAGE = "https://placehold.co/400x400?text=No+Image";

export default function ProductGrid({ products, onAddToCart }) {
  if (!products || !products.length) {
    return <p className="empty">No products found</p>;
  }

  return (
    <div className="product-grid">
      {products.map((p) => (
        <div key={p.id} className="product-card">
          <div className="product-image-wrap">
            <img
              src={p.primary_image || FALLBACK_IMAGE}
              alt={p.name}
            />
            {p.stock_quantity === 0 && (
              <span className="out-of-stock-badge">Out of Stock</span>
            )}
          </div>

          <div className="product-info">
            <h4 className="product-name">{p.name}</h4>

            <div className="product-pricing">
              <span className="product-price">
                KES {Number(p.price).toLocaleString()}
              </span>
              {p.compare_at_price && (
                <span className="product-old-price">
                  KES {Number(p.compare_at_price).toLocaleString()}
                </span>
              )}
            </div>

            <p className={`stock-label ${p.stock_quantity > 0 ? "in-stock" : "no-stock"}`}>
              {p.stock_quantity > 0 ? `In Stock (${p.stock_quantity})` : "Out of Stock"}
            </p>

            <div className="product-actions">
              <Link to={`/products/${p.slug}`} className="view-btn">
                View
              </Link>
              <button
                className="cart-btn"
                disabled={p.stock_quantity === 0}
                onClick={() => onAddToCart && onAddToCart(p, 1)}
              >
                Add to Cart
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}