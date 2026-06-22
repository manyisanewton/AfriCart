import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section style={{ padding: "64px 20px", textAlign: "center" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto" }}>
        <p style={{ color: "#f97316", fontWeight: 800, letterSpacing: "0.12em", textTransform: "uppercase" }}>
          Page not found
        </p>
        <h1 style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", margin: "12px 0 16px", color: "#0f172a" }}>
          We could not find that page
        </h1>
        <p style={{ fontSize: "1rem", lineHeight: 1.7, color: "#475569", margin: "0 auto 24px", maxWidth: "580px" }}>
          The page may have moved, may not be published yet, or the link may be incorrect.
        </p>
        <Link
          to="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "12px 18px",
            borderRadius: "999px",
            background: "#f97316",
            color: "#fff",
            fontWeight: 700,
            textDecoration: "none",
          }}
        >
          Return home
        </Link>
      </div>
    </section>
  );
}
