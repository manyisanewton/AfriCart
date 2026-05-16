import { useState } from 'react';

export default function MpesaPayment({ onSubmit, loading, statusMessage }) {
  const [mpesaPhone, setMpesaPhone] = useState('');
  const [error, setError] = useState('');

  function formatPhone(raw) {
    const digits = raw.replace(/\D/g, '');
    if (digits.startsWith('0') && digits.length === 10) {
      return '254' + digits.slice(1);
    }
    if (digits.startsWith('254') && digits.length === 12) {
      return digits;
    }
    if (digits.startsWith('7') && digits.length === 9) {
      return '254' + digits;
    }
    return digits;
  }

  function handlePay() {
    const formatted = formatPhone(mpesaPhone);
    if (formatted.length !== 12 || !formatted.startsWith('254')) {
      setError('Enter a valid Kenyan phone number e.g. 0712345678');
      return;
    }
    setError('');
    onSubmit(formatted);
  }

  return (
    <div className="mpesa-payment">
      <div className="mpesa-logo">
        <span className="mpesa-badge">M-PESA</span>
      </div>
      <p className="mpesa-instruction">
        Enter your M-Pesa number. You will receive a PIN prompt on your phone.
      </p>
      <input
        type="tel"
        placeholder="e.g. 0712 345 678"
        value={mpesaPhone}
        onChange={e => setMpesaPhone(e.target.value)}
        disabled={loading}
        className="mpesa-input"
      />
      {error && <p className="mpesa-error">{error}</p>}
      {statusMessage && (
        <div className="mpesa-status">
          <span className="spinner" />
          <p>{statusMessage}</p>
        </div>
      )}
      <button
        className="pay-btn"
        onClick={handlePay}
        disabled={loading || !mpesaPhone}
      >
        {loading ? 'Processing...' : 'Pay Now'}
      </button>
    </div>
  );
}