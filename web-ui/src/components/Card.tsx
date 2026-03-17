interface CardProps {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}

export function Card({ title, children, action }: CardProps) {
  return (
    <div className="bg-bg-secondary border border-border-primary rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wide">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}
