import api from "./api";

const paymentAPI = {
  createPayment: ({ order_id, amount, phone_number, provider = "mpesa", currency = "KES" }) =>
    api.post("/payments", {
      order_id,
      amount,
      phone_number,
      provider,
      method: provider,
      currency,
    }),
  listPayments: () => api.get("/payments"),
};

export default paymentAPI;
