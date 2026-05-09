import "../../styles/footer.css";
export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">

        {/* TechHive */}
        <div>
          <h3 className="font-bold mb-3">TechHive</h3>
          <p>Your trusted electronics marketplace.</p>
        </div>

        {/* Quick Links */}
        <div>
          <h3 className="font-bold mb-3">Quick Links</h3>
          <ul className="space-y-2">
            <li>Home</li>
            <li>Products</li>
            <li>Cart</li>
          </ul>
        </div>

        {/* Categories */}
        <div>
          <h3 className="font-bold mb-3">Categories</h3>
          <ul className="space-y-2">
            <li>Smartphones</li>
            <li>Laptops</li>
            <li>Electronics</li>
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
          <span>Privacy Policy</span>
          <span>Terms of Service</span>
          <span>Return Policy</span>
        </div>

        <div>© 2026 TechHive. All rights reserved</div>
      </div>
    </footer>
  );
}