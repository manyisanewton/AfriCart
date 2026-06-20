import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

export const productAPI = {
  listProducts: () => api.get("/products"),

  listCategories: () => api.get("/categories"),

  listBrands: () => api.get("/brands"),

  getProduct: (slug) => api.get(`/products/${slug}`),
};

export default api;