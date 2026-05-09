import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { productAPI } from "../../services/api";
import "../../styles/featuredCategories.css";

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

const FALLBACK_ICON = "🛒";

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


export default function FeaturedCategories() {
    const [categories, setCategories] = useState([]);
    const navigate = useNavigate();

    useEffect(() => {
        fetchCategories();
    }, []);

    async function fetchCategories() {
        try {
            const res = await productAPI.listCategories();
            const real = res.data.items || [];
            // merge real with mock, real ones take priority
            const realSlugs = real.map(c => c.slug);
            const extras = MOCK_CATEGORIES.filter(m => !realSlugs.includes(m.slug));
            setCategories([...real, ...extras]);
        } catch (err) {
            setCategories(MOCK_CATEGORIES);
        }
    }
    function handleClick(slug) {
        navigate(`/products?category=${slug}`);
    }

    return (
        <div className="categories-bar">
            <div className="categories-inner">
                {categories.map((cat) => (
                    <button
                        key={cat.id}
                        className="category-pill"
                        onClick={() => handleClick(cat.slug)}
                    >
                        <span className="category-icon">
                            {CATEGORY_ICONS[cat.slug] || FALLBACK_ICON}
                        </span>
                        <span className="category-name">{cat.name}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}