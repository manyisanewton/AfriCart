// src/services/api.js
import axios from "axios";

const api = axios.create({
    baseURL: "http://127.0.0.1:5000/api/v1"
});

// Auth interceptor — attaches JWT to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

const DEFAULT_IMAGE = "https://placehold.co/400x400?text=TechHive";

const mockCategories = [
    { id: 1, name: "Electronics", slug: "electronics" },
    { id: 2, name: "Smartphones", slug: "smartphones" },
    { id: 3, name: "Laptops", slug: "laptops" },
    { id: 4, name: "Accessories", slug: "accessories" },
    { id: 5, name: "Audio", slug: "audio" }
];

const mockProducts = [
    { id: 1, name: "iPhone 15 Pro", slug: "iphone-15-pro", price: 99900, compare_at_price: 109900, description: "The iPhone 15 Pro features a durable titanium design, A17 Pro chip, 48MP camera system, and USB-C connectivity.", short_description: "Latest Apple iPhone with A17 Pro chip", sku: "APL-IP15P-001", stock_quantity: 50, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 2, name: "Smartphones", slug: "smartphones" }, brand: { id: 1, name: "Apple", slug: "apple" }, rating: 4.8, reviews_count: 234 },
    { id: 2, name: "Samsung Galaxy S24 Ultra", slug: "samsung-galaxy-s24-ultra", price: 89900, compare_at_price: 99900, description: "Samsung's flagship with AI features, 200MP camera, built-in S Pen.", short_description: "Samsung's flagship smartphone with AI", sku: "SSM-GS24U-001", stock_quantity: 45, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 2, name: "Smartphones", slug: "smartphones" }, brand: { id: 2, name: "Samsung", slug: "samsung" }, rating: 4.7, reviews_count: 189 },
    { id: 3, name: "MacBook Pro 14", slug: "macbook-pro-14", price: 149900, compare_at_price: 169900, description: "Apple MacBook Pro with M3 chip, 14-inch Liquid Retina XDR display.", short_description: "Powerful Apple laptop with M3 chip", sku: "APL-MBP14-001", stock_quantity: 30, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 3, name: "Laptops", slug: "laptops" }, brand: { id: 1, name: "Apple", slug: "apple" }, rating: 4.9, reviews_count: 456 },
    { id: 4, name: "Dell XPS 15", slug: "dell-xps-15", price: 129900, compare_at_price: 149900, description: "Premium Dell laptop with InfinityEdge display, Intel Core i7.", short_description: "Premium Dell laptop", sku: "DELL-XPS15-001", stock_quantity: 25, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 3, name: "Laptops", slug: "laptops" }, brand: { id: 3, name: "Dell", slug: "dell" }, rating: 4.6, reviews_count: 123 },
    { id: 5, name: "Sony WH-1000XM5", slug: "sony-wh-1000xm5", price: 34900, compare_at_price: 39900, description: "Industry-leading noise canceling headphones with 30-hour battery life.", short_description: "Premium noise-cancelling headphones", sku: "SNY-WH1000-001", stock_quantity: 100, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 5, name: "Audio", slug: "audio" }, brand: { id: 4, name: "Sony", slug: "sony" }, rating: 4.9, reviews_count: 567 },
    { id: 6, name: "Google Pixel 8 Pro", slug: "google-pixel-8-pro", price: 79900, compare_at_price: 89900, description: "Google's flagship with AI-powered camera, Tensor G3 chip.", short_description: "Pure Android flagship", sku: "GOOG-P8P-001", stock_quantity: 35, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 2, name: "Smartphones", slug: "smartphones" }, brand: { id: null, name: "Google", slug: "google" }, rating: 4.7, reviews_count: 89 },
    { id: 7, name: "iPad Air 5", slug: "ipad-air-5", price: 64900, compare_at_price: 74900, description: "Powerful iPad with M1 chip, 10.9-inch Liquid Retina display.", short_description: "Versatile Apple tablet", sku: "APL-IPA5-001", stock_quantity: 40, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 3, name: "Laptops", slug: "laptops" }, brand: { id: 1, name: "Apple", slug: "apple" }, rating: 4.8, reviews_count: 234 },
    { id: 8, name: "AirPods Pro 2", slug: "airpods-pro-2", price: 24900, compare_at_price: 29900, description: "Apple AirPods Pro with H2 chip, Active Noise Cancellation.", short_description: "Premium wireless earbuds", sku: "APL-APP2-001", stock_quantity: 75, primary_image: DEFAULT_IMAGE, images: [DEFAULT_IMAGE, DEFAULT_IMAGE], category: { id: 5, name: "Audio", slug: "audio" }, brand: { id: 1, name: "Apple", slug: "apple" }, rating: 4.8, reviews_count: 345 }
];

export const productAPI = {
    listProducts: async() => {
        await new Promise(resolve => setTimeout(resolve, 500));
        return { data: { items: mockProducts, pagination: { page: 1, per_page: 10, total: mockProducts.length, total_pages: 1 } } };
    },
    listCategories: async() => {
        await new Promise(resolve => setTimeout(resolve, 200));
        return { data: { items: mockCategories } };
    },
    getProduct: async(slug) => {
        await new Promise(resolve => setTimeout(resolve, 300));
        const product = mockProducts.find(p => p.slug === slug);
        return { data: { item: product || null } };
    },
    listBrands: async() => {
        await new Promise(resolve => setTimeout(resolve, 200));
        return { data: { items: [] } };
    }
};

export const orderAPI = {
    createOrder: async(deliveryDetails) => {
        const response = await api.post('/orders', deliveryDetails);
        return response.data;
    }
};

export const paymentAPI = {
    createPayment: async(payload) => {
        const response = await api.post('/payments', payload);
        return response.data;
    },
    getPayments: async() => {
        const response = await api.get('/payments');
        return response.data;
    }
};

export const authAPI = {
    login: async(email, password) => {
        const response = await api.post('/auth/login', { email, password });
        return response.data;
    },
    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }
};

export default api;