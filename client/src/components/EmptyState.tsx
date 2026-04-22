interface EmptyStateProps {
  title: string;
  description: string;
}

export function EmptyState({
  title,
  description,
}: EmptyStateProps) {
  return (
    <div className="empty-state" role="status">
      <p className="eyebrow">Empty</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
