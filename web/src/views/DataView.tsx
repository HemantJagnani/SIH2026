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

  if (loading) return <div>Loading data...</div>;

  return (
    <div className="view-content">
      <h2>Raw Observations Data</h2>
      <p>Showing {observations.length} records</p>
      
      <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
        <table className="data-table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ccc' }}>
              <th>Source</th>
              <th>Airline</th>
              <th>Route</th>
              <th>Date</th>
              <th>Departs</th>
              <th>Arrives</th>
              <th>Stops</th>
              <th>Total Fare (INR)</th>
            </tr>
          </thead>
          <tbody>
            {observations.map((o, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                <td>{o.source}</td>
                <td>{o.airline}</td>
                <td>{o.route}</td>
                <td>{o.travel_date}</td>
                <td>{o.departure_time_local?.split('T')[1] || '-'}</td>
                <td>{o.arrival_time_local?.split('T')[1] || '-'}</td>
                <td>{o.stops}</td>
                <td>₹{o.total_fare}</td>
              </tr>
            ))}
            {observations.length === 0 && (
              <tr>
                <td colSpan={8}>No observations found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
