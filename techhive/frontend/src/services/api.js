// src/services/api.js
import axios from "axios";

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api/v1"
});

const API_ORIGIN = String(api.defaults.baseURL || "").replace(/\/api\/v1\/?$/, "");
const FALLBACK_IMAGE = "https://placehold.co/400x400?text=No+Image";

function mediaUrl(src) {
    if (!src) return FALLBACK_IMAGE;
    if (src.startsWith("blob:") || src.startsWith("data:") || /^https?:\/\//.test(src)) {
        return src;
    }
    return `${API_ORIGIN}${src.startsWith("/") ? src : `/${src}`}`;
}

function normalizeProduct(product) {
    if (!product) return product;

    const images = Array.isArray(product.images)
        ? product.images.map((image) => mediaUrl(image?.image_url || image?.src || image))
        : [];

    const primaryImage = mediaUrl(
        product.primary_image?.image_url
        || product.primary_image
        || images[0]
    );

    return {
        ...product,
        price: Number(product.price || 0),
        compare_at_price: product.compare_at_price ? Number(product.compare_at_price) : null,
        primary_image: primaryImage,
        images: images.length ? images : [primaryImage],
        category_name: product.category?.name || "",
        category_slug: product.category?.slug || "",
        brand_name: product.brand?.name || "",
    };
}


const mockProducts = [{
        id: 1,
        name: "iPhone 15 Pro",
        slug: "iphone-15-pro",
        price: 99900,
        description: "Latest Apple iPhone with A17 Pro chip",
        short_description: "Latest Apple iPhone",
        stock_quantity: 50,
        image: "https://picsum.photos/id/0/300/300",
        category_id: 2,
        brand_id: 1
    },
    {
        id: 2,
        name: "Samsung Galaxy S24",
        slug: "samsung-galaxy-s24",
        price: 89900,
        description: "Samsung's flagship smartphone with AI features",
        short_description: "Samsung flagship phone",
        stock_quantity: 45,
        image: "https://picsum.photos/id/1/300/300",
        category_id: 2,
        brand_id: 2
    },
    {
        id: 3,
        name: "MacBook Pro 14",
        slug: "macbook-pro-14",
        price: 149900,
        description: "Apple MacBook Pro with M3 chip",
        short_description: "Powerful laptop",
        stock_quantity: 30,
        image: "https://picsum.photos/id/2/300/300",
        category_id: 3,
        brand_id: 1
    },
    {
        id: 4,
        name: "Dell XPS 15",
        slug: "dell-xps-15",
        price: 129900,
        description: "Premium Dell laptop with InfinityEdge display",
        short_description: "Premium laptop",
        stock_quantity: 25,
        image: "https://picsum.photos/id/3/300/300",
        category_id: 3,
        brand_id: 3
    },
    {
        id: 5,
        name: "Sony WH-1000XM5",
        slug: "sony-wh-1000xm5",
        price: 34900,
        description: "Industry-leading noise canceling headphones",
        short_description: "Premium headphones",
        stock_quantity: 100,
        image: "https://picsum.photos/id/4/300/300",
        category_id: 5,
        brand_id: 4
    }
];

// Modified API calls with fallback to mock data
export const productAPI = {
    listProducts: async() => {
        const response = await api.get('/products');
        return {
            ...response,
            data: {
                ...response.data,
                items: (response.data?.items || []).map(normalizeProduct),
            },
        };
    },
    listCategories: async() => {
        const response = await api.get('/categories');
        return response;
    },
    getProduct: async(slug) => {
        try {
            const response = await api.get(`/products/${slug}`);
            if (response.data?.item) {
                return {
                    ...response,
                    data: {
                        ...response.data,
                        item: normalizeProduct(response.data.item),
                    },
                };
            }
            const product = mockProducts.find(p => p.slug === slug);
            return { data: { item: normalizeProduct(product) } };
        } catch (error) {
            const product = mockProducts.find(p => p.slug === slug);
            return { data: { item: normalizeProduct(product) } };
        }
    },
    mediaUrl,
    normalizeProduct,
};

export default api;
