import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="auth-wrap">
      <div className="card auth-card" style={{ textAlign: 'center' }}>
        <h1 className="auth-title">Page not found</h1>
        <p className="auth-sub">The page you're looking for doesn't exist.</p>
        <Link to="/" className="btn btn-primary">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
