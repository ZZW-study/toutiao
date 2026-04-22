interface LoadingBlockProps {
  label: string;
}

export function LoadingBlock({
  label,
}: LoadingBlockProps) {
  return (
    <section className="loading-block" aria-live="polite">
      <p>{label}</p>
      <div className="loading-block__bar" />
    </section>
  );
}
