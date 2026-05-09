import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import BottomNav from "../components/layout/BottomNav";
// import "./layout.css"; 

export default function Layout({ children, cart }) {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar cart={cart} />
      <main style={{ flex: 1 }}>
        {children}
      </main>
      <Footer />
      <BottomNav cart={cart} />
    </div>
  );
}