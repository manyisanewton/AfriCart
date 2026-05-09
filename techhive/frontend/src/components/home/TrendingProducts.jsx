import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { productAPI } from "../../services/api";
import "../../styles/trendingProducts.css";

const FALLBACK_IMAGE = "https://placehold.co/400x400?text=No+Image";

export default function TrendingProducts() {
  const [allProducts, setAllProducts] = useState([]);
  const [products, setProducts] = useState([]);
  const [sort, setSort] = useState("newest");
  const [maxPrice, setMaxPrice] = useState(500000);

  useEffect(() => {
    fetchProducts();
  }, []);

  async function fetchProducts() {
    try {
      const res = await productAPI.listProducts();
      const items = res.data.items || [];
      setAllProducts(items);
      setProducts(items);
    } catch (err) {
      console.error("Trending products error:", err);
    }
  }

  useEffect(() => {
    let filtered = [...allProducts];

    filtered = filtered.filter(p => Number(p.price) <= maxPrice);

    if (sort === "newest") {
      filtered.sort((a, b) => b.id - a.id);
    } else if (sort === "price_low") {
      filtered.sort((a, b) => Number(a.price) - Number(b.price));
    } else if (sort === "price_high") {
      filtered.sort((a, b) => Number(b.price) - Number(a.price));
    }

    setProducts(filtered);
  }, [sort, maxPrice, allProducts]);

  return (
    <section className="trending-section">
      <div className="trending-header">
        <h2 className="trending-title">Trending Products</h2>

        <div className="trending-controls">
          <div className="price-range">
            <label>
              Max: KES {Number(maxPrice).toLocaleString()}
            </label>
            <input
              type="range"
              min="1000"
              max="500000"
              step="1000"
              value={maxPrice}
              onChange={e => setMaxPrice(Number(e.target.value))}
            />
          </div>

          <select
            className="sort-select"
            value={sort}
            onChange={e => setSort(e.target.value)}
          >
            <option value="newest">Newest</option>
            <option value="price_low">Price: Low to High</option>
            <option value="price_high">Price: High to Low</option>
          </select>
        </div>
      </div>

      <div className="trending-grid">
        {products.length === 0 ? (
          <p className="no-products">No products found.</p>
        ) : (
          products.slice(0, 8).map(p => (
            <div key={p.id} className="product-card">
              <div className="product-image-wrap">
                <img
                  src={p.primary_image || FALLBACK_IMAGE}
                  alt={p.name}
                />
              </div>
              <div className="product-info">
                <h4 className="product-name">{p.name}</h4>
                <p className="product-price">
                  KES {Number(p.price).toLocaleString()}
                </p>
                {p.compare_at_price && (
                  <p className="product-old-price">
                    KES {Number(p.compare_at_price).toLocaleString()}
                  </p>
                )}
                <Link
                  to={`/products/${p.slug}`}
                  className="product-btn"
                >
                  View Product
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}