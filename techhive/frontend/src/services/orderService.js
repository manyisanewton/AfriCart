import api from "./api";

export const orderAPI = {
  // Step 1: create a delivery address, returns { id, ... }
  createAddress: (addressData) => api.post("/addresses", addressData),

  // Step 2: sync each cart item to the server-side cart
  // (backend needs items in its own cart table before an order can be created)
  addCartItem: (productId, quantity) =>
    api.post("/cart/items", { product_id: productId, quantity }),

  syncCart: async (cartItems) => {
    for (const item of cartItems) {
      await orderAPI.addCartItem(item.id, item.quantity);
    }
  },

  // Step 3: create the order, needs address_id
  createOrder: (addressId) => api.post("/orders", { address_id: addressId }),

  // Orchestrates all three steps. Returns the created order.
  placeOrder: async ({ cart, address }) => {
    const addressRes = await orderAPI.createAddress(address);
    const addressId = addressRes.data.item.id;

    await orderAPI.syncCart(cart);

    const orderRes = await orderAPI.createOrder(addressId);
    console.log("Raw order response:", orderRes.data);
    return orderRes.data.item || orderRes.data.order || orderRes.data;
  },
};

export default orderAPI;