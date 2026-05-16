import { paymentAPI } from './api';

export async function createPayment(orderId, amount, phoneNumber) {
    try {
        const data = await paymentAPI.createPayment({
            order_id: orderId,
            amount,
            phone_number: phoneNumber,
            provider: 'mpesa',
            currency: 'KES'
        });
        return {
            success: true,
            paymentId: data.payment ? data.payment.id : data.id
        };
    } catch (err) {
        const errData = err.response ? err.response.data : null;
        const errObj = errData ? errData.error : null;
        const message = errObj ? errObj.message : 'Failed to initiate payment';
        return { success: false, message };
    }
}

export function pollPaymentStatus(paymentId, onSuccess, onFailure, onTimeout) {
    let attempts = 0;
    const maxAttempts = 60;

    const interval = setInterval(async() => {
        attempts++;

        if (attempts > maxAttempts) {
            clearInterval(interval);
            onTimeout();
            return;
        }

        try {
            const data = await paymentAPI.getPayments();
            const payments = data.payments || data.items || [];
            const payment = payments.find(p => p.id === paymentId);

            if (!payment) return;

            if (payment.status === 'paid') {
                clearInterval(interval);
                onSuccess();
            } else if (payment.status === 'failed') {
                clearInterval(interval);
                onFailure('Payment was declined. Please try again.');
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }, 2000);

    return interval;
}