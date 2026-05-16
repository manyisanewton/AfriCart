import api from './api';

export async function createAddress(formData) {
    try {
        const response = await api.post('/addresses', {
            recipient_name: formData.fullName,
            phone_number: formData.phone,
            address_line_1: formData.address,
            city: formData.city,
            country: 'Kenya',
            label: 'Home'
        });
        const data = response.data;
        return {
            success: true,
            addressId: data.address ? data.address.id : data.id
        };
    } catch (err) {
        const errData = err.response ? err.response.data : null;
        const errObj = errData ? errData.error : null;
        const message = errObj ? errObj.message : 'Failed to save address';
        return { success: false, message };
    }
}

export async function syncCartToBackend(cart) {
    try {
        for (const item of cart) {
            await api.post('/cart/items', {
                product_id: item.id,
                quantity: item.quantity
            });
        }
        return { success: true };
    } catch (err) {
        const errData = err.response ? err.response.data : null;
        const errObj = errData ? errData.error : null;
        const message = errObj ? errObj.message : 'Failed to sync cart';
        return { success: false, message };
    }
}

export async function createOrder(addressId) {
    try {
        const response = await api.post('/orders', { address_id: addressId });
        const data = response.data;
        return {
            success: true,
            orderId: data.order ? data.order.id : data.id
        };
    } catch (err) {
        const errData = err.response ? err.response.data : null;
        const errObj = errData ? errData.error : null;
        const message = errObj ? errObj.message : 'Failed to create order';
        return { success: false, message };
    }
}