import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ShoppingCart, User, Search, Menu, X, Cpu, Heart } from "lucide-react";
import "../../styles/navbar.css";

export default function Navbar({ cart = [] }) {
  const [menuOpen, setMenuOpen] = useState(false);

  const cartCount = Array.isArray(cart)
    ? cart.reduce((sum, item) => sum + (item?.quantity || 1), 0)
    : 0;

  return (
    <header className="navbar">
      <div className="nav-inner">

        {/* LEFT: logo + hamburger */}
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

        {/* CENTER: search */}
        <div className="nav-search">
          <Search size={20} className="search-icon" />
          <input 
            type="text"
            placeholder="Search for electronics..." 
            aria-label="Search"
          />
        </div>

        {/* RIGHT: icons */}
        <div className="nav-right">
          <Link to="/wishlist" className="nav-icon" aria-label="Wishlist">
            <Heart size={22} />
          </Link>
          
          <Link to="/cart" className="nav-icon cart-icon" aria-label="Cart">
            <ShoppingCart size={22} />
            {cartCount > 0 && (
              <span className="cart-badge">{cartCount}</span>
            )}
          </Link>
          
          <Link to="/account" className="nav-icon" aria-label="Account">
            <User size={22} />
          </Link>
        </div>

      </div>

      {/* MOBILE MENU */}
      {menuOpen && (
        <div className="mobile-menu">
          <Link to="/" onClick={() => setMenuOpen(false)}>Home</Link>
          <Link to="/products" onClick={() => setMenuOpen(false)}>All Products</Link>
          <Link to="/wishlist" onClick={() => setMenuOpen(false)}>Wishlist</Link>
          <Link to="/cart" onClick={() => setMenuOpen(false)}>Cart ({cartCount})</Link>
          <Link to="/account" onClick={() => setMenuOpen(false)}>My Account</Link>
        </div>
      )}
    </header>
  );
}