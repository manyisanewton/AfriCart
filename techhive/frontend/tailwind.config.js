/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,jsx}"],
    theme: {
        extend: {
            colors: {
                primary: "#1A56DB",
                secondary: "#F59E0B",
                dark: "#1E293B",
                light: "#F8FAFC",
                success: "#10B981",
                danger: "#EF4444",
            },
            borderRadius: {
                card: "8px",
                btn: "6px",
                badge: "4px",
            },
            boxShadow: {
                card: "0 2px 12px rgba(0,0,0,0.08)",
            },
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"],
            },
        },
    },
    plugins: [],
};