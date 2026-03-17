interface ProgressBarProps {
  value: number;
  label: string;
  detail?: string;
}

export function ProgressBar({ value, label, detail }: ProgressBarProps) {
  const color = value > 80 ? 'bg-warning' : 'bg-accent';

  return (
    <div className="mb-3 last:mb-0">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-text-muted">{label}</span>
        <span className="text-text-secondary">{detail ?? `${value.toFixed(1)}%`}</span>
      </div>
      <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}
