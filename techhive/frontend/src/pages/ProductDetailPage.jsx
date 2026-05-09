import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { productAPI } from "../services/api";
import Zoom from "react-medium-image-zoom";
import "react-medium-image-zoom/dist/styles.css";
import "../styles/productDetail.css";

const FALLBACK_IMAGE = "https://placehold.co/400x400?text=No+Image";


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

      //  Normalize everything
      const images =
        data.images && data.images.length > 0
          ? data.images
          : [data.primary_image || FALLBACK_IMAGE]
      const normalized = {
        ...data,
        price: Number(data.price),
        compare_at_price: data.compare_at_price
          ? Number(data.compare_at_price)
          : null,
        category: data.category?.name || "N/A",
        brand: data.brand?.name || "N/A",
        images,
      };

      setProduct(normalized);
      setSelectedImage(images[0]);

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
              src={selectedImage || FALLBACK_IMAGE }
              alt={product.name}
            />
          </Zoom>
        </div>

        <div className="thumbnails">
          {product.images.map((img, index) => (
            <img
              key={index}
              src={img || FALLBACK_IMAGE}
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
            <span className="meta-value">{product.category}</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Brand:</span>
            <span className="meta-value">{product.brand}</span>
          </div>
        </div>
      </div>

    </div>
  );
}