import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./layouts/layout";
import HomePage from "./pages/HomePage";
import ProductListingPage from "./pages/ProductListingPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import OrderConfirmationPage from "./pages/OrderConfirmationPage";
import ContentPage from "./pages/ContentPage";
import "./styles/alert.css";

const CART_STORAGE_KEY = "techhive_storefront_cart";

function App() {
  const [cart, setCart] = useState(() => {
    try {
      const raw = window.localStorage.getItem(CART_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.error("Failed to restore cart from storage:", error);
      return [];
    }
  });
  const [alert, setAlert] = useState("");

  useEffect(() => {
    try {
      window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    } catch (error) {
      console.error("Failed to persist cart:", error);
    }
  }, [cart]);

  const addToCart = (product, quantity = 1) => {
    setCart((prev) => {
      const existing = prev.find((item) => item.id === product.id);

      if (existing) {
        return prev.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + quantity }
            : item
        );
      }

      return [...prev, { ...product, quantity }];
    });

    setAlert(`${product.name} added to cart`);

    setTimeout(() => setAlert(""), 2000);
  };

  return (
    <BrowserRouter>
      {alert && <div className="top-alert">{alert}</div>}

      <Layout cart={cart}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/products"
            element={<ProductListingPage addToCart={addToCart} />}
          />
          <Route
            path="/products/:slug"
            element={<ProductDetailPage addToCart={addToCart} />}
          />
          <Route
            path="/cart"
            element={<CartPage cart={cart} setCart={setCart} />}
          />
          <Route
            path="/checkout"
            element={<CheckoutPage cart={cart} setCart={setCart} />}
          />
          <Route path="/payment" element={<OrderConfirmationPage />} />
          <Route
            path="/account"
            element={
              <div style={{ padding: "2rem", textAlign: "center" }}>
                Account page coming soon
              </div>
            }
          />
          <Route path="*" element={<ContentPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
