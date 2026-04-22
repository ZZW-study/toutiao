interface PaginationProps {
  hasMore: boolean;
  onPageChange: (page: number) => void;
  page: number;
  total: number;
}

export function Pagination({
  hasMore,
  onPageChange,
  page,
  total,
}: PaginationProps) {
  return (
    <div className="pagination">
      <button
        type="button"
        className="button button--ghost"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        上一页
      </button>
      <div className="pagination__meta">
        <strong>第 {page} 页</strong>
        <span>共 {total} 条内容</span>
      </div>
      <button
        type="button"
        className="button button--ghost"
        disabled={!hasMore}
        onClick={() => onPageChange(page + 1)}
      >
        下一页
      </button>
    </div>
  );
}
