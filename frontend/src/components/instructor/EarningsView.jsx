import React from 'react';
import { DollarSign, TrendingUp } from 'lucide-react';

export default function EarningsView({ instructorId, totalEarnings }) {
  return (
    <div className="earnings-view" data-testid="earnings-view">
      <div className="earnings-summary">
        <div className="earnings-card">
          <DollarSign className="earnings-icon" size={48} />
          <div>
            <h2 data-testid="total-earnings">${totalEarnings.toFixed(2)}</h2>
            <p>Total Earnings</p>
          </div>
        </div>

        <div className="earnings-info">
          <TrendingUp size={24} className="info-icon" />
          <div>
            <h3>Earnings Breakdown</h3>
            <p>You earn 100% of each course sale</p>
          </div>
        </div>

      </div>

      <div className="earnings-note">
        <h3>Payment Information</h3>
        <p>Earnings are calculated after each successful course purchase.</p>
        <p>Withdrawals can be requested once you reach $100.</p>
      </div>
    </div>
  );
}