interface ErrorNoticeProps {
  message: string;
  onRetry?: () => void;
  title: string;
}

export function ErrorNotice({
  message,
  onRetry,
  title,
}: ErrorNoticeProps) {
  return (
    <section className="error-notice">
      <p className="eyebrow">Load Failed</p>
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          className="button button--primary"
          onClick={onRetry}
        >
          重新加载
        </button>
      ) : null}
    </section>
  );
}
