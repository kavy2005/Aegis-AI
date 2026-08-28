interface StateBlockProps {
  title: string;
  subtitle?: string;
  variant?: 'empty' | 'error';
  action?: { label: string; onClick: () => void };
}

export function StateBlock({ title, subtitle, variant = 'empty', action }: StateBlockProps) {
  return (
    <div className={variant === 'error' ? 'state-block error' : 'state-block'} role={variant === 'error' ? 'alert' : undefined}>
      <p className="state-title">{title}</p>
      {subtitle && <p className="state-sub">{subtitle}</p>}
      {action && (
        <button type="button" className="btn btn-ghost mt-6" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
