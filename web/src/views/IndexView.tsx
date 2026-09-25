import { useState, useEffect } from 'react';

interface Observation {
  route: string;
  origin: string;
  destination: string;
  airline: string;
  airline_code: string;
  flight_number: string;
  cabin: string;
  travel_date: string;
  lead_days: number;
  total_fare: number;
  base_fare: number;
  taxes: number;
  source: string;
  availability: string;
  collected_at: string;
  fare_family: string;
  stops: number;
  price_status: string;
  requires_self_transfer: boolean;
  collection_mode: string;
}

export default function IndexView() {
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('http://localhost:8001/api/observations')
      .then((res) => {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then((data) => {
        setObservations(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="loading" style={{ padding: 'var(--sp-8)' }}>Loading observations...</div>;
  }

  if (error) {
    return <div className="error-state" style={{ padding: 'var(--sp-8)', color: 'var(--red)' }}>Error: {error}</div>;
  }

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--sp-6)' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 600, color: 'var(--ink)', marginBottom: 'var(--sp-2)' }}>
          Fare Observations
        </h1>
        <p style={{ color: 'var(--ink-2)' }}>
          Showing the latest {observations.length} collected flight fares.
        </p>
      </div>

      <div style={{ overflowX: 'auto', backgroundColor: '#fff', borderRadius: '8px', border: '1px solid var(--contour)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--paper-2)', borderBottom: '1px solid var(--contour)' }}>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Route</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Airline</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Flight</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Travel Date</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Lead Days</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Total Fare</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Path</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Source</th>
              <th style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--ink-2)' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {observations.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--ink-2)' }}>
                  No observations found. Run the scraper to collect data.
                </td>
              </tr>
            ) : (
              observations.map((obs, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--contour)' }}>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500 }}>{obs.route}</td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)' }}>{obs.airline}</td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)', color: 'var(--ink-2)', fontSize: '0.9em' }}>{obs.flight_number}</td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
                    {obs.travel_date ? new Date(obs.travel_date).toLocaleDateString('en-GB') : '—'}
                  </td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)', color: 'var(--ink-2)' }}>{obs.lead_days}d</td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)', fontWeight: 500, color: 'var(--green)' }}>
                    ₹{obs.total_fare.toLocaleString('en-IN')}
                  </td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
                    <span style={{ fontSize: '10px', color: 'var(--ink-2)', border: '1px solid var(--contour)', padding: '2px 4px', borderRadius: '4px', background: 'var(--paper-2)' }}>
                      {obs.collection_mode || 'API'}
                    </span>
                  </td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
                    <span style={{ padding: '2px 6px', backgroundColor: 'var(--paper-2)', borderRadius: '4px', fontSize: '0.85em' }}>
                      {obs.source}
                    </span>
                  </td>
                  <td style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
                    <span style={{ 
                      padding: '2px 6px', 
                      backgroundColor: obs.price_status === 'OK' ? '#ecfdf5' : '#fef2f2', 
                      color: obs.price_status === 'OK' ? '#059669' : '#dc2626',
                      borderRadius: '4px', 
                      fontSize: '0.85em' 
                    }}>
                      {obs.price_status || 'UNKNOWN'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
