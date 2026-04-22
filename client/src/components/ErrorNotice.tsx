interface ErrorNoticeProps {
  title: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorNotice({
  title,
  message,
  onRetry,
}: ErrorNoticeProps) {
  return (
    <div className="error-notice" role="alert">
      <p className="eyebrow">Error</p>
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="text-action text-action--button"
        >
          重试
        </button>
      ) : null}
    </div>
  );
}
