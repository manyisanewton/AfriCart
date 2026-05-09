import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./layouts/layout";
import HomePage from "./pages/HomePage";
import ProductListingPage from "./pages/ProductListingPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import CartPage from "./pages/CartPage";
import "./styles/alert.css";

function App() {
  const [cart, setCart] = useState([]);
  const [alert, setAlert] = useState("");

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
          <Route path="/products" element={<ProductListingPage addToCart={addToCart} />} />
          <Route
            path="/products/:slug"
            element={<ProductDetailPage addToCart={addToCart} />}
          />
          <Route
            path="/cart"
            element={<CartPage cart={cart} setCart={setCart} />}
          />
          <Route
            path="/account"
            element={<div style={{ padding: "2rem", textAlign: "center" }}>Account page coming soon</div>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );

}

export default App;