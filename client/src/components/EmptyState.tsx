interface EmptyStateProps {
  action?: React.ReactNode;
  description: string;
  title: string;
}

export function EmptyState({
  action,
  description,
  title,
}: EmptyStateProps) {
  return (
    <section className="empty-state">
      <p className="eyebrow">No Data</p>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </section>
  );
}
