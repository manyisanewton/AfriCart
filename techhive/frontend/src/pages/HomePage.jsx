import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { productAPI } from "../services/api";
import HeroBanner from "../components/home/HeroBanner";
import FeaturedCategories from "../components/home/FeaturedCategories";
import TrendingProducts from "../components/home/TrendingProducts";
import "../styles/homePage.css";

const FALLBACK_IMAGE = "https://placehold.co/400x400?text=No+Image";

export default function HomePage() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const productsRes = await productAPI.listProducts();
      setProducts(productsRes?.data?.items || []);
    } catch (err) {
      console.error("Home data load failed:", err);
      setProducts([]);
    }
  }

  return (
    <div className="home">
      <HeroBanner />
      <FeaturedCategories />
      <TrendingProducts />

    </div>
  );
}
