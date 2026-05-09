// src/services/api.js
import axios from "axios";

const api = axios.create({
    baseURL: "http://127.0.0.1:5000/api/v1"
});


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
        console.log("REAL API RESPONSE:", response.data);
        return response;
    },
    listCategories: async() => {
        const response = await api.get('/categories');
        console.log("REAL CATEGORIES:", response.data);
        return response;
    },
    getProduct: async(slug) => {
        try {
            const response = await api.get(`/products/${slug}`);
            console.log("GET PRODUCT RESPONSE:", response.data);
            if (response.data) {
                return response;
            }
            const product = mockProducts.find(p => p.slug === slug);
            console.log("MOCK FALLBACK:", product);
            return { data: product };
        } catch (error) {
            console.log("GET PRODUCT ERROR:", error.message);
            const product = mockProducts.find(p => p.slug === slug);
            console.log("MOCK FALLBACK:", product);
            return { data: product };
        }
    }
};

export default api;