import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { productAPI } from "../services/api";
import Zoom from "react-medium-image-zoom";
import "react-medium-image-zoom/dist/styles.css";
import "../styles/productDetail.css";

export default function ProductDetailPage({ addToCart }) {
  const { slug } = useParams();

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState("");
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    fetchProduct();
  }, [slug]);

  async function fetchProduct() {
    try {
      setLoading(true);

      const res = await productAPI.getProduct(slug);
      const data = res.data.item;
      setProduct(data);
      setSelectedImage(data.images?.[0] || data.primary_image);

    } catch (err) {
      console.error("PRODUCT FETCH ERROR:", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="loader">Loading...</div>;
  if (!product) return <div className="loader">Product not found</div>;


  return (
    <div className="product-page">

      {/* IMAGE GALLERY */}
      <div className="gallery">
        <div className="main-image">
          <Zoom>
            <img
              src={selectedImage || product.primary_image}
              alt={product.name}
            />
          </Zoom>
        </div>

        <div className="thumbnails">
          {product.images.map((img, index) => (
            <img
              key={index}
              src={img}
              alt="thumb"
              className={img === selectedImage ? "active" : ""}
              onClick={() => setSelectedImage(img)}
            />
          ))}
        </div>
      </div>

      {/* PRODUCT INFO */}
      <div className="info">
        <h1>{product.name}</h1>

        <p className="description">
          {product.description || "No description available"}
        </p>

        <div className="price-section">
          <span className="price">
            KES {product.price.toLocaleString()}
          </span>

          {product.compare_at_price && (
            <span className="original-price">
              KES {product.compare_at_price.toLocaleString()}
            </span>
          )}

          <div className="stock-info">
            {product.stock_quantity > 0 ? (
              <span className="in-stock">
                ✓ In Stock ({product.stock_quantity})
              </span>
            ) : (
              <span className="out-of-stock">✗ Out of Stock</span>
            )}
          </div>
        </div>

        {/* Quantity */}
        <div className="quantity-section">
          <label>Quantity</label>

          <div className="qty-selector">
            <button
              onClick={() => setQuantity(q => Math.max(1, q - 1))}
              disabled={product.stock_quantity === 0}
            >
              −
            </button>

            <span>{quantity}</span>

            <button
              onClick={() =>
                setQuantity(q => Math.min(product.stock_quantity, q + 1))
              }
              disabled={quantity >= product.stock_quantity}
            >
              +
            </button>
          </div>
        </div>

        <button
          className="add-to-cart-btn"
          onClick={() => addToCart(product, quantity)}
          disabled={product.stock_quantity === 0}
        >
          {product.stock_quantity > 0 ? "Add to Cart" : "Sold Out"}
        </button>

        {/* META */}
        <div className="product-meta">
          <div className="meta-item">
            <span className="meta-label">SKU:</span>
            <span className="meta-value">{product.sku || "N/A"}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Category:</span>
            <span className="meta-value">{product.category_name || "N/A"}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Brand:</span>
            <span className="meta-value">{product.brand_name || "N/A"}</span>
          </div>
        </div>
      </div>

    </div>
  );
}
