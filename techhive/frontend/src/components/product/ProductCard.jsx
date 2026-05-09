import { Link } from "react-router-dom";

export default function ProductCard({ product }) {
  return (
    <div className="card product-card">

      <div className="badge">
        New
      </div>

      <img
        src={p.primary_image || "https://via.placeholder.com/300"}
        alt={p.name}
      />
      
      <h3>{product.name}</h3>

      <p className="price">KES {product.price}</p>

      <p className="stock">
        {product.stock_quantity > 0 ? "In Stock" : "Out of Stock"}
      </p>

      <div className="rating">
        ★★★★☆
      </div>

      <Link to={`/products/${product.slug}`}>
        View Product
      </Link>

    </div>
  );
}