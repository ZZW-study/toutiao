interface PaginationProps {
  page: number;
  total: number;
  hasMore: boolean;
  onPageChange: (page: number) => void;
}

export function Pagination({
  page,
  total,
  hasMore,
  onPageChange,
}: PaginationProps) {
  return (
    <nav className="pagination" aria-label="新闻分页">
      <button
        type="button"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="pagination__button"
      >
        上一页
      </button>

      <div className="pagination__meta">
        <span>第 {page} 页</span>
        <small>共 {total} 条</small>
      </div>

      <button
        type="button"
        onClick={() => onPageChange(page + 1)}
        disabled={!hasMore}
        className="pagination__button"
      >
        下一页
      </button>
    </nav>
  );
}
