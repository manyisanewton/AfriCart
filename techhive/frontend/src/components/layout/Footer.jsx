import { Link } from "react-router-dom";
import "../../styles/footer.css";

const quickLinks = [
  { label: "Home", to: "/" },
  { label: "Products", to: "/products" },
  { label: "Cart", to: "/cart" },
  { label: "Buyer Protection", to: "/buyer-protection-policy" },
];

const policyLinks = [
  { label: "Privacy Policy", to: "/privacy-policy" },
  { label: "Return Policy", to: "/return-policy" },
  { label: "Shipping Policy", to: "/shipping-and-delivery-policy" },
  { label: "Warranty Policy", to: "/warranty-policy" },
  { label: "Dispute Resolution", to: "/dispute-resolution" },
];

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">

        {/* TechHive */}
        <div className="footer-brand">
          <img src="/logo.png" alt="TechHive" className="footer-logo" />
          <p>Your trusted electronics marketplace.</p>
        </div>

        {/* Quick Links */}
        <div>
          <h3 className="font-bold mb-3">Quick Links</h3>
          <ul className="space-y-2">
            {quickLinks.map((link) => (
              <li key={link.to}>
                <Link to={link.to}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Customer Policies */}
        <div>
          <h3 className="font-bold mb-3">Customer Policies</h3>
          <ul className="space-y-2">
            {policyLinks.map((link) => (
              <li key={link.to}>
                <Link to={link.to}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Contact */}
        <div>
          <h3 className="font-bold mb-3">Contact Us</h3>
          <p>Email: support@techhive.com</p>
          <p>Phone: +254 700 000000</p>
        </div>

      </div>

      {/* Bottom row */}
      <div className="footerBottom">
        <div className="space-x-4">
          <Link to="/privacy-policy">Privacy Policy</Link>
          <Link to="/payment-information-and-guidelines">Payment Information</Link>
          <Link to="/report-a-product">Report a Product</Link>
        </div>

        <div>© 2026 TechHive. All rights reserved</div>
      </div>
    </footer>
  );
}
