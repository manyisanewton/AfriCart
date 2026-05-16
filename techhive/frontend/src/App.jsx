// src/App.jsx
import { Navigate } from "react-router-dom";
import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { CartProvider, useCart } from './context/CartContext';
import Layout from "./layouts/layout";
import HomePage from "./pages/HomePage";
import ProductListingPage from "./pages/ProductListingPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import OrderSuccessPage from "./pages/OrderSuccessPage";
import AdminLayout from "./layouts/AdminLayout";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminProductsPage from "./pages/admin/AdminProductsPage";
import AdminOrdersPage from "./pages/admin/AdminOrdersPage";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import AdminVendorsPage from "./pages/admin/AdminVendorsPage";
import AdminBannersPage from "./pages/admin/AdminBannersPage";
// import AdminBrandsPage from "./pages/admin/AdminBrandsPage";
// import AdminCategoriesPage from "./pages/admin/AdminCategoriesPage";
// import AdminPromosPage from "./pages/admin/AdminPromosPage";
import AdminReportsPage from "./pages/admin/AdminReportsPage";
import "./styles/alert.css";

// Component that uses cart context
function AppContent() {
  const { addToCart, cart } = useCart();
  const [alert, setAlert] = useState("");

  const handleAddToCart = (product, quantity = 1) => {
    addToCart(product, null, quantity);
    setAlert(`${product.name} added to cart`);
    setTimeout(() => setAlert(""), 2000);
  };

  return (
    <>
      {alert && <div className="top-alert">{alert}</div>}
      <Layout cart={cart}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/products" element={<ProductListingPage addToCart={handleAddToCart} />} />
          <Route path="/products/:slug" element={<ProductDetailPage addToCart={handleAddToCart} />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-success" element={<OrderSuccessPage />} />
          <Route path="/account" element={<div style={{ padding: "2rem", textAlign: "center" }}>Account page coming soon</div>} />
          <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
<Route path="/admin" element={<AdminLayout />}>
  <Route path="dashboard" element={<AdminDashboardPage />} />
  <Route path="products" element={<AdminProductsPage />} />
  <Route path="orders" element={<AdminOrdersPage />} />
  <Route path="users" element={<AdminUsersPage />} />
  <Route path="vendors" element={<AdminVendorsPage />} />
  <Route path="banners" element={<AdminBannersPage />} />
  {/* <Route path="brands" element={<AdminBrandsPage />} /> */}
  {/* <Route path="categories" element={<AdminCategoriesPage />} />
  <Route path="promos" element={<AdminPromosPage />} /> */}
  <Route path="reports" element={<AdminReportsPage />} />
</Route>
        </Routes>
      </Layout>
    </>
  );
}

// Main App - CartProvider wraps everything
function App() {
  return (
    <BrowserRouter>
      <CartProvider>
        <AppContent />
      </CartProvider>
    </BrowserRouter>
  );
}

export default App;