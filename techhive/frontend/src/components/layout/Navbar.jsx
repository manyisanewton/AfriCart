import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShoppingCart, User, Search, Menu, X, Cpu } from "lucide-react";
import { productAPI } from "../../services/api";
import "../../styles/navbar.css";

const CATEGORY_ICONS = {
  electronics: "📱",
  laptops: "💻",
  smartphones: "📲",
  kitchen: "🍳",
  accessories: "🎧",
  gaming: "🎮",
  television: "📺",
  appliances: "🏠",
  cameras: "📷",
  networking: "📡",
};

const MOCK_CATEGORIES = [
  { id: 10, name: "Smartphones", slug: "smartphones" },
  { id: 11, name: "Laptops", slug: "laptops" },
  { id: 12, name: "Electronics", slug: "electronics" },
  { id: 13, name: "Kitchen", slug: "kitchen" },
  { id: 14, name: "Accessories", slug: "accessories" },
  { id: 15, name: "Gaming", slug: "gaming" },
  { id: 16, name: "TVs", slug: "television" },
  { id: 17, name: "Appliances", slug: "appliances" },
  { id: 18, name: "Cameras", slug: "cameras" },
  { id: 19, name: "Networking", slug: "networking" },
];

const FALLBACK_ICON = "🛒";

export default function Navbar({ cart = [] }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [categories, setCategories] = useState([]);
  const navigate = useNavigate();

  const cartCount = Array.isArray(cart)
    ? cart.reduce((sum, item) => sum + (item?.quantity || 1), 0)
    : 0;

  useEffect(() => {
    fetchCategories();
  }, []);

  async function fetchCategories() {
    try {
      const res = await productAPI.listCategories();
      const real = res.data.items || [];
      const realSlugs = real.map(c => c.slug);
      const extras = MOCK_CATEGORIES.filter(m => !realSlugs.includes(m.slug));
      setCategories([...real, ...extras]);
    } catch (err) {
      setCategories(MOCK_CATEGORIES);
    }
  }

  function handleCategoryClick(slug) {
    navigate(`/products?category=${slug}`);
    setMenuOpen(false);
  }

  function handleSearch(e) {
    if (e.key === 'Enter' && searchQuery.trim()) {
      navigate(`/products?search=${searchQuery.trim()}`);
    }
  }

  return (
    <header className="navbar">

      {/* ROW 1: main nav */}
      <div className="nav-inner">
        <div className="nav-left">
          <button
            className="hamburger"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menu"
          >
            {menuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          <Link to="/" className="logo">
            <Cpu size={28} className="logo-icon" />
            <span>TechHive</span>
          </Link>
        </div>

        {/* Desktop search */}
        <div className="nav-search">
          <Search size={20} className="search-icon" />
          <input
            type="text"
            placeholder="Search for electronics..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={handleSearch}
            aria-label="Search"
          />
        </div>

        <div className="nav-right">
          <Link to="/cart" className="nav-icon cart-icon" aria-label="Cart">
            <ShoppingCart size={22} />
            {cartCount > 0 && (
              <span className="cart-badge">{cartCount}</span>
            )}
          </Link>

          <Link to="/account" className="nav-icon" aria-label="Account">
            <User size={22} />
          </Link>

          {process.env.NODE_ENV === 'development' && (
            <Link to="/admin/dashboard" className="nav-icon" style={{ fontSize: '12px' }}>
              Admin
            </Link>
          )}
        </div>
      </div>

      {/* Mobile search — below nav row, above categories */}
      <div className="mobile-search">
        <Search size={18} className="search-icon" />
        <input
          type="text"
          placeholder="Search for electronics..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={handleSearch}
          aria-label="Search"
        />
      </div>

      {/* ROW 2: categories bar */}
      <div className="nav-categories">
        <div className="nav-categories-inner">
          {categories.map(cat => (
            <button
              key={cat.id}
              className="nav-category-pill"
              onClick={() => handleCategoryClick(cat.slug)}
            >
              <span>{CATEGORY_ICONS[cat.slug] || FALLBACK_ICON}</span>
              <span>{cat.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="mobile-menu">
          <Link to="/" onClick={() => setMenuOpen(false)}>Home</Link>
          <Link to="/products" onClick={() => setMenuOpen(false)}>All Products</Link>
          <Link to="/wishlist" onClick={() => setMenuOpen(false)}>Wishlist</Link>
          <Link to="/cart" onClick={() => setMenuOpen(false)}>Cart ({cartCount})</Link>
          <Link to="/account" onClick={() => setMenuOpen(false)}>My Account</Link>
          <div className="mobile-categories">
            <p className="mobile-categories-label">Categories</p>
            {categories.map(cat => (
              <button
                key={cat.id}
                className="mobile-category-item"
                onClick={() => handleCategoryClick(cat.slug)}
              >
                {CATEGORY_ICONS[cat.slug] || FALLBACK_ICON} {cat.name}
              </button>
            ))}
          </div>
        </div>
      )}    </header>
  );
}