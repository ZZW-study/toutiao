interface LoadingBlockProps {
  label: string;
}

export function LoadingBlock({ label }: LoadingBlockProps) {
  return (
    <div className="loading-block" aria-live="polite" aria-busy="true">
      <div className="loading-block__shimmer" />
      <p>{label}</p>
    </div>
  );
}
