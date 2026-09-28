import { useState, useEffect } from 'react';
import { api, type Observation } from '../api';

export default function DataView() {
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.observations()
      .then(obs => {
        setObservations(obs);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="view-content">
        <div className="state-banner state-banner--loading">Loading raw observations data...</div>
      </div>
    );
  }

  return (
    <div className="view-content">
      <h2>Raw Observations Data</h2>
      <p className="text-caption" style={{ marginBottom: 'var(--sp-3)' }}>Showing {observations.length} records</p>
      
      <div style={{ overflowX: 'auto', marginTop: 'var(--sp-2)' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Airline</th>
              <th>Route</th>
              <th>Date</th>
              <th>Departs</th>
              <th>Arrives</th>
              <th className="col-num">Stops</th>
              <th className="col-num">Total Fare (INR)</th>
            </tr>
          </thead>
          <tbody>
            {observations.map((o, i) => (
              <tr key={i}>
                <td>{o.source}</td>
                <td>{o.airline}</td>
                <td style={{ fontWeight: 600 }}>{o.route}</td>
                <td className="font-num">{o.travel_date}</td>
                <td className="font-num">{o.departure_time_local?.split('T')[1]?.slice(0, 5) || '—'}</td>
                <td className="font-num">{o.arrival_time_local?.split('T')[1]?.slice(0, 5) || '—'}</td>
                <td className="font-num col-num">{o.stops === 0 ? 'Nonstop' : `${o.stops}`}</td>
                <td className="font-num col-num" style={{ fontWeight: 700 }}>₹{Math.round(Number(o.total_fare)).toLocaleString('en-IN')}</td>
              </tr>
            ))}
            {observations.length === 0 && (
              <tr>
                <td colSpan={8}>
                  <div className="data-table-empty">No observations found in storage.</div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
