import { Link, useLocation } from "react-router-dom";
import { Home, Grid, ShoppingCart, User } from "lucide-react";
import "../../styles/bottomNav.css";

export default function BottomNav({ cart }) {
  const location = useLocation();
  const cartCount = cart?.reduce((sum, item) => sum + item.quantity, 0) || 0;

  const navItems = [
    { to: "/", icon: <Home size={22} />, label: "Home" },
    { to: "/products", icon: <Grid size={22} />, label: "Products" },
    { to: "/cart", icon: <ShoppingCart size={22} />, label: "Cart", badge: cartCount },
    { to: "/account", icon: <User size={22} />, label: "Account" },
  ];

  return (
    <nav className="bottom-nav">
      {navItems.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className={`bottom-nav-item ${location.pathname === item.to ? "active" : ""}`}
        >
          <div className="bottom-nav-icon-wrap">
            {item.icon}
            {item.badge > 0 && (
              <span className="bottom-nav-badge">{item.badge}</span>
            )}
          </div>
          <span className="bottom-nav-label">{item.label}</span>
        </Link>
      ))}
    </nav>
  );
}