import type { Order } from '../hooks/useWebSocket';

interface OrdersTableProps {
    orders: Order[];
}

export default function OrdersTable({ orders }: OrdersTableProps) {
    return (
        <div>
            <h3 className="heading-lg" style={{ marginBottom: '12px' }}>OPEN ORDERS</h3>

            {orders.length === 0 ? (
                <div style={{
                    padding: '20px',
                    border: '2px solid rgba(0,0,0,0.15)',
                    textAlign: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    opacity: 0.4,
                }}>
                    NO ACTIVE ORDERS
                </div>
            ) : (
                <div style={{ border: '2px solid rgba(0,0,0,0.2)', overflow: 'hidden' }}>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>SIDE</th>
                                <th>PRICE</th>
                                <th>SIZE</th>
                                <th>AGE</th>
                                <th>STATUS</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map((order) => (
                                <tr key={order.order_id}>
                                    <td>
                                        <span style={{
                                            fontWeight: 700,
                                            textTransform: 'uppercase',
                                            color: order.side === 'buy' ? '#0F2F3A' : '#D65A00',
                                        }}>
                                            {order.side}
                                        </span>
                                    </td>
                                    <td style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
                                        ${order.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                                    </td>
                                    <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                                        {order.size.toFixed(6)}
                                    </td>
                                    <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                                        {order.age_seconds.toFixed(0)}s
                                    </td>
                                    <td>
                                        <span style={{
                                            fontSize: '0.65rem',
                                            fontWeight: 700,
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.08em',
                                        }}>
                                            {order.status}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
