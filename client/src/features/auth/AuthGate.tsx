import { useAuth } from "./useAuth";

interface AuthGateProps {
  actionLabel?: string;
  description: string;
  title: string;
}

export function AuthGate({
  actionLabel = "立即登录",
  description,
  title,
}: AuthGateProps) {
  const { openAuthModal } = useAuth();

  return (
    <section className="empty-state auth-gate">
      <p className="eyebrow">Login Required</p>
      <h3>{title}</h3>
      <p>{description}</p>
      <button
        type="button"
        className="button button--primary"
        onClick={() => openAuthModal("login", description)}
      >
        {actionLabel}
      </button>
    </section>
  );
}
