import { Link } from "react-router-dom";
import "../styles/cart.css";

export default function CartPage({ cart, setCart }) {

  function increase(id) {
    setCart(prev =>
      prev.map(item =>
        item.id === id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      )
    );
  }

  function decrease(id) {
    setCart(prev =>
      prev.map(item =>
        item.id === id
          ? {
            ...item,
            quantity: item.quantity > 1
              ? item.quantity - 1
              : 0
          }
          : item
      )
    );
  }

  function removeItem(id) {
    setCart(prev => prev.filter(item => item.id !== id));
  }

  const subtotal = cart.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  const shipping = cart.length > 0 ? 500 : 0;
  const total = subtotal + shipping;

  if (cart.length === 0) {
    return (
      <div className="cart-page">
        <h1>Shopping Cart</h1>
        <p>Your cart is empty.</p>

        <Link to="/products">Continue Shopping</Link>
      </div>
    );
  }

  return (
    <div className="cart-page">

      <div className="cart-left">
        <h1>Shopping Cart</h1>

        {cart.map(item => (
          <div key={item.id} className="cart-item">

            <img src={item.primary_image ||  "https://placehold.co/400x400?text=No+Image"} alt={item.name} />

            <div className="cart-info">
              <h3>{item.name}</h3>
              <p>KES {item.price}</p>

              <div className="qty-box">
                <button onClick={() => decrease(item.id)}>-</button>
                <span>{item.quantity}</span>
                <button onClick={() => increase(item.id)}>+</button>
              </div>

              <button
                className="remove-btn"
                onClick={() => removeItem(item.id)}
              >
                Remove
              </button>
            </div>

            <div className="line-total">
              KES {item.price * item.quantity}
            </div>

          </div>
        ))}
      </div>

      <div className="cart-right">
        <h2>Order Summary</h2>

        <p>Subtotal: KES {subtotal}</p>
        <p>Shipping: KES {shipping}</p>

        <hr />

        <h3>Total: KES {total}</h3>

        <button className="checkout-btn">
          Proceed to Checkout
        </button>
      </div>

    </div>
  );
}