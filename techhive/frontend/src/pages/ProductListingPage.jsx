import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { productAPI } from "../services/api";
import ProductGrid from "../components/product/ProductGrid";
import "../styles/productListing.css";


const FALLBACK_IMAGE = "https://placehold.co/400x400?text=No+Image";

export default function ProductListingPage( { addToCart } ) {
  const [products, setProducts] = useState([]);
  const [allProducts, setAllProducts] = useState([]);
  const [categories, setCategories] = useState([]);

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState("newest");
  const [price, setPrice] = useState(500000);
  const [showFilters, setShowFilters] = useState(false);

  const [searchParams] = useSearchParams();

  useEffect(() => {
    const cat = searchParams.get("category");
    if (cat) setCategory(cat);
  }, [searchParams]);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    const res = await productAPI.listProducts();
    const catRes = await productAPI.listCategories();

    const items = res.data.items || [];


    const itemsWithImages = items.map(p => ({
      ...p,
      primary_image: p.primary_image || FALLBACK_IMAGE
    }));


    setProducts(itemsWithImages);
    setAllProducts(itemsWithImages);
    setCategories(catRes.data.items || []);
  }

  useEffect(() => {
    let filtered = [...allProducts];

    if (search) {
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase())
      );
    }

    if (category !== "all") {
      filtered = filtered.filter(p =>
        p.category?.slug === category ||
        p.category?.name?.toLowerCase() === category.toLowerCase()
      );
    }
    filtered = filtered.filter(p => Number(p.price) <= price);

    if (sort === "price_low") {
      filtered.sort((a, b) => Number(a.price) - Number(b.price));
    }

    if (sort === "price_high") {
      filtered.sort((a, b) => Number(b.price) - Number(a.price));
    }

    if (sort === "newest") {
      filtered.sort((a, b) => b.id - a.id);
    }

    setProducts(filtered);
  }, [search, category, sort, price, allProducts]);

  const clearFilters = () => {
    setSearch("");
    setCategory("all");
    setSort("newest");
    setPrice(500000);
  };



  return (
    <div className="listing-page">
      {/* DESKTOP SIDEBAR */}
      <div className="filters-sidebar">
        <h3>Filter Products</h3>

        <div className="filter-group">
          <label>Search</label>
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>Category</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="all">All Categories</option>
            {categories.map(c => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Sort By</label>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="newest">Newest</option>
            <option value="price_low">Price: Low to High</option>
            <option value="price_high">Price: High to Low</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Max Price: <span className="price-value">KES {price.toLocaleString()}</span></label>
          <input
            type="range"
            min="0"
            max="500000"
            step="1000"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
          />
        </div>

        <button className="clear-filters" onClick={clearFilters}>
          Clear All Filters
        </button>
      </div>

      {/* MOBILE FILTER BUTTON */}
      <button className="filter-toggle-btn" onClick={() => setShowFilters(true)}>
        Filters
      </button>

      {/* MOBILE FILTER DRAWER */}
      <div className={`filter-drawer ${showFilters ? "open" : ""}`}>
        <div className="filter-header">
          <h3>Filter Products</h3>
          <button className="close-btn" onClick={() => setShowFilters(false)}>
            ✕
          </button>
        </div>

        <input
          type="text"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="all">All Categories</option>
          {categories.map(c => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="newest">Newest</option>
          <option value="price_low">Price: Low to High</option>
          <option value="price_high">Price: High to Low</option>
        </select>

        <div className="price-range">
          <label>Max Price: KES {price.toLocaleString()}</label>
          <input
            type="range"
            min="0"
            max="500000"
            step="1000"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
          />
        </div>

        <button className="clear-filters" onClick={() => {
          clearFilters();
          setShowFilters(false);
        }}>
          Clear All Filters
        </button>
      </div>

      {/* PRODUCT GRID */}
      <ProductGrid products={products} />
    </div>
  );
}