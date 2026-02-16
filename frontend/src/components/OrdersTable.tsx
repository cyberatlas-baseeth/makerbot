import type { Order } from '../hooks/useWebSocket';

interface OrdersTableProps {
    orders: Order[];
}

export default function OrdersTable({ orders }: OrdersTableProps) {
    return (
        <div className="glass-card animate-fade-in" style={{ animationDelay: '0.15s' }}>
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary">
                    Active Orders
                </h2>
                <span className="text-xs text-text-muted font-mono">{orders.length} orders</span>
            </div>

            {orders.length === 0 ? (
                <div className="text-center py-8 text-text-muted text-sm">
                    No active orders
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Side</th>
                                <th>Price</th>
                                <th>Size</th>
                                <th>Age</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map((order) => (
                                <tr key={order.order_id}>
                                    <td>
                                        <span className={`font-semibold ${order.side === 'buy' ? 'num-green' : 'num-red'}`}>
                                            {order.side.toUpperCase()}
                                        </span>
                                    </td>
                                    <td className="font-mono">
                                        ${order.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                                    </td>
                                    <td className="font-mono">{order.size}</td>
                                    <td className="font-mono text-text-secondary">{order.age_seconds.toFixed(0)}s</td>
                                    <td>
                                        <span className={`badge ${order.status === 'open' ? 'badge-running' : 'badge-paused'}`}>
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
